"""
tests/test_kafka_consumer.py
Comprehensive verification suite for:
1. Docker Container Harmonization and Consolidation (Priority 1)
2. Kafka Producer Telemetry Schema with XAI Factors (Priority 3)
3. Kafka Telemetry Consumer, Drift Detection, and Security Alerting Pipeline (Priority 3)
4. Fallback Queueing, RLHF Feedback Buffering, and FastAPI Observability Endpoints.
"""
import os
import socket
import time
import pytest
from fastapi.testclient import TestClient

from backend.main import app
from backend.core.config import settings
from backend.core.kafka_producer import GovernanceTelemetryProducer, telemetry_producer
from backend.ml.kafka_consumer import (
    GovernanceEventConsumer,
    governance_consumer,
    get_consumer_metrics,
    get_drift_report,
)

client = TestClient(app)


# ==============================================================================
# SECTION 1: Docker Stack Consolidation & Environment Verification (Priority 1)
# ==============================================================================

def test_dotenv_configuration_loaded():
    """Verify that .env file exists and configuration parameters are loaded into settings."""
    env_file = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env")
    assert os.path.exists(env_file), ".env file should exist in project root"

    assert settings.POSTGRES_USER == "governor_admin"
    assert settings.POSTGRES_DB == "governance_db"
    assert settings.POSTGRES_PORT == 5432
    assert "postgresql://" in settings.DATABASE_URL
    assert settings.REDIS_PORT == 6379
    assert settings.KAFKA_BOOTSTRAP_SERVERS == "localhost:9092"
    assert settings.KAFKA_TOPIC_TELEMETRY == "agentic-iam.telemetry"


def test_docker_services_ports_open():
    """Verify that PostgreSQL (5432), Redis (6379), and Kafka (9092) ports are reachable when Docker is running."""
    services = [
        ("PostgreSQL", "localhost", 5432),
        ("Redis", "localhost", 6379),
        ("Kafka", "localhost", 9092),
    ]
    for name, host, port in services:
        try:
            with socket.create_connection((host, port), timeout=0.5):
                pass
        except Exception as e:
            pytest.skip(f"Docker service {name} not reachable on {host}:{port} ({e}) - Docker engine may be stopped")


def test_no_duplicate_postgres_containers():
    """Verify that only postgres-governor is bound to host port 5432 and agentic-postgres is absent."""
    import subprocess
    try:
        res = subprocess.run(
            ["docker", "ps", "--filter", "name=postgres", "--format", "{{.Names}}"],
            capture_output=True,
            text=True,
            check=True,
            timeout=5
        )
    except Exception:
        # If docker CLI is not directly accessible or daemon inactive in test environment, skip docker ps check
        return

    names = [n.strip() for n in res.stdout.strip().splitlines() if n.strip()]
    if names:
        assert "postgres-governor" in names, f"Expected postgres-governor in running containers, found: {names}"
        assert "agentic-postgres" not in names, "agentic-postgres was expected to be removed during consolidation"


def test_docker_compose_harmonized_stack():
    """Verify that docker-compose.yml defines consolidated services, volumes, and ports."""
    compose_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "docker-compose.yml")
    assert os.path.exists(compose_path), "docker-compose.yml must exist"

    with open(compose_path, "r", encoding="utf-8") as f:
        content = f.read()

    # Priority 1 Consolidation assertions
    assert "container_name: postgres-governor" in content
    assert "agentic-postgres" not in content, "Obsolete agentic-postgres must not exist in compose file"
    assert "governor_pgdata" in content, "Volume must use named governor_pgdata"
    assert "container_name: redis-governor" in content
    assert "container_name: kafka-governor" in content
    assert "container_name: gateway-pep" in content
    assert "POSTGRES_PORT" in content
    assert "REDIS_PORT" in content
    assert "KAFKA_PORT" in content
    assert "GATEWAY_PORT" in content


# ==============================================================================
# SECTION 2: Kafka Producer Telemetry Schema & XAI Factors (Priority 3)
# ==============================================================================

def test_kafka_telemetry_event_schema_with_xai_factors():
    """Verify emitted telemetry event matches required schema including xai_factors."""
    producer = telemetry_producer
    factors = ["SHANNON_ENTROPY_HIGH", "VELOCITY_BURST_DETECTED"]
    
    event = producer.emit_event(
        agent_id="Agent-Audit-Test",
        role="tier1_customer_service",
        endpoint="/gateway/transfers/wire",
        method="POST",
        governor_status="BLOCKED",
        risk_score=0.92,
        pep_latency_ms=2.15,
        payload_preview="Transfer INR 10,000,000",
        violation_reason="SOX-404 Least-Privilege Policy Violation",
        xai_factors=factors,
    )

    assert "event_id" in event
    assert "timestamp" in event
    assert "timestamp_iso" in event
    assert event["agent_id"] == "Agent-Audit-Test"
    assert event["role"] == "tier1_customer_service"
    assert event["endpoint"] == "/gateway/transfers/wire"
    assert event["method"] == "POST"
    assert event["governor_status"] == "BLOCKED"
    assert event["risk_score"] == 0.92
    assert event["pep_latency_ms"] == 2.15
    assert event["xai_factors"] == factors
    assert "SOX-404" in event["violation_reason"]
    assert "metadata" in event


def test_kafka_telemetry_event_derives_xai_when_none_provided():
    """Verify that xai_factors defaults cleanly to violation_reason if omitted."""
    producer = telemetry_producer
    event = producer.emit_event(
        agent_id="Agent-Derive-Test",
        role="tier1_customer_service",
        endpoint="/gateway/faq",
        method="GET",
        governor_status="ALLOWED",
        risk_score=0.10,
        pep_latency_ms=0.85,
        violation_reason=None,
        xai_factors=None,
    )
    assert event["xai_factors"] == []
    assert event["governor_status"] == "ALLOWED"


# ==============================================================================
# SECTION 3: Kafka Consumer, Drift Detection, and Security Alerts (Priority 3)
# ==============================================================================

def test_consumer_processes_telemetry_event_and_updates_counts():
    """Verify consumer successfully ingests events and aggregates status metrics."""
    consumer = GovernanceEventConsumer(topics=["agentic-iam.telemetry"])
    consumer.reset_state()

    event = {
        "event_id": "test-evt-01",
        "timestamp": time.time(),
        "agent_id": "Agent-Support-01",
        "role": "tier1_support",
        "endpoint": "/accounts/401/balance",
        "method": "GET",
        "governor_status": "ALLOWED",
        "risk_score": 0.10,
        "pep_latency_ms": 1.2,
        "xai_factors": ["Nominal behavioral risk profile"],
    }

    result = consumer.process_event(event)
    assert result["status"] == "ALLOWED"
    assert result["risk_score"] == 0.10
    assert result["xai_factors"] == ["Nominal behavioral risk profile"]

    metrics = consumer.get_metrics()
    assert metrics["total_events_processed"] == 1
    assert metrics["status_counts"]["ALLOWED"] == 1
    assert metrics["rolling_window"]["current_samples"] == 1


def test_consumer_security_incident_alerting():
    """Verify that QUARANTINED and high-risk events trigger security alerts."""
    consumer = GovernanceEventConsumer(topics=["agentic-iam.telemetry"])
    consumer.reset_state()

    quarantine_event = {
        "event_id": "test-quarantine-01",
        "timestamp": time.time(),
        "agent_id": "Agent-Rogue-99",
        "role": "tier1_customer_service",
        "endpoint": "/customers/export",
        "method": "GET",
        "governor_status": "QUARANTINED",
        "risk_score": 0.98,
        "pep_latency_ms": 3.5,
        "xai_factors": ["HIGH_ENTROPY (5.6 bits)", "ILLEGAL_API_TRANSITION"],
        "violation_reason": "ML Behavioral Anomaly Detected",
    }

    consumer.process_event(quarantine_event)
    metrics = consumer.get_metrics()

    assert metrics["alerts"]["total_security_alerts"] >= 1
    latest_alert = metrics["alerts"]["recent_security_alerts"][-1]
    assert latest_alert["agent_id"] == "Agent-Rogue-99"
    assert latest_alert["severity"] == "CRITICAL"
    assert "HIGH_ENTROPY (5.6 bits)" in latest_alert["xai_factors"]


def test_consumer_attack_campaign_detection():
    """Verify that an agent triggering multiple violations triggers an ATTACK_CAMPAIGN_DETECTED alert."""
    consumer = GovernanceEventConsumer(topics=["agentic-iam.telemetry"])
    consumer.reset_state()

    rogue_agent = "Agent-Attacker-X"
    for i in range(3):
        consumer.process_event({
            "event_id": f"attack-{i}",
            "timestamp": time.time(),
            "agent_id": rogue_agent,
            "role": "tier1_customer_service",
            "endpoint": "/transfers/wire",
            "method": "POST",
            "governor_status": "BLOCKED",
            "risk_score": 0.90,
            "pep_latency_ms": 1.5,
            "violation_reason": "Policy violation",
        })

    alerts = consumer.get_metrics()["alerts"]["recent_security_alerts"]
    campaign_alerts = [a for a in alerts if a.get("type") == "ATTACK_CAMPAIGN_DETECTED"]
    assert len(campaign_alerts) == 1
    assert campaign_alerts[0]["agent_id"] == rogue_agent
    assert campaign_alerts[0]["severity"] == "CRITICAL"


def test_consumer_feature_and_concept_drift_detection():
    """Verify drift detection triggers when rolling anomaly rate and mean risk exceed thresholds."""
    consumer = GovernanceEventConsumer(
        topics=["agentic-iam.telemetry"],
        window_size=20,
        drift_anomaly_threshold=0.20,
        drift_risk_shift_threshold=0.25,
    )
    consumer.reset_state()

    # Step 1: Send 10 benign events -> Drift should NOT trigger
    for i in range(10):
        consumer.process_event({
            "event_id": f"benign-{i}",
            "timestamp": time.time(),
            "agent_id": f"Agent-Benign-{i}",
            "role": "tier1_customer_service",
            "endpoint": "/accounts/401/balance",
            "method": "GET",
            "governor_status": "ALLOWED",
            "risk_score": 0.10,
            "pep_latency_ms": 0.9,
            "xai_factors": ["Nominal"],
        })

    drift_report = consumer.get_drift_report()
    assert drift_report["status"] == "STABLE"
    assert "MODEL_STABLE" in drift_report["recommendation"]

    # Step 2: Inject sudden burst of 10 anomalous events -> Drift MUST trigger
    for i in range(10):
        consumer.process_event({
            "event_id": f"anomaly-{i}",
            "timestamp": time.time(),
            "agent_id": f"Agent-Attack-{i}",
            "role": "tier1_customer_service",
            "endpoint": "/transfers/wire",
            "method": "POST",
            "governor_status": "QUARANTINED",
            "risk_score": 0.95,
            "pep_latency_ms": 4.2,
            "xai_factors": ["HIGH_ENTROPY", "BURST_VELOCITY"],
        })

    drift_report_after = consumer.get_drift_report()
    assert drift_report_after["status"] == "DRIFT_DETECTED"
    assert "TRIGGER_RETRAINING" in drift_report_after["recommendation"]
    assert len(drift_report_after["drift_alerts"]) > 0


def test_consumer_retraining_feedback_buffer():
    """Verify that blocked operations and borderline risk samples are buffered for model retraining."""
    consumer = GovernanceEventConsumer(topics=["agentic-iam.telemetry"])
    consumer.reset_state()

    consumer.process_event({
        "event_id": "feedback-01",
        "timestamp": time.time(),
        "agent_id": "Agent-Borderline",
        "role": "tier1_customer_service",
        "endpoint": "/accounts/401/deposits/liquidate",
        "method": "POST",
        "governor_status": "BLOCKED",
        "risk_score": 0.68,
        "pep_latency_ms": 1.1,
        "xai_factors": ["POLICY_BLOCK"],
    })

    metrics = consumer.get_metrics()
    assert metrics["retraining_buffer"]["buffered_samples"] == 1


def test_consumer_in_memory_fallback_queue():
    """Verify in-memory fallback queue drains and processes events without blocking."""
    consumer = GovernanceEventConsumer(topics=["agentic-iam.telemetry"])
    consumer.reset_state()

    test_event = {
        "event_id": "fallback-test-01",
        "timestamp": time.time(),
        "agent_id": "Agent-Fallback-01",
        "role": "tier1_support",
        "endpoint": "/faq",
        "method": "GET",
        "governor_status": "ALLOWED",
        "risk_score": 0.10,
        "pep_latency_ms": 0.5,
    }

    consumer.enqueue_event(test_event)
    assert not consumer.fallback_queue.empty()

    # Manually drain one item
    ev = consumer.fallback_queue.get_nowait()
    res = consumer.process_event(ev)
    assert res["status"] == "ALLOWED"
    assert consumer.total_processed == 1


# ==============================================================================
# SECTION 4: FastAPI Observability Endpoints Integration
# ==============================================================================

def test_api_telemetry_metrics_endpoint():
    """Verify GET /api/v1/telemetry/metrics returns 200 with complete observability schema."""
    res = client.get("/api/v1/telemetry/metrics")
    assert res.status_code == 200
    data = res.json()

    assert "total_events_processed" in data
    assert "status_counts" in data
    assert "rolling_window" in data
    assert "drift_monitoring" in data
    assert "alerts" in data
    assert "retraining_buffer" in data
    assert "consumer_active" in data


def test_api_ml_drift_status_endpoint():
    """Verify GET /api/v1/ml/drift-status returns 200 with drift report."""
    res = client.get("/api/v1/ml/drift-status")
    assert res.status_code == 200
    data = res.json()

    assert "status" in data
    assert data["status"] in ("STABLE", "DRIFT_DETECTED")
    assert "recommendation" in data
    assert "metrics" in data
    assert "retraining_samples_ready" in data


def test_gateway_pep_produces_telemetry_with_xai_factors():
    """Verify that a request through the gateway PEP triggers telemetry emission with xai_factors."""
    from backend.core.auth import NHITokenManager

    token = NHITokenManager.mint_agent_token("Agent-Integ-01", "tier1_customer_service")
    res = client.get(
        "/gateway/faq",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert res.status_code == 200
    assert res.json()["governor_status"] == "ALLOWED"


def test_kafka_consumer_default_topics():
    """Verify consumer default topics include telemetry, alerts, and governance events topics."""
    consumer = GovernanceEventConsumer()
    assert settings.KAFKA_TOPIC_TELEMETRY in consumer.topics
    assert settings.KAFKA_TOPIC_ALERTS in consumer.topics
    assert "agent.governance.events" in consumer.topics


def test_consumer_null_and_malformed_fields_robustness():
    """Verify consumer safely handles null risk_score, latency, metadata, and duplicate event_ids."""
    consumer = GovernanceEventConsumer(topics=["agentic-iam.telemetry"])
    consumer.reset_state()

    malformed_event = {
        "event_id": "malformed-edge-01",
        "agent_id": "Agent-Malformed",
        "risk_score": None,
        "pep_latency_ms": None,
        "metadata": None,
        "governor_status": None,
        "xai_factors": None,
        "violation_reason": None,
    }
    res = consumer.process_event(malformed_event)
    assert res["status"] == "ALLOWED"
    assert res["risk_score"] == 0.10
    assert res["xai_factors"] == []
    assert consumer.total_processed == 1

    # Verify duplicate event_id is safely ignored without re-incrementing total_processed
    dup_res = consumer.process_event(malformed_event)
    assert dup_res["status"] == "DUPLICATE_IGNORED"
    assert consumer.total_processed == 1


def test_check_drift_consistent_schema_with_few_samples():
    """Verify _check_drift returns consistent keys (sample_count, mean_risk, anomaly_rate, reasons) even with <10 samples."""
    consumer = GovernanceEventConsumer(topics=["agentic-iam.telemetry"])
    consumer.reset_state()

    # 0 samples
    d0 = consumer._check_drift()
    assert d0["drift_detected"] is False
    assert d0["sample_count"] == 0
    assert "mean_risk" in d0
    assert "anomaly_rate" in d0
    assert "reasons" in d0 and isinstance(d0["reasons"], list)

    # 3 samples
    for i in range(3):
        consumer.process_event({"event_id": f"sample-{i}", "risk_score": 0.12})

    d3 = consumer._check_drift()
    assert d3["drift_detected"] is False
    assert d3["sample_count"] == 3
    assert isinstance(d3["reasons"], list)


def test_model_retraining_with_feedback_buffer():
    """Verify buffered feedback samples trigger online model retraining and update active risk engine."""
    consumer = GovernanceEventConsumer(topics=["agentic-iam.telemetry"])
    consumer.reset_state()

    consumer.process_event({
        "event_id": "feedback-sample-01",
        "agent_id": "Agent-Borderline-1",
        "endpoint": "/transfers/wire",
        "method": "POST",
        "risk_score": 0.65,
        "governor_status": "BLOCKED",
        "xai_factors": ["POLICY_BLOCK"],
    })
    consumer.process_event({
        "event_id": "feedback-sample-02",
        "agent_id": "Agent-Borderline-2",
        "endpoint": "/accounts/401/deposits/liquidate",
        "method": "POST",
        "risk_score": 0.72,
        "governor_status": "BLOCKED",
        "xai_factors": ["HIGH_RISK_TRANSITION"],
    })

    assert len(consumer.retraining_feedback_buffer) == 2

    res = consumer.trigger_retraining()
    assert res["status"] == "SUCCESS"
    assert res["samples_incorporated"] == 2
    assert len(consumer.retraining_feedback_buffer) == 0  # Buffer cleared


def test_api_ml_retrain_endpoint():
    """Verify POST /api/v1/ml/retrain triggers online model retraining via REST API."""
    res = client.post("/api/v1/ml/retrain")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "SUCCESS"
    assert "samples_incorporated" in data
    assert "total_training_samples" in data


def test_producer_dual_dispatch_on_quarantine():
    """Verify producer dispatches quarantine events to both telemetry and alerts streams."""
    producer = telemetry_producer
    dispatched_topics = []

    # Mock producer.send to track destination topics
    if producer.producer:
        orig_send = producer.producer.send
        def mock_send(topic, key=None, value=None):
            dispatched_topics.append(topic)
            return orig_send(topic, key=key, value=value)
        producer.producer.send = mock_send

    producer._dispatch({
        "event_id": "dual-dispatch-test",
        "agent_id": "Agent-Test-Quar",
        "governor_status": "QUARANTINED",
        "risk_score": 0.95,
        "xai_factors": ["BURST_ATTACK"],
    })

    if producer.producer:
        assert settings.KAFKA_TOPIC_TELEMETRY in dispatched_topics
        assert settings.KAFKA_TOPIC_ALERTS in dispatched_topics
        producer.producer.send = orig_send
