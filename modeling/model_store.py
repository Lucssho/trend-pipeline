from pathlib import Path

from bertopic import BERTopic

MODEL_DIR = Path(__file__).resolve().parent.parent / "data" / "bertopic_model"


def model_exists():
    return MODEL_DIR.exists()


def save_model(topic_model):
    MODEL_DIR.parent.mkdir(parents=True, exist_ok=True)
    topic_model.save(str(MODEL_DIR), serialization="safetensors", save_ctfidf=True)


def load_model():
    return BERTopic.load(str(MODEL_DIR))
