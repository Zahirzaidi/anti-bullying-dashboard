import os
import pickle
from pathlib import Path

import firebase_admin
import librosa
import numpy as np
from firebase_admin import credentials, db
from flask import Flask, jsonify, request

app = Flask(__name__)

BASE_DIR = Path(__file__).resolve().parent
MODEL_PATH = BASE_DIR / "model.pkl"
FIREBASE_KEY_PATH = BASE_DIR / "firebase_key.json"
FIREBASE_DATABASE_URL = "https://antibullyingsystem-95305-default-rtdb.firebaseio.com/"
DEFAULT_ROOM_ID = os.getenv("ROOM_ID", "JT0-01")
DEFAULT_SAMPLE_RATE = int(os.getenv("AUDIO_SAMPLE_RATE", "4000"))
MIN_AUDIO_SAMPLES = int(os.getenv("MIN_AUDIO_SAMPLES", "256"))

model = None
startup_errors = []


def load_model():
    if not MODEL_PATH.exists():
        startup_errors.append(f"Model file not found: {MODEL_PATH.name}")
        return None

    if MODEL_PATH.stat().st_size == 0:
        startup_errors.append(f"Model file is empty: {MODEL_PATH.name}")
        return None

    with MODEL_PATH.open("rb") as model_file:
        return pickle.load(model_file)


def init_firebase():
    if not FIREBASE_KEY_PATH.exists():
        startup_errors.append(f"Firebase key not found: {FIREBASE_KEY_PATH.name}")
        return False

    if firebase_admin._apps:
        return True

    cred = credentials.Certificate(str(FIREBASE_KEY_PATH))
    firebase_admin.initialize_app(
        cred,
        {
            "databaseURL": FIREBASE_DATABASE_URL,
        },
    )
    return True


def extract_features(audio_bytes, sample_rate):
    audio_data = np.frombuffer(audio_bytes, dtype=np.int16)
    if audio_data.size == 0:
        raise ValueError("Empty audio payload")
    if audio_data.size < MIN_AUDIO_SAMPLES:
        raise ValueError(
            f"Audio payload too short: got {audio_data.size} samples, need at least {MIN_AUDIO_SAMPLES}"
        )

    normalized_audio = audio_data.astype(np.float32) / 32768.0
    mfcc = librosa.feature.mfcc(y=normalized_audio, sr=sample_rate, n_mfcc=13)
    return np.mean(mfcc.T, axis=0), int(audio_data.size)


def update_room_status(room_id, status, prediction):
    room_ref = db.reference(f"rooms/{room_id}")
    room_ref.update(
        {
            "status": status,
            "lastPrediction": prediction,
        }
    )


model = load_model()
firebase_ready = init_firebase()


@app.get("/audio-spec")
def audio_spec():
    return jsonify(
        {
            "method": "POST",
            "path": "/audio",
            "query_params": {
                "room": f"Optional. Default: {DEFAULT_ROOM_ID}",
                "sr": f"Optional. Default: {DEFAULT_SAMPLE_RATE}",
            },
            "body_format": {
                "type": "raw bytes",
                "encoding": "PCM signed 16-bit little-endian",
                "channels": 1,
                "sample_rate": DEFAULT_SAMPLE_RATE,
                "minimum_samples": MIN_AUDIO_SAMPLES,
            },
        }
    )


@app.get("/health")
def health():
    return jsonify(
        {
            "ok": model is not None and firebase_ready,
            "model_loaded": model is not None,
            "firebase_ready": firebase_ready,
            "errors": startup_errors,
            "default_room": DEFAULT_ROOM_ID,
            "default_sample_rate": DEFAULT_SAMPLE_RATE,
            "minimum_audio_samples": MIN_AUDIO_SAMPLES,
        }
    )


@app.post("/audio")
def process_audio():
    if model is None:
        return jsonify({"ok": False, "error": "Model not loaded", "details": startup_errors}), 500

    if not firebase_ready:
        return jsonify({"ok": False, "error": "Firebase not ready", "details": startup_errors}), 500

    room_id = request.args.get("room", DEFAULT_ROOM_ID)
    sample_rate = request.args.get("sr", type=int) or DEFAULT_SAMPLE_RATE

    try:
        mfcc_mean, sample_count = extract_features(request.data, sample_rate)
        prediction = model.predict([mfcc_mean])[0]
        status = "ALERT" if str(prediction).lower() == "scream" else "NORMAL"
        update_room_status(room_id, status, str(prediction))
    except Exception as exc:
        return jsonify({"ok": False, "error": str(exc)}), 400

    return jsonify(
        {
            "ok": True,
            "room": room_id,
            "sample_rate": sample_rate,
            "sample_count": sample_count,
            "prediction": str(prediction),
            "status": status,
        }
    )


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)
