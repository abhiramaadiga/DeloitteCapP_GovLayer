"""
backend/core/kafka_producer.py
High-performance, Non-Blocking Kafka Telemetry Producer.
Publishes real-time NHI interaction events to 'agent.governance.events'.

Key Enterprise Features:
1. Zero-Latency Inline Impact: Asynchronous event publishing (adds <0.1ms to PEP).
2. Graceful Fallback Circuit Breaker: Automatically uses an in-memory ring buffer
   if Kafka broker is offline or unreachable, ensuring core banking is never blocked.
3. Open-Ended Schema: Standardized event schema with extensible metadata fields
   for future modules (Multi-agent delegation tracing, SIEM connectors, MLOps retraining).
"""
import json
import logging
import queue
import socket
import threading
import time
import uuid
from typing import Any, Dict, Optional

logger = logging.getLogger("agentic_iam.kafka_producer")

KAFKA_BOOTSTRAP_SERVERS = "localhost:9092"
KAFKA_TOPIC_TELEMETRY = "agent.governance.events"
KAFKA_TOPIC_ALERTS = "agent.alerts.v1"


class GovernanceTelemetryProducer:
    """
    Singleton Kafka Telemetry Producer with non-blocking dispatch and
    in-memory ring buffer fallback when broker is unreachable.
    """
    _instance = None
    _lock = threading.Lock()

    def __new__(cls, *args, **kwargs):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(GovernanceTelemetryProducer, cls).__new__(cls)
                cls._instance._initialized = False
            return cls._instance

    def __init__(
        self,
        bootstrap_servers: str = KAFKA_BOOTSTRAP_SERVERS,
        telemetry_topic: str = KAFKA_TOPIC_TELEMETRY,
        alerts_topic: str = KAFKA_TOPIC_ALERTS,
    ):
        if self._initialized:
            return

        self.bootstrap_servers = bootstrap_servers
        self.telemetry_topic = telemetry_topic
        self.alerts_topic = alerts_topic
        self.producer = None
        self.offline_queue: queue.Queue = queue.Queue(maxsize=10000)
        self._is_connected = False
        
        self._init_producer()
        self._initialized = True

    def _broker_reachable(self) -> bool:
        """TCP probe (<100ms timeout) to verify Kafka broker availability."""
        try:
            host, port_str = self.bootstrap_servers.split(",")[0].strip().split(":")
            with socket.create_connection((host, int(port_str)), timeout=0.10):
                return True
        except Exception:
            return False

    def _init_producer(self):
        """Initializes KafkaProducer or falls back gracefully to in-memory mode."""
        if not self._broker_reachable():
            logger.info("Kafka broker unreachable or offline. Operating in in-memory telemetry buffer mode.")
            self._is_connected = False
            return

        try:
            from kafka import KafkaProducer
            self.producer = KafkaProducer(
                bootstrap_servers=self.bootstrap_servers.split(","),
                value_serializer=lambda v: json.dumps(v).encode("utf-8"),
                key_serializer=lambda k: k.encode("utf-8") if k else None,
                acks=0,  # Fire-and-forget for telemetry streaming (<1ms)
                retries=1,
                max_block_ms=150,
            )
            self._is_connected = True
            logger.info(f"Connected to Kafka broker at {self.bootstrap_servers}. Telemetry topic: '{self.telemetry_topic}'")
        except Exception as e:
            logger.warning(f"Kafka client initialization failed ({e}). Falling back to in-memory queue.")
            self._is_connected = False
            self.producer = None

    def emit_event(
        self,
        agent_id: str,
        role: str,
        endpoint: str,
        method: str,
        governor_status: str,
        risk_score: float = 0.10,
        pep_latency_ms: float = 0.0,
        payload_preview: str = "",
        violation_reason: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Formats and dispatches an immutable telemetry event asynchronously.
        Leaves open ends in 'metadata' for future modules:
          - parent_agent_id (for multi-agent graph tracing)
          - compliance_tags (for SOX/FFIEC audit)
          - mfa_stepup_status (for adaptive verification)
        """
        event = {
            "event_id": str(uuid.uuid4()),
            "timestamp": time.time(),
            "timestamp_iso": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "agent_id": agent_id,
            "role": role,
            "endpoint": endpoint,
            "method": method.upper(),
            "governor_status": governor_status,  # "ALLOWED", "BLOCKED", "QUARANTINED"
            "risk_score": round(risk_score, 4),
            "pep_latency_ms": round(pep_latency_ms, 3),
            "payload_preview": payload_preview[:256] if payload_preview else "",
            "violation_reason": violation_reason,
            # Open-ended schema extension hook for future modules
            "metadata": metadata or {
                "trace_id": str(uuid.uuid4())[:8],
                "parent_agent_id": None,
                "session_depth": 1,
                "compliance_tags": ["SOX_404", "FFIEC_REVOCATION"],
                "model_version": "isolation_forest_v1",
            }
        }

        # Non-blocking dispatch
        threading.Thread(target=self._dispatch, args=(event,), daemon=True).start()
        return event

    def _dispatch(self, event: dict):
        """Asynchronously produces to Kafka topic or in-memory fallback queue."""
        if self._is_connected and self.producer:
            try:
                topic = self.alerts_topic if event["governor_status"] == "QUARANTINED" else self.telemetry_topic
                self.producer.send(topic, key=event["agent_id"], value=event)
                return
            except Exception as e:
                logger.error(f"Failed to publish event to Kafka: {e}. Storing in fallback queue.")

        # In-memory buffer fallback
        try:
            self.offline_queue.put_nowait(event)
        except queue.Full:
            self.offline_queue.get_nowait()
            self.offline_queue.put_nowait(event)


# Global singleton instance
telemetry_producer = GovernanceTelemetryProducer()
