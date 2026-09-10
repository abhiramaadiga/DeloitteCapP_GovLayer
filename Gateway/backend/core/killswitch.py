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
        
        return record

    @staticmethod
    def lift_quarantine(agent_id: str, justification: str, analyst_id: str) -> Dict[str, Any]:
        """Regulatory requirement: Un-quarantine requires human justification."""
        if not justification or len(justification.strip()) < 5:
            raise ValueError("FFIEC Compliance: Justification must be provided to lift quarantine.")
            
        RevocationCache.delete(f"revoked:agent:{agent_id}")
        return {
            "agent_id": agent_id,
            "status": "ACTIVE",
            "action": "QUARANTINE_LIFTED",
            "analyst_id": analyst_id,
            "justification": justification,
            "timestamp": int(time.time())
        }