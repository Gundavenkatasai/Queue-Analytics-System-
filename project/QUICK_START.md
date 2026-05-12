# ⚡ QUICK START - Real-Time Surveillance System

## 🚀 START IN 30 SECONDS

**Easiest Way (Recommended):**

```bash
cd project
START_ALL.bat
```

**Manual Way (3 Terminals):**

### Terminal 1: Backend API

```bash
cd backend
php artisan serve --port=8000
```

### Terminal 2: Frontend Dashboard

```bash
cd frontend
npm start
```

### Terminal 3: ML Service (Requires Webcam)

```bash
cd ml-service
python main.py
```

---

## Then Open: http://localhost:3000

## 📊 What You'll See

**Dashboard (http://localhost:3000):**

- 🟢 LIVE indicator - Camera is actively detecting
- 👥 People count - Updates in real-time as people enter/leave
- 📊 Occupancy % - Current crowd level
- ➡️ Entry/Exit counts - Cumulative for the day
- ⏳ Queue detection - Alert when 3+ people align vertically
- ⏱️ Dwell time - How long people stay visible
- 📈 Timeline charts - Real-time trends

**Backend Console (Terminal 1):**

```
Server running on [http://127.0.0.1:8000]
POST /api/analytics/timeline - 200 OK (frame data from ML)
```

**ML Service Console (Terminal 3):**

```
Frame 000015 | People: 12 | Occupancy: 12.0% | Entry: 45 | Exit: 38
Frame 000030 | People: 15 | Occupancy: 15.0% | Entry: 46 | Exit: 38
...
```

## 🎯 Test It

| Action                  | Expected Result             |
| ----------------------- | --------------------------- |
| Move in front of camera | People count increases      |
| Stand still for 30s     | Dwell time increases        |
| Cross horizontal line   | Entry/Exit counts increment |
| Get 50+ people          | Alert banner appears        |
| Stand in line (3+)      | Queue detection triggers    |
| Wait 1 hour             | Recording chunk completes   |

---

## 🔗 Important URLs

| URL                                      | Purpose         |
| ---------------------------------------- | --------------- |
| http://localhost:3000                    | Main dashboard  |
| http://localhost:8000/api                | Backend API     |
| http://localhost:8000/api/analytics/live | Current metrics |

---

## 🛑 Stop System

Press Ctrl+C in each terminal. All data is saved.

---

## 🆘 Issues?

| Problem                         | Solution                                            |
| ------------------------------- | --------------------------------------------------- |
| "Camera not found"              | Verify webcam connected; check `ml-service/main.py` |
| "Port 8000 in use"              | Kill process: `netstat -ano \| findstr :8000`       |
| "npm not found"                 | Install Node.js from nodejs.org                     |
| "API Connection error"          | Ensure backend started first                        |
| "Dashboard shows connecting..." | Check browser console (F12) for errors              |

---

## 📁 Key Files

```
backend/
  ├─ app/Http/Controllers/AnalyticsTimelineController.php (9 endpoints)
  ├─ routes/api.php (all routes configured)
  └─ storage/ (JSON fallback data)

frontend/
  ├─ src/components/Dashboard.jsx (real-time UI)
  └─ src/App.jsx

ml-service/
  ├─ main.py (surveillance coordinator)
  ├─ real_time_detection.py (detection engine)
  ├─ realtime_recorder.py (recording pipeline)
  └─ storage/videos/ (recorded chunks)
```

---

## ✨ What's Implemented

✅ Real-time person detection (15 FPS)
✅ 6 Analytics features (entry, exit, queue, occupancy, dwell time, peak hours)
✅ H.264 MP4 recording (640x480, 480p)
✅ 1-hour automatic chunk rotation
✅ MongoDB + JSON storage
✅ 9 REST API endpoints
✅ Live dashboard with charts
✅ Alert system (occupancy > 50, queue detected)
✅ Person tracking with unique IDs
✅ Heatmap generation

---

## 🎉 You're Ready!

1. Run `START_ALL.bat` or the 3 commands
2. Wait 5 seconds
3. Open http://localhost:3000
4. Watch real-time surveillance in action!

**NO MOCK DATA - ALL REAL CAMERA DETECTION**

For detailed docs, see:

- `IMPLEMENTATION_COMPLETE.md` - Full feature list
- `START_SYSTEM.md` - Startup guide & troubleshooting
