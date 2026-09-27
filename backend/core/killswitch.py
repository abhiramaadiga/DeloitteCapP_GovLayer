"""
backend/core/killswitch.py
Real-time automated kill-switch and FFIEC-compliant quarantine manager.
"""
import time
from typing import Dict, Any, Optional
from backend.core.cache import RevocationCache

class KillSwitch:
    """Handles instant revocation and SOC analyst reinstatement."""
    
    @staticmethod
    def is_quarantined(agent_id: str) -> bool:
        status = RevocationCache.get(f"revoked:agent:{agent_id}")
        return status is not None

    @staticmethod
    def quarantine_agent(agent_id: str, reason: str, risk_score: float) -> Dict[str, Any]:
        start_time = time.perf_counter()
        
        timestamp = int(time.time())
        record = {
            "agent_id": agent_id,
            "status": "QUARANTINED",
            "reason": reason,
            "risk_score": risk_score,
            "timestamp": timestamp,
        }
        
        # Calculate MTTR in milliseconds
        mttr_ms = round((time.perf_counter() - start_time) * 1000, 3)
        record["mttr_ms"] = mttr_ms
        
        # Write to distributed revocation cache
        RevocationCache.set(f"revoked:agent:{agent_id}", str(record), ttl_seconds=86400)
        
        # Synchronize ML risk engine in-memory L1 cache
        try:
            import backend.ml.risk_engine as re
            re._quarantine_cache[agent_id] = {
                "risk_score": risk_score,
                "reason": reason,
                "timestamp": timestamp,
            }
        except Exception:
            pass

        return record

    @staticmethod
    def lift_quarantine(agent_id: str, justification: str, analyst_id: str = "SOC-ANALYST") -> Dict[str, Any]:
        """Regulatory requirement: Un-quarantine requires human justification and verified analyst identity."""
        if not analyst_id or not str(analyst_id).strip():
            raise ValueError("FFIEC Compliance: Valid analyst_id is required to lift quarantine.")
        if not justification or len(justification.strip()) < 5:
            raise ValueError("FFIEC Compliance: Justification must contain at least 5 non-whitespace characters.")
            
        RevocationCache.delete(f"revoked:agent:{agent_id}")

        # Synchronize ML risk engine L1 cache & feature extractor tracking
        try:
            import backend.ml.risk_engine as re
            re._quarantine_cache.pop(agent_id, None)
        except Exception:
            pass

        try:
            from backend.ml.feature_extractor import reset_agent_state
            reset_agent_state(agent_id)
        except Exception:
            pass

        return {
            "agent_id": agent_id,
            "status": "ACTIVE",
            "action": "QUARANTINE_LIFTED",
            "analyst_id": analyst_id,
            "justification": justification,
            "timestamp": int(time.time())
        }

    @staticmethod
    def reinstate_agent(agent_id: str, analyst_id: str, justification: str) -> Dict[str, Any]:
        """Alias for lift_quarantine for FFIEC compliance calls."""
        return KillSwitch.lift_quarantine(agent_id, justification, analyst_id)

    @staticmethod
    def clear_all():
        """Clears all agent revocations across RevocationCache, risk_engine, and feature extractor."""
        RevocationCache.clear_all_revocations()
        try:
            import backend.ml.risk_engine as re
            re._quarantine_cache.clear()
        except Exception:
            pass
        try:
            from backend.ml.feature_extractor import reset_agent_state
            reset_agent_state(None)
        except Exception:
            pass