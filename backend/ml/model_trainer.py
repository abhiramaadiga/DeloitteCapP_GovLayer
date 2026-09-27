"""
Model Trainer: Fits an Isolation Forest on 5,000+ synthetic benign banking
telemetry baselines and serializes to backend/ml/models/isolation_forest.joblib.
"""
import logging
import numpy as np
import joblib
from pathlib import Path
from sklearn.ensemble import IsolationForest

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("agentic_iam.model_trainer")

MODEL_DIR = Path(__file__).resolve().parent / "models"
MODEL_PATH = MODEL_DIR / "isolation_forest.joblib"


def train(n_normal: int = 5000, n_anomaly: int = 250):
    """
    Generates synthetic baseline telemetry and trains an Isolation Forest.

    Feature vector: [entropy, velocity_rps, markov_score, payload_bytes]

    Benign baselines:
      - Entropy:      2.5 - 4.0 bits  (natural language JSON queries)
      - Velocity:     0.1 - 2.5 RPS   (human-supervised agent cadence)
      - Markov:       0.0             (legal endpoint transitions only)
      - Payload:      50 - 500 bytes  (small query / response bodies)

    Anomaly seeds (5%):
      - Entropy:      4.8 - 6.0 bits  (base64 dumps, prompt injection)
      - Velocity:     12 - 30 RPS     (autonomous scraping bursts)
      - Markov:       0.0 or 1.0      (illegal state jumps)
      - Payload:      800 - 8000 bytes (bulk data exfiltration)
    """
    np.random.seed(42)
    logger.info(f"Generating {n_normal} benign + {n_anomaly} anomaly training samples...")

    # Benign Traffic
    benign = np.column_stack([
        np.random.uniform(2.5, 4.0, n_normal),       # Entropy
        np.random.uniform(0.1, 2.5, n_normal),       # Velocity RPS
        np.zeros(n_normal),                           # Markov (all legal)
        np.random.uniform(50.0, 500.0, n_normal),    # Payload bytes
    ])

    # Anomalous Traffic
    anomalies = np.column_stack([
        np.random.uniform(4.8, 6.0, n_anomaly),                          # High entropy
        np.random.uniform(12.0, 30.0, n_anomaly),                        # Burst RPS
        np.random.choice([0.0, 1.0], n_anomaly, p=[0.3, 0.7]),           # Illegal jumps
        np.random.uniform(800.0, 8000.0, n_anomaly),                     # Large payloads
    ])

    X = np.vstack([benign, anomalies])
    logger.info(f"Training feature matrix shape: {X.shape}")

    # n_estimators=100 (team decision for higher robustness)
    model = IsolationForest(
        n_estimators=100,
        max_samples=256,
        random_state=42,
        contamination=0.05,
        n_jobs=-1,
    )
    model.fit(X)
    logger.info("Isolation Forest fitted successfully.")

    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    joblib.dump(model, MODEL_PATH)
    logger.info(f"Model saved to {MODEL_PATH}")

    # Quick sanity check
    benign_sample = np.array([[3.5, 1.0, 0.0, 120.0]])
    attack_sample = np.array([[5.5, 20.0, 1.0, 4000.0]])
    logger.info(f"Sanity - benign decision: {model.decision_function(benign_sample)[0]:.4f}")
    logger.info(f"Sanity - attack decision: {model.decision_function(attack_sample)[0]:.4f}")
    logger.info("Training complete!")


def retrain_with_feedback(
    feedback_samples: list = None,
    n_normal: int = 2000,
    n_anomaly: int = 100,
    save: bool = True,
) -> dict:
    """
    Retrains the Isolation Forest model incorporating real-world telemetry feedback
    (RLHF borderline samples, policy violations, and detected drift instances).
    Reloads the active model in risk_engine upon completion.
    """
    import time
    np.random.seed(int(time.time()) % 100000)
    samples_count = len(feedback_samples or [])
    logger.info(f"Retraining Isolation Forest with feedback: {samples_count} dynamic samples.")

    benign = np.column_stack([
        np.random.uniform(2.5, 4.0, n_normal),
        np.random.uniform(0.1, 2.5, n_normal),
        np.zeros(n_normal),
        np.random.uniform(50.0, 500.0, n_normal),
    ])

    anomalies = np.column_stack([
        np.random.uniform(4.8, 6.0, n_anomaly),
        np.random.uniform(12.0, 30.0, n_anomaly),
        np.random.choice([0.0, 1.0], n_anomaly, p=[0.3, 0.7]),
        np.random.uniform(800.0, 8000.0, n_anomaly),
    ])

    stack_list = [benign, anomalies]

    # Convert feedback samples into feature rows if provided
    feedback_features = []
    if feedback_samples:
        for s in feedback_samples:
            vec = s.get("vector")
            if vec and len(vec) == 4:
                feedback_features.append(vec)
            else:
                risk = float(s.get("risk_score", 0.5))
                ent = 4.5 + (risk * 1.5) if risk >= 0.75 else 3.2
                vel = 15.0 if risk >= 0.75 else 1.0
                markov = 1.0 if (s.get("xai_factors") and any("TRANSITION" in str(f) for f in s["xai_factors"])) else 0.0
                p_bytes = 2000.0 if risk >= 0.75 else 200.0
                feedback_features.append([ent, vel, markov, p_bytes])

    if feedback_features:
        stack_list.append(np.array(feedback_features))

    X = np.vstack(stack_list)
    logger.info(f"Retraining dataset shape: {X.shape}")

    model = IsolationForest(
        n_estimators=100,
        max_samples=256,
        random_state=42,
        contamination=0.05,
        n_jobs=1,
    )
    model.fit(X)

    if save:
        MODEL_DIR.mkdir(parents=True, exist_ok=True)
        joblib.dump(model, MODEL_PATH)
        logger.info(f"Retrained model saved to {MODEL_PATH}")
        try:
            from backend.ml.risk_engine import reload_model
            reload_model()
            logger.info("Active Isolation Forest model reloaded into risk engine.")
        except Exception as e:
            logger.warning(f"Could not reload model in risk engine: {e}")

    return {
        "status": "SUCCESS",
        "samples_incorporated": len(feedback_features),
        "total_training_samples": int(X.shape[0]),
        "model_path": str(MODEL_PATH),
    }


if __name__ == "__main__":
    train()
