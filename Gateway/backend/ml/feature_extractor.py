"""
Feature Extractor for AI Agent Behavioral Governance.
Extracts real-time behavioral features from Non-Human Identity (NHI) API telemetry.

Features extracted:
  1. Shannon Entropy H(X) in bits - flags prompt injection & base64 exfiltration (>4.8 bits)
  2. Sliding-window Request Velocity - requests per second (RPS) in a 10-second window
  3. Markov Endpoint Sequence Score - detects illegal state jumps in API workflows
"""
import math
import time
from collections import Counter, defaultdict, deque
from typing import Any, Dict, Optional


# ---------------------------------------------------------------------------
# Module-level state: sliding window queues and per-agent last-seen endpoints
# ---------------------------------------------------------------------------
_velocity_windows: Dict[str, deque] = defaultdict(deque)
_agent_last_endpoint: Dict[str, str] = {}

# SOX 404 / Least-Privilege boundary violations - O(1) set lookup
ILLEGAL_TRANSITIONS = {
    ("/auth/agent-handshake", "/customers/export"),
    ("/auth/agent-handshake", "/transfers/wire"),
    ("/faq", "/transfers/wire"),
    ("/faq", "/customers/export"),
    ("/balance", "/customers/export"),
    ("/balance", "/transfers/wire"),
    ("/transactions/recent", "/customers/export"),
    ("/transactions/recent", "/transfers/wire"),
}

VELOCITY_WINDOW_SECONDS = 10.0


def calculate_entropy(text: str) -> float:
    """
    Computes Shannon Entropy H(X) = -sum P(x) log2 P(x) in bits.

    Benchmarks:
      - Normal English / JSON banking queries:  ~3.0 - 4.2 bits
      - Base64-encoded data exfiltration:       ~5.2 - 6.0 bits
      - Prompt injection with encoded payloads: > 4.8 bits
    """
    if not text:
        return 0.0
    n = len(text)
    return round(
        -sum((c / n) * math.log2(c / n) for c in Counter(text).values()),
        4,
    )


def calculate_velocity(agent_id: str, current_time: float = None) -> float:
    """
    Calculates instantaneous requests-per-second (RPS) in a sliding 10-second window.
    """
    now = current_time if current_time is not None else time.time()
    q = _velocity_windows[agent_id]
    q.append(now)
    cutoff = now - VELOCITY_WINDOW_SECONDS
    while q and q[0] < cutoff:
        q.popleft()
    return round(len(q) / VELOCITY_WINDOW_SECONDS, 2)


def normalize_endpoint(endpoint: str) -> str:
    """Normalizes parameterized paths like /accounts/401/balance to /balance."""
    clean = endpoint.strip("/")
    if clean.startswith("accounts/") and clean.endswith("/balance"):
        return "/balance"
    return "/" + clean if not clean.startswith("/") else clean


def calculate_markov_score(agent_id: str, endpoint: str) -> float:
    """
    Returns 1.0 if the transition from the agent's previous endpoint to the
    current endpoint is an illegal privilege-escalation jump, else 0.0.
    """
    norm = normalize_endpoint(endpoint)
    prev = _agent_last_endpoint.get(agent_id)
    _agent_last_endpoint[agent_id] = norm
    if prev is None:
        return 0.0
    return 1.0 if (prev, norm) in ILLEGAL_TRANSITIONS else 0.0


def extract_features(
    agent_id: str,
    endpoint: str,
    http_method: str,
    payload_bytes: int,
    raw_payload_str: str,
    timestamp: float = None,
) -> Dict[str, Any]:
    """
    High-speed feature extraction pipeline.

    Parameters
    ----------
    agent_id        : Unique non-human identity identifier
    endpoint        : Target banking API endpoint path
    http_method     : HTTP method (GET, POST, PUT, DELETE)
    payload_bytes   : Size of the request payload in bytes
    raw_payload_str : Raw text body of the request
    timestamp       : Optional UNIX epoch; defaults to time.time()

    Returns
    -------
    dict with keys: entropy, velocity_rps, markov_score, payload_bytes,
                    vector (list for ML inference)
    """
    entropy = calculate_entropy(raw_payload_str)
    velocity_rps = calculate_velocity(agent_id, current_time=timestamp)
    markov_score = calculate_markov_score(agent_id, endpoint)

    return {
        "agent_id": agent_id,
        "endpoint": endpoint,
        "http_method": http_method,
        "entropy": entropy,
        "velocity_rps": velocity_rps,
        "markov_score": markov_score,
        "payload_bytes": payload_bytes,
        "vector": [entropy, velocity_rps, markov_score, float(payload_bytes)],
    }


def reset_agent_state(agent_id: str = None):
    """Clears tracking state. If agent_id is None, clears all."""
    if agent_id:
        _velocity_windows.pop(agent_id, None)
        _agent_last_endpoint.pop(agent_id, None)
        try:
            from backend.core.cache import RevocationCache
            RevocationCache.delete(f"revoked:agent:{agent_id}")
        except Exception:
            pass
    else:
        _velocity_windows.clear()
        _agent_last_endpoint.clear()
        try:
            from backend.core.cache import RevocationCache
            RevocationCache.clear_all_revocations()
        except Exception:
            pass
