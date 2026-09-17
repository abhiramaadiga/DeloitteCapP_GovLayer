"""
Composite Risk Scoring Engine with sub-1ms fast-path and auto-quarantine.

Provides the exact callable required by the gateway:
  evaluate_agent_request(agent_id, endpoint, payload_str, method) -> Dict

Auto-invokes KillSwitch.quarantine_agent() when risk_score >= 0.75.
"""
import math
import time
import logging
import joblib
from pathlib import Path
from typing import Any, Dict, List, Optional

from backend.ml.feature_extractor import (
    extract_features,
    reset_agent_state,
    calculate_markov_score,
    normalize_endpoint,
)

logger = logging.getLogger("agentic_iam.risk_engine")

MODEL_PATH = Path(__file__).resolve().parent / "models" / "isolation_forest.joblib"
_model = None

# In-memory quarantine cache (L1 fallback; primary store is Backend Lead's Redis KillSwitch)
_quarantine_cache: Dict[str, dict] = {}

RISK_THRESHOLD = 0.75


def _load_model(force_reload: bool = False):
    global _model
    if (_model is None or force_reload) and MODEL_PATH.exists():
        _model = joblib.load(MODEL_PATH)
        _model.n_jobs = 1
        logger.info(f"Loaded Isolation Forest model from {MODEL_PATH}")
    return _model


def reload_model():
    """Forces reloading the active model from disk into memory."""
    return _load_model(force_reload=True)


# Eagerly pre-warm model on import to avoid cold-start latency spikes
try:
    _m = _load_model()
    if _m is not None:
        _m.decision_function([[3.0, 1.0, 0.0, 100.0]])
except Exception:
    pass


def _sigmoid_calibrate(raw_decision: float, steepness: float = 3.0) -> float:
    """Maps Isolation Forest decision_function output to [0.0, 1.0] risk score."""
    return round(1.0 / (1.0 + math.exp(steepness * raw_decision)), 4)


def evaluate_agent_request(
    agent_id: str,
    endpoint: str,
    payload_str: str,
    method: str = "GET",
    timestamp: Optional[float] = None,
) -> Dict[str, Any]:
    """
    Evaluates a single agent API request and returns a risk assessment.

    Parameters
    ----------
    agent_id    : Non-human identity ID (e.g. "Agent-Support-01")
    endpoint    : Target banking API path (e.g. "/transfers/wire")
    payload_str : Raw request body text
    method      : HTTP method (GET, POST, etc.)
    timestamp   : Optional UNIX epoch for deterministic testing

    Returns
    -------
    {
        "risk_score":    float  (0.0 - 1.0),
        "is_anomaly":    bool,
        "entropy":       float,
        "velocity_rps":  float,
        "factors":       list[str]
    }
    """
    t0 = time.perf_counter()

    # Fast check: already quarantined in L1 in-memory cache?
    if agent_id in _quarantine_cache:
        return {
            "risk_score": 1.0,
            "is_anomaly": True,
            "entropy": 0.0,
            "velocity_rps": 0.0,
            "factors": ["AGENT_ALREADY_QUARANTINED"],
            "blocked": True,
            "latency_ms": round((time.perf_counter() - t0) * 1000, 3),
        }

    # Fast-path bypass for trivial balance/FAQ queries (<0.05ms)
    norm_endpoint = normalize_endpoint(endpoint)
    if (
        norm_endpoint in ("/balance", "/faq")
        and len(payload_str) < 60
        and method == "GET"
    ):
        # Update sequence tracking even on fast-path
        calculate_markov_score(agent_id, norm_endpoint)
        return {
            "risk_score": 0.10,
            "is_anomaly": False,
            "entropy": 3.2,
            "velocity_rps": 0.0,
            "factors": [],
            "fast_path": True,
            "latency_ms": round((time.perf_counter() - t0) * 1000, 3),
        }

    # Deep check: distributed KillSwitch (Redis) status for full pipeline evaluations
    is_quarantined_status = False
    try:
        from backend.core.killswitch import KillSwitch
        is_quarantined_status = KillSwitch.is_quarantined(agent_id)
        if not is_quarantined_status and agent_id in _quarantine_cache:
            _quarantine_cache.pop(agent_id, None)
    except Exception:
        is_quarantined_status = agent_id in _quarantine_cache

    if is_quarantined_status:
        return {
            "risk_score": 1.0,
            "is_anomaly": True,
            "entropy": 0.0,
            "velocity_rps": 0.0,
            "factors": ["AGENT_ALREADY_QUARANTINED"],
            "blocked": True,
            "latency_ms": round((time.perf_counter() - t0) * 1000, 3),
        }

    # Extract features
    payload_bytes = len(payload_str.encode("utf-8"))
    feats = extract_features(
        agent_id=agent_id,
        endpoint=endpoint,
        http_method=method,
        payload_bytes=payload_bytes,
        raw_payload_str=payload_str,
        timestamp=timestamp,
    )

    entropy = feats["entropy"]
    velocity_rps = feats["velocity_rps"]
    markov_score = feats["markov_score"]
    vector = [feats["vector"]]

    # ML Inference
    model = _load_model()
    if model is not None:
        raw_decision = float(model.decision_function(vector)[0])
        risk_score = _sigmoid_calibrate(raw_decision)
    else:
        logger.warning("Model not loaded - using heuristic-only scoring.")
        risk_score = 0.30

    # Guardrail hard floors (deterministic safety nets)
    factors: List[str] = []

    if entropy > 4.8:
        factors.append(f"HIGH_ENTROPY ({entropy:.2f} bits > 4.8)")
        risk_score = max(risk_score, 0.80)

    if velocity_rps > 10.0:
        factors.append(f"BURST_VELOCITY ({velocity_rps:.1f} RPS > 10.0)")
        risk_score = max(risk_score, 0.78)

    if markov_score == 1.0:
        factors.append(f"ILLEGAL_API_TRANSITION (to {endpoint})")
        risk_score = max(risk_score, 0.82)

    if payload_bytes > 4000:
        factors.append(f"LARGE_PAYLOAD ({payload_bytes} bytes > 4000)")
        risk_score = max(risk_score, 0.76)

    # Clamp
    risk_score = round(min(max(risk_score, 0.0), 1.0), 4)
    is_anomaly = risk_score >= RISK_THRESHOLD

    # Auto-quarantine via KillSwitch integration
    if is_anomaly:
        reason = "; ".join(factors) if factors else "ML behavioral anomaly score exceeded threshold"
        _quarantine_cache[agent_id] = {
            "risk_score": risk_score,
            "reason": reason,
            "timestamp": time.time(),
        }
        # Integration point: call Backend Lead's KillSwitch
                # Integration point: call Backend Lead's KillSwitch
        try:
            from backend.core.killswitch import KillSwitch
            KillSwitch.quarantine_agent(agent_id, reason, risk_score)
            logger.critical(
                f"[KILL-SWITCH] Agent {agent_id} quarantined | "
                f"Score: {risk_score} | Factors: {factors}"
            )
        except ImportError:
            try:
                from backend.kill_switch import KillSwitch #Still should check on this 
                KillSwitch.quarantine_agent(agent_id, reason, risk_score)
            except ImportError:
                logger.warning(f"[KILL-SWITCH LOCAL] Agent {agent_id} quarantined in memory L1 cache.")
        except Exception as e:
            logger.error(f"KillSwitch call failed: {e}")

    latency_ms = round((time.perf_counter() - t0) * 1000, 3)
    return {
        "risk_score": risk_score,
        "is_anomaly": is_anomaly,
        "entropy": entropy,
        "velocity_rps": velocity_rps,
        "factors": factors,
        "latency_ms": latency_ms,
    }


def reinstate_agent(agent_id: str, analyst_id: str, justification: str) -> bool:
    """FFIEC-compliant un-quarantine. Requires analyst ID and rationale (min 10 chars)."""
    if not analyst_id or not justification or len(justification.strip()) < 10:
        raise ValueError(
            "FFIEC Compliance Error: Reinstatement requires analyst_id "
            "and detailed justification (min 10 chars)."
        )
    _quarantine_cache.pop(agent_id, None)
    try:
        reset_agent_state(agent_id)
    except Exception:
        pass
    try:
        from backend.core.killswitch import KillSwitch
        KillSwitch.lift_quarantine(agent_id, justification, analyst_id)
    except (ImportError, Exception):
        pass
    return True


def clear_all_quarantines():
    """Wipes all agent quarantine records from ML L1 cache."""
    _quarantine_cache.clear()
    try:
        reset_agent_state(None)
    except Exception:
        pass


def is_quarantined(agent_id: str) -> bool:
    """Check if agent is currently quarantined in L1 cache or KillSwitch."""
    try:
        from backend.core.killswitch import KillSwitch
        return KillSwitch.is_quarantined(agent_id)
    except Exception:
        return agent_id in _quarantine_cache
