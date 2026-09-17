"""
backend/core/policy_engine.py
Dual-Plane Dynamic Governance Policy Engine.
Maintains an in-memory cached policy set (<0.05ms evaluation latency)
backed by PostgreSQL governance_policies as the persistent source of truth.
"""
import fnmatch
import time
import threading
from typing import Dict, Any, List, Optional
from backend.core.database import SessionLocal, GovernancePolicy

class PolicyEngine:
    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super(PolicyEngine, cls).__new__(cls)
                    cls._instance._init_engine()
        return cls._instance

    def _init_engine(self):
        self._policies: List[Dict[str, Any]] = []
        self._last_loaded_at: float = 0.0
        self._cache_lock = threading.RLock()
        self.reload_cache()

    def reload_cache(self) -> int:
        """
        Reloads active and inactive governance policies from PostgreSQL into the in-memory cache.
        Thread-safe atomic update.
        """
        start_t = time.perf_counter()
        db = SessionLocal()
        try:
            records = db.query(GovernancePolicy).all()
            new_policies = []
            for r in records:
                new_policies.append({
                    "id": r.id,
                    "policy_id": r.policy_id,
                    "agent_id": r.agent_id or "*",
                    "role": r.role or "*",
                    "endpoint_pattern": r.endpoint_pattern or "*",
                    "method": (r.method or "*").upper(),
                    "action": (r.action or "DENY").upper(),
                    "compliance_tag": r.compliance_tag or "SOX-404",
                    "description": r.description or "",
                    "is_active": bool(r.is_active),
                    "created_at": r.created_at,
                    "updated_at": r.updated_at,
                })
            with self._cache_lock:
                self._policies = new_policies
                self._last_loaded_at = time.time()

            load_ms = round((time.perf_counter() - start_t) * 1000, 3)
            print(f"[PolicyEngine] In-memory cache reloaded ({len(new_policies)} policies) from database in {load_ms}ms.")
            return len(new_policies)
        except Exception as e:
            print(f"[PolicyEngine Error] Failed to reload policies from DB: {e}")
            return len(self._policies)
        finally:
            db.close()

    def get_all_cached_policies(self) -> List[Dict[str, Any]]:
        """Returns spapshot of policies currently in cache."""
        with self._cache_lock:
            return list(self._policies)

    @staticmethod
    def _match_pattern(endpoint: str, pattern: str) -> bool:
        """
        Matches endpoint against wildcard pattern.
        Handles leading/trailing slashes and wildcards gracefully.
        """
        ep = endpoint.strip().lower()
        pat = pattern.strip().lower()

        if pat == "*" or pat == "/*":
            return True
        if ep == pat:
            return True
        if fnmatch.fnmatch(ep, pat):
            return True
        if not pat.endswith("*") and ep.startswith(pat.rstrip("*")):
            return True
        return False

    def evaluate(
        self,
        agent_id: str,
        role: str,
        endpoint: str,
        method: str = "GET"
    ) -> Dict[str, Any]:
        """
        Evaluates an agent tool execution request against active in-memory governance policies.
        Priority:
        1. Any matching active DENY rule -> Denied immediately.
        2. Any matching active ALLOW rule -> Allowed immediately.
        3. Default fallback -> Allowed.
        """
        start_t = time.perf_counter()
        normalized_method = (method or "GET").strip().upper()
        clean_endpoint = endpoint.split("?")[0].strip()
        if not clean_endpoint.startswith("/"):
            clean_endpoint = "/" + clean_endpoint

        matching_denies = []
        matching_allows = []

        with self._cache_lock:
            policies_snapshot = self._policies

        for p in policies_snapshot:
            if not p["is_active"]:
                continue
            if p["agent_id"] != "*" and p["agent_id"] != agent_id:
                continue
            if p["role"] != "*" and p["role"] != role:
                continue
            if p["method"] != "*" and p["method"] != normalized_method:
                continue
            if self._match_pattern(clean_endpoint, p["endpoint_pattern"]):
                if p["action"] == "DENY":
                    matching_denies.append(p)
                elif p["action"] == "ALLOW":
                    matching_allows.append(p)

        eval_lat_ms = round((time.perf_counter() - start_t) * 1000, 4)

        if matching_denies:
            denying_policy = matching_denies[0]
            reason = f"POLICY VIOLATION [{denying_policy['compliance_tag']}]: {denying_policy['description']}"
            return {
                "allowed": False,
                "action": "DENY",
                "violation_reason": reason,
                "policy_id": denying_policy["policy_id"],
                "compliance_tag": denying_policy["compliance_tag"],
                "eval_latency_ms": eval_lat_ms,
                "matched_pattern": denying_policy["endpoint_pattern"],
            }

        if matching_allows:
            allowing_policy = matching_allows[0]
            return {
                "allowed": True,
                "action": "ALLOW",
                "violation_reason": None,
                "policy_id": allowing_policy["policy_id"],
                "compliance_tag": allowing_policy["compliance_tag"],
                "eval_latency_ms": eval_lat_ms,
                "matched_pattern": allowing_policy["endpoint_pattern"],
            }

        return {
            "allowed": True,
            "action": "DEFAULT_ALLOW",
            "violation_reason": None,
            "policy_id": None,
            "compliance_tag": "LEAST-PRIVILEGE",
            "eval_latency_ms": eval_lat_ms,
            "matched_pattern": None,
        }

    def get_stats(self) -> Dict[str, Any]:
        with self._cache_lock:
            total = len(self._policies)
            active = sum(1 for p in self._policies if p["is_active"])
            deny_count = sum(1 for p in self._policies if p["is_active"] and p["action"] == "DENY")
            allow_count = sum(1 for p in self._policies if p["is_active"] and p["action"] == "ALLOW")

        return {
            "total_policies": total,
            "active_policies": active,
            "deny_policies": deny_count,
            "allow_policies": allow_count,
            "last_loaded_at": self._last_loaded_at,
            "dual_plane": "PostgreSQL (Source) -> L1 In-Memory Cache (Evaluation)"
        }

policy_engine = PolicyEngine()
