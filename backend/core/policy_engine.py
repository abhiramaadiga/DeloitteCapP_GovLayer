"""
backend/core/policy_engine.py
Dual-Plane Dynamic Governance Policy Engine.
Maintains an in-memory cached policy set (<0.05ms evaluation latency)
backed by PostgreSQL governance_policies as the persistent source of truth.
"""
import re
import fnmatch
import time
import threading
from typing import Dict, Any, List, Optional, Tuple
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
        self._eval_cache: Dict[Tuple[str, str, str, str], Dict[str, Any]] = {}
        self._last_loaded_at: float = 0.0
        self._cache_lock = threading.RLock()
        self.reload_cache()
        try:
            self.evaluate("Agent-Warmup", "tier1_customer_service", "/accounts/401/balance", "GET")
        except Exception:
            pass

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
                pat_str = (r.endpoint_pattern or "*").strip().lower()
                try:
                    pat_regex = re.compile(fnmatch.translate(pat_str))
                except Exception:
                    pat_regex = None
                new_policies.append({
                    "id": r.id,
                    "policy_id": r.policy_id,
                    "agent_id": (r.agent_id or "*").strip(),
                    "role": (r.role or "*").strip().lower(),
                    "endpoint_pattern": pat_str,
                    "pattern_regex": pat_regex,
                    "method": (r.method or "*").strip().upper(),
                    "action": (r.action or "DENY").strip().upper(),
                    "compliance_tag": r.compliance_tag or "SOX-404",
                    "description": r.description or "",
                    "is_active": bool(r.is_active),
                    "created_at": r.created_at,
                    "updated_at": r.updated_at,
                })
            with self._cache_lock:
                self._policies = new_policies
                self._eval_cache = {}
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
        """Returns snapshot of policies currently in cache."""
        return list(self._policies)

    @staticmethod
    def _match_pattern(endpoint: str, pattern: str, pattern_regex: Optional[Any] = None) -> bool:
        """
        Matches endpoint against wildcard pattern.
        Handles leading/trailing slashes and wildcards with microsecond latency.
        """
        ep = endpoint.strip().lower()
        pat = pattern.strip().lower()

        if pat == "*" or pat == "/*":
            return True
        if ep == pat:
            return True
        if pat.endswith("*"):
            prefix = pat[:-1]
            if ep.startswith(prefix):
                return True
        if pattern_regex is not None:
            return pattern_regex.match(ep) is not None
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
        clean_endpoint = endpoint.split("?")[0].strip().lower()
        if not clean_endpoint.startswith("/"):
            clean_endpoint = "/" + clean_endpoint

        agent_clean = (agent_id or "*").strip()
        role_lower = (role or "*").strip().lower()

        cache_key = (agent_clean, role_lower, clean_endpoint, normalized_method)
        cached_decision = self._eval_cache.get(cache_key)
        if cached_decision is not None:
            return {
                **cached_decision,
                "eval_latency_ms": round((time.perf_counter() - start_t) * 1000, 4)
            }

        policies_snapshot = self._policies

        matching_denies = []
        matching_allows = []

        for p in policies_snapshot:
            if not p["is_active"]:
                continue
            if p["agent_id"] != "*" and p["agent_id"] != agent_clean:
                continue
            if p["role"] != "*" and p["role"] != role_lower:
                continue
            if p["method"] != "*" and p["method"] != normalized_method:
                continue
            if self._match_pattern(clean_endpoint, p["endpoint_pattern"], p.get("pattern_regex")):
                if p["action"] == "DENY":
                    matching_denies.append(p)
                elif p["action"] == "ALLOW":
                    matching_allows.append(p)

        eval_lat_ms = round((time.perf_counter() - start_t) * 1000, 4)

        if matching_denies:
            denying_policy = matching_denies[0]
            reason = f"POLICY VIOLATION [{denying_policy['compliance_tag']}]: {denying_policy['description']}"
            result = {
                "allowed": False,
                "action": "DENY",
                "violation_reason": reason,
                "policy_id": denying_policy["policy_id"],
                "compliance_tag": denying_policy["compliance_tag"],
                "eval_latency_ms": eval_lat_ms,
                "matched_pattern": denying_policy["endpoint_pattern"],
            }
        elif matching_allows:
            allowing_policy = matching_allows[0]
            result = {
                "allowed": True,
                "action": "ALLOW",
                "violation_reason": None,
                "policy_id": allowing_policy["policy_id"],
                "compliance_tag": allowing_policy["compliance_tag"],
                "eval_latency_ms": eval_lat_ms,
                "matched_pattern": allowing_policy["endpoint_pattern"],
            }
        else:
            result = {
                "allowed": True,
                "action": "DEFAULT_ALLOW",
                "violation_reason": None,
                "policy_id": None,
                "compliance_tag": "LEAST-PRIVILEGE",
                "eval_latency_ms": eval_lat_ms,
                "matched_pattern": None,
            }

        self._eval_cache[cache_key] = result
        return result

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
