JT001 device setup

Recommended path for this project now:

- Use `esp32_jt001_firebase.ino` for the real device.
- Let ESP32 update `rooms/JT001` directly in Firebase.
- Keep `server.py` only as an optional future path if you later complete the ML model and Firebase admin key.

What the sketch does:

- Connects ESP32 to WiFi
- Connects ESP32 to Firebase Realtime Database
- Reads the MAX9814 analog output on `GPIO34`
- Writes `rooms/JT001/status` as `NORMAL` or `ALERT`
- Stores extra diagnostics: `peakToPeak`, `avgDeviation`, `device`

Expected Firebase path:

- `rooms/JT001/status`

Why this path is the best fit now:

- Your dashboard already listens to `rooms/.../status`
- Your Telegram notification flow already depends on the dashboard detecting `ALERT`
- It avoids the incomplete `model.pkl` and missing `firebase_key.json`

Before upload:

- Install `Firebase ESP Client` library in Arduino IDE
- Select the correct COM port
- Upload `esp32_jt001_firebase.ino`
- Open Serial Monitor at `115200`

Threshold tuning:

- Watch the printed `peakToPeak` and `avgDeviation`
- In a quiet room, note the usual values
- During a shout/test sound, note the higher values
- Adjust `ALERT_PEAK_TO_PEAK` and `ALERT_AVG_DEVIATION` in the sketch

Current default room:

- `JT001`
