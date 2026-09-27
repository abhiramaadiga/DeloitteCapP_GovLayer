"""
backend/ml/kafka_consumer.py
Enterprise Kafka Telemetry & ML Governance Consumer.
Monitors real-time agent behavioral telemetry for:
1. Continuous ML Concept Shift & Feature Drift Detection
2. Real-time Security Audit & Incident Alerting (XAI causal tracking)
3. Online ML Feedback Loop & RLHF Retraining Buffer
4. Graceful In-Memory Fallback when Kafka broker is offline.
"""
import json
import logging
import queue
import socket
import threading
import time
import uuid
from collections import Counter, defaultdict, deque
from typing import Any, Callable, Dict, List, Optional, Union

from backend.core.config import settings
from backend.core.kafka_producer import telemetry_producer

logger = logging.getLogger("agentic_iam.kafka_consumer")


class GovernanceEventConsumer:
    """
    Kafka consumer and telemetry processing engine for Non-Human Identity (NHI) governance.
    Analyzes telemetry events emitted by the Zero-Trust Gateway PEP:
      - agent_id, role, endpoint, method
      - risk_score, governor_status, pep_latency_ms, xai_factors
    Detects feature drift, tracks security alerts, and maintains retraining buffers.
    """

    # Baseline benchmarks from benign synthetic training
    BASELINE_MEAN_RISK = 0.15
    BASELINE_ANOMALY_RATE = 0.05
    BASELINE_MAX_PEP_LATENCY = 5.0

    def __init__(
        self,
        bootstrap_servers: Optional[str] = None,
        topics: Optional[Union[str, List[str]]] = None,
        group_id: Optional[str] = None,
        on_event: Optional[Callable[[dict], dict]] = None,
        window_size: int = 100,
        drift_anomaly_threshold: float = 0.20,
        drift_risk_shift_threshold: float = 0.25,
    ):
        self.bootstrap_servers = bootstrap_servers or settings.KAFKA_BOOTSTRAP_SERVERS
        if topics is None:
            self.topics = [settings.KAFKA_TOPIC_TELEMETRY, settings.KAFKA_TOPIC_ALERTS, "agent.governance.events"]
        elif isinstance(topics, str):
            self.topics = [topics]
        else:
            self.topics = list(topics)

        self.group_id = group_id or settings.KAFKA_GROUP_ID
        self.on_event = on_event
        self.window_size = window_size
        self.drift_anomaly_threshold = drift_anomaly_threshold
        self.drift_risk_shift_threshold = drift_risk_shift_threshold

        # Processing & Metrics State
        self.total_processed: int = 0
        self.status_counts: Dict[str, int] = {"ALLOWED": 0, "BLOCKED": 0, "QUARANTINED": 0}
        self.recent_events: deque = deque(maxlen=self.window_size)
        self.security_alerts: deque = deque(maxlen=200)
        self.drift_alerts: deque = deque(maxlen=100)
        self.retraining_feedback_buffer: deque = deque(maxlen=500)
        self.agent_violations: Dict[str, int] = defaultdict(int)
        self._processed_ids: deque = deque(maxlen=2000)
        self._processed_ids_set: set = set()

        # Threading & Kafka State
        self.kafka_consumer = None
        self.fallback_queue: queue.Queue = queue.Queue(maxsize=10000)
        self._running = False
        self._worker_thread: Optional[threading.Thread] = None
        self._lock = threading.RLock()

        # Connect to Kafka or fallback
        self._init_kafka()

        # Register consumer to receive offline telemetry events from the producer
        telemetry_producer.add_fallback_listener(self.enqueue_event)

    @property
    def topic(self) -> str:
        """Backwards compatibility for single topic access."""
        return self.topics[0] if self.topics else settings.KAFKA_TOPIC_TELEMETRY

    def _broker_reachable(self) -> bool:
        """Fast TCP socket probe (<150ms) to check if Kafka broker is up."""
        try:
            host, port_str = self.bootstrap_servers.split(",")[0].strip().split(":")
            with socket.create_connection((host, int(port_str)), timeout=0.15):
                return True
        except Exception:
            return False

    def _init_kafka(self):
        """Initializes Kafka consumer or falls back to in-memory mode."""
        if not self._broker_reachable():
            logger.info("Kafka broker unreachable or offline. Operating in in-memory queue fallback mode.")
            self.kafka_consumer = None
            return

        try:
            from kafka import KafkaConsumer
            try:
                from kafka.serializer import DeserializeWrapper
                val_deser = DeserializeWrapper(lambda m: json.loads(m.decode("utf-8")))
            except Exception:
                val_deser = lambda m: json.loads(m.decode("utf-8"))

            self.kafka_consumer = KafkaConsumer(
                *self.topics,
                bootstrap_servers=self.bootstrap_servers.split(","),
                group_id=self.group_id,
                value_deserializer=val_deser,
                auto_offset_reset="latest",
                enable_auto_commit=True,
                consumer_timeout_ms=1000,
            )
            logger.info(
                f"Connected to Kafka broker at {self.bootstrap_servers} (topics: {self.topics}, group: {self.group_id})"
            )
        except Exception as e:
            logger.warning(f"Kafka consumer initialization failed ({e}). Operating in in-memory fallback mode.")
            self.kafka_consumer = None

    # ---- In-memory queue fallback API ----

    def enqueue_event(self, event: dict):
        """
        Pushes an event into the fallback queue.
        Called when Kafka is offline or during testing.
        """
        try:
            self.fallback_queue.put_nowait(event)
        except queue.Full:
            try:
                self.fallback_queue.get_nowait()
            except queue.Empty:
                pass
            self.fallback_queue.put_nowait(event)

    # ---- Core Telemetry & ML Processing Pipeline ----

    def process_event(self, event: dict) -> Dict[str, Any]:
        """
        Processes an incoming telemetry event:
        1. Ingests and sanitizes fields (agent_id, endpoint, risk_score, governor_status, pep_latency_ms, xai_factors).
        2. Updates streaming metrics & rolling window.
        3. Runs real-time feature & concept drift detection.
        4. Generates security audit alerts for violations.
        5. Buffers feedback samples for RLHF / model recalibration.
        """
        with self._lock:
            event_id = str(event.get("event_id") or uuid.uuid4())
            if event_id in self._processed_ids_set:
                return {"event_id": event_id, "status": "DUPLICATE_IGNORED", "drift_detected": False}
            self._processed_ids.append(event_id)
            self._processed_ids_set.add(event_id)
            if len(self._processed_ids) > 2000:
                old_id = self._processed_ids.popleft()
                self._processed_ids_set.discard(old_id)

            self.total_processed += 1
            raw_status = event.get("governor_status")
            status = (raw_status or "ALLOWED").upper()
            if status in self.status_counts:
                self.status_counts[status] += 1
            else:
                self.status_counts[status] = 1

            agent_id = event.get("agent_id") or "unknown"
            endpoint = event.get("endpoint") or "/unknown"
            method = (event.get("method") or "GET").upper()

            raw_risk = event.get("risk_score")
            risk_score = float(raw_risk) if raw_risk is not None else 0.10

            raw_latency = event.get("pep_latency_ms")
            pep_latency_ms = float(raw_latency) if raw_latency is not None else 0.0

            xai_factors = event.get("xai_factors") or ([event.get("violation_reason")] if event.get("violation_reason") else [])

            record = {
                "event_id": event_id,
                "timestamp": event.get("timestamp") or time.time(),
                "agent_id": agent_id,
                "role": event.get("role") or "unknown",
                "endpoint": endpoint,
                "method": method,
                "governor_status": status,
                "risk_score": risk_score,
                "pep_latency_ms": pep_latency_ms,
                "xai_factors": xai_factors,
                "violation_reason": event.get("violation_reason"),
            }
            self.recent_events.append(record)

            # 1. Security Alerting
            is_quarantined = (status == "QUARANTINED")
            is_blocked = (status == "BLOCKED")
            is_high_risk = (risk_score >= 0.75)

            if is_quarantined or is_blocked or is_high_risk:
                self.agent_violations[agent_id] += 1
                severity = "CRITICAL" if is_quarantined else ("HIGH" if is_high_risk else "MEDIUM")
                alert = {
                    "alert_id": str(uuid.uuid4())[:8],
                    "timestamp": time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime(record["timestamp"])),
                    "severity": severity,
                    "agent_id": agent_id,
                    "endpoint": endpoint,
                    "governor_status": status,
                    "risk_score": risk_score,
                    "xai_factors": xai_factors,
                    "violation_reason": record["violation_reason"] or f"Risk score {risk_score} exceeded threshold",
                    "consecutive_violations": self.agent_violations[agent_id],
                }
                self.security_alerts.append(alert)

                # Flag multi-violation attack campaigns
                if self.agent_violations[agent_id] >= 3:
                    campaign_alert = {
                        "alert_id": str(uuid.uuid4())[:8],
                        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime()),
                        "severity": "CRITICAL",
                        "type": "ATTACK_CAMPAIGN_DETECTED",
                        "agent_id": agent_id,
                        "endpoint": endpoint,
                        "message": f"Agent '{agent_id}' triggered {self.agent_violations[agent_id]} security violations. Potential automated adversarial exploitation.",
                    }
                    self.security_alerts.append(campaign_alert)

            # 2. ML Feedback & RLHF Buffer
            raw_meta = event.get("metadata")
            meta = raw_meta if isinstance(raw_meta, dict) else {}
            flagged_for_rlhf = bool(meta.get("flagged_for_rlhf", False))

            if is_blocked or (0.55 <= risk_score < 0.75) or flagged_for_rlhf:
                self.retraining_feedback_buffer.append({
                    "event_id": record["event_id"],
                    "agent_id": agent_id,
                    "endpoint": endpoint,
                    "method": method,
                    "risk_score": risk_score,
                    "xai_factors": xai_factors,
                    "feedback_type": "BLOCKED_OR_BORDERLINE",
                    "timestamp": record["timestamp"],
                })

            # 3. Concept Drift & Feature Shift Detection
            drift_report = self._check_drift()

            result = {
                "event_id": record["event_id"],
                "status": status,
                "risk_score": risk_score,
                "xai_factors": xai_factors,
                "drift_detected": drift_report["drift_detected"],
            }

            if self.on_event:
                try:
                    self.on_event(event)
                except Exception as e:
                    logger.error(f"Error in on_event callback: {e}")

            return result

    def _check_drift(self) -> Dict[str, Any]:
        """
        Evaluates statistical properties of the rolling telemetry window.
        Triggers drift alerts if anomaly rate or average risk score deviates significantly from baseline.
        """
        count = len(self.recent_events)
        if count < 10:
            return {
                "drift_detected": False,
                "sample_count": count,
                "mean_risk": round(sum(e["risk_score"] for e in self.recent_events) / count, 4) if count > 0 else self.BASELINE_MEAN_RISK,
                "anomaly_rate": round(sum(1 for e in self.recent_events if e["risk_score"] >= 0.75 or e["governor_status"] == "QUARANTINED") / count, 4) if count > 0 else 0.0,
                "reasons": [],
                "reason": "Insufficient samples for drift evaluation",
            }

        scores = [e["risk_score"] for e in self.recent_events]
        mean_risk = sum(scores) / count
        anomalies = sum(1 for e in self.recent_events if e["risk_score"] >= 0.75 or e["governor_status"] == "QUARANTINED")
        anomaly_rate = anomalies / count

        reasons = []
        drift_detected = False

        if anomaly_rate > self.drift_anomaly_threshold:
            drift_detected = True
            reasons.append(
                f"ANOMALY_RATE_SPIKE: Current rolling anomaly rate {anomaly_rate:.1%} exceeds threshold {self.drift_anomaly_threshold:.1%} (baseline: {self.BASELINE_ANOMALY_RATE:.1%})"
            )

        risk_shift = mean_risk - self.BASELINE_MEAN_RISK
        if risk_shift > self.drift_risk_shift_threshold:
            drift_detected = True
            reasons.append(
                f"MEAN_RISK_ELEVATION: Rolling mean risk score {mean_risk:.3f} shifted by +{risk_shift:.3f} above baseline {self.BASELINE_MEAN_RISK:.3f}"
            )

        if drift_detected:
            drift_alert = {
                "drift_id": str(uuid.uuid4())[:8],
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime()),
                "sample_count": count,
                "mean_risk": round(mean_risk, 4),
                "anomaly_rate": round(anomaly_rate, 4),
                "reasons": reasons,
            }
            if not self.drift_alerts or self.drift_alerts[-1]["reasons"] != reasons:
                self.drift_alerts.append(drift_alert)
                logger.warning(f"[ML Drift Alert] {'; '.join(reasons)}")

        return {
            "drift_detected": drift_detected,
            "sample_count": count,
            "mean_risk": round(mean_risk, 4),
            "anomaly_rate": round(anomaly_rate, 4),
            "reasons": reasons,
        }

    def get_metrics(self) -> Dict[str, Any]:
        """Returns comprehensive real-time telemetry metrics and drift status."""
        with self._lock:
            count = len(self.recent_events)
            if count > 0:
                scores = [e["risk_score"] for e in self.recent_events]
                latencies = [e["pep_latency_ms"] for e in self.recent_events]
                mean_risk = round(sum(scores) / count, 4)
                mean_latency = round(sum(latencies) / count, 2)
                anomalies = sum(1 for e in self.recent_events if e["risk_score"] >= 0.75 or e["governor_status"] == "QUARANTINED")
                anomaly_rate = round(anomalies / count, 4)
            else:
                mean_risk = self.BASELINE_MEAN_RISK
                mean_latency = 0.0
                anomaly_rate = 0.0

            drift_info = self._check_drift()

            return {
                "consumer_active": self._running,
                "kafka_connected": self.kafka_consumer is not None,
                "bootstrap_servers": self.bootstrap_servers,
                "topics": self.topics,
                "total_events_processed": self.total_processed,
                "status_counts": dict(self.status_counts),
                "rolling_window": {
                    "size": self.window_size,
                    "current_samples": count,
                    "mean_risk_score": mean_risk,
                    "mean_pep_latency_ms": mean_latency,
                    "anomaly_rate": anomaly_rate,
                },
                "drift_monitoring": {
                    "drift_detected": drift_info["drift_detected"],
                    "baseline_mean_risk": self.BASELINE_MEAN_RISK,
                    "baseline_anomaly_rate": self.BASELINE_ANOMALY_RATE,
                    "recent_drift_alerts": list(self.drift_alerts)[-5:],
                },
                "alerts": {
                    "total_security_alerts": len(self.security_alerts),
                    "recent_security_alerts": list(self.security_alerts)[-5:],
                },
                "retraining_buffer": {
                    "buffered_samples": len(self.retraining_feedback_buffer),
                    "capacity": self.retraining_feedback_buffer.maxlen,
                },
            }

    def get_drift_report(self) -> Dict[str, Any]:
        """Provides in-depth drift analysis and retraining recommendations."""
        with self._lock:
            metrics = self.get_metrics()
            drift_detected = metrics["drift_monitoring"]["drift_detected"]
            recommendation = (
                "TRIGGER_RETRAINING: Severe concept/feature drift observed. Execute backend/ml/model_trainer.py to adapt baseline."
                if drift_detected
                else "MODEL_STABLE: Telemetry conforms to baseline benign distribution. No retraining required."
            )
            return {
                "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                "status": "DRIFT_DETECTED" if drift_detected else "STABLE",
                "recommendation": recommendation,
                "metrics": metrics["rolling_window"],
                "drift_alerts": list(self.drift_alerts)[-10:],
                "retraining_samples_ready": len(self.retraining_feedback_buffer),
            }

    def trigger_retraining(self, max_samples: Optional[int] = None) -> Dict[str, Any]:
        """
        Triggers model retraining using buffered feedback samples from the telemetry consumer.
        Updates the active model in risk_engine upon completion.
        """
        with self._lock:
            samples = list(self.retraining_feedback_buffer)
            if max_samples:
                samples = samples[-max_samples:]
            self.retraining_feedback_buffer.clear()

        from backend.ml.model_trainer import retrain_with_feedback
        return retrain_with_feedback(feedback_samples=samples, save=True)

    def reset_state(self):
        """Clears buffers and resets counters (useful for unit testing)."""
        with self._lock:
            self.total_processed = 0
            self.status_counts = {"ALLOWED": 0, "BLOCKED": 0, "QUARANTINED": 0}
            self.recent_events.clear()
            self.security_alerts.clear()
            self.drift_alerts.clear()
            self.retraining_feedback_buffer.clear()
            self.agent_violations.clear()
            self._processed_ids.clear()
            self._processed_ids_set.clear()
            while not self.fallback_queue.empty():
                try:
                    self.fallback_queue.get_nowait()
                except queue.Empty:
                    break

    # ---- Background Worker Loop ----

    def _worker_loop(self):
        """
        Unified background worker loop:
        1. Drains in-memory fallback queue without latency.
        2. Polls Kafka topics for real-time telemetry if broker is connected.
        3. Recovers and automatically reconnects to Kafka if broker restarts or becomes available.
        """
        logger.info(f"Governance event consumer worker loop started (topics: {self.topics}).")
        last_reconnect_probe = 0.0
        while self._running:
            # 1. Drain fallback queue
            try:
                while not self.fallback_queue.empty():
                    event = self.fallback_queue.get_nowait()
                    self.process_event(event)
            except Exception as e:
                logger.error(f"Fallback queue processing error: {e}")

            # 2. Poll Kafka if active
            if self.kafka_consumer:
                try:
                    records = self.kafka_consumer.poll(timeout_ms=500)
                    for topic_partition, messages in records.items():
                        for message in messages:
                            if not self._running:
                                break
                            self.process_event(message.value)
                except Exception as e:
                    logger.warning(f"Kafka consume error ({e}). Entering fallback and probing reconnect.")
                    try:
                        self.kafka_consumer.close(timeout=0.5)
                    except Exception:
                        pass
                    self.kafka_consumer = None
            else:
                # 3. If Kafka not connected, periodically probe for broker availability
                now = time.time()
                if now - last_reconnect_probe > 5.0:
                    last_reconnect_probe = now
                    if self._broker_reachable():
                        try:
                            self._init_kafka()
                        except Exception:
                            pass
                time.sleep(0.2)

    def start(self):
        """Starts the consumer background thread."""
        if self._running:
            return
        self._running = True
        self._worker_thread = threading.Thread(target=self._worker_loop, daemon=True, name="KafkaGovernanceConsumerThread")
        self._worker_thread.start()
        logger.info(f"Governance event consumer started (mode: {'KAFKA' if self.kafka_consumer else 'IN-MEMORY-FALLBACK'}).")

    def stop(self):
        """Gracefully stops the consumer."""
        self._running = False
        if self._worker_thread:
            self._worker_thread.join(timeout=3.0)
            self._worker_thread = None
        if self.kafka_consumer:
            try:
                self.kafka_consumer.close(timeout=1.0)
            except Exception:
                pass
            self.kafka_consumer = None
        logger.info("Governance event consumer stopped.")

    def reset_metrics(self):
        """Resets telemetry counts, alerts, drift status, and retraining buffers to baseline."""
        with self._lock:
            self.total_processed = 0
            self.status_counts = {"ALLOWED": 0, "BLOCKED": 0, "QUARANTINED": 0}
            self.recent_events.clear()
            self.security_alerts.clear()
            self.drift_alerts.clear()
            self.retraining_feedback_buffer.clear()
            self.agent_violations.clear()
            self._processed_ids.clear()
            self._processed_ids_set.clear()
            while not self.fallback_queue.empty():
                try:
                    self.fallback_queue.get_nowait()
                except Exception:
                    break
        logger.info("Governance consumer metrics reset to baseline.")



# Global Singleton Instance
governance_consumer = GovernanceEventConsumer()


def start_telemetry_consumer():
    """Convenience helper to start the global telemetry consumer."""
    governance_consumer.start()


def stop_telemetry_consumer():
    """Convenience helper to stop the global telemetry consumer."""
    governance_consumer.stop()


def get_consumer_metrics() -> Dict[str, Any]:
    """Fetches metrics from the global consumer."""
    return governance_consumer.get_metrics()


def get_drift_report() -> Dict[str, Any]:
    """Fetches drift report from the global consumer."""
    return governance_consumer.get_drift_report()


if __name__ == "__main__":
    def _print_result(event):
        print(f"[CONSUMED] {event.get('agent_id')} -> {event.get('endpoint')} | Status: {event.get('governor_status')}")

    consumer = GovernanceEventConsumer(on_event=_print_result)
    consumer.start()
    print("Governance consumer running. Press Ctrl+C to stop.")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        consumer.stop()
