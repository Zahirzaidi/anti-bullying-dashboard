ESP32 to Python server

Server expectation:

- URL: `POST /audio?room=JT0-01&sr=4000`
- Body: raw audio bytes only
- Audio format: signed 16-bit PCM, little-endian, mono
- Sample rate: `4000` Hz by default
- Minimum payload: `256` samples

What the ESP32 must send:

- Do not send WAV header.
- Do not send JSON around the samples.
- Send microphone samples as raw `int16_t` bytes.
- Keep the same sample rate used during model training. If model training used another sample rate, change `sr` and backend default to match.

Recommended ESP32 flow:

1. Read mic samples into an `int16_t` buffer.
2. Collect at least 256 samples. More is usually better if it matches training.
3. HTTP POST the raw buffer directly to the Python server.
4. Include room id in query string, for example `JT0-01`.

Example request from a device:

```text
POST http://<server-ip>:5000/audio?room=JT0-01&sr=4000
Content-Type: application/octet-stream
Body: raw int16 PCM bytes
```

Important matching rule:

- The MFCC settings used in `server.py` only work properly if the incoming audio format matches the data used to train `model.pkl`.
- If you trained the model using WAV files, 8 kHz audio, normalized floats, or a fixed clip duration, the ESP32 capture must be made consistent with that.

Quick checks:

- `GET /health` shows whether model and Firebase are ready.
- `GET /audio-spec` shows the expected request format.

Typical failure causes:

- `model.pkl` is empty or trained with different preprocessing.
- `firebase_key.json` is missing.
- ESP32 sends 8-bit data, not 16-bit.
- ESP32 sends a WAV file header instead of raw PCM.
- Sample rate from ESP32 does not match model training.
