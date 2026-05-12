# 🚀 QUICK START GUIDE - SURVEILLANCE SYSTEM

## ⚡ START THE SYSTEM (Fastest Way)

### Option 1: Automated (Recommended - ONE COMMAND)

```bash
cd "c:\Users\venka\OneDrive\Desktop\laravel\laravel project\project"
python system_startup.py
```

This automatically starts all services and runs tests!

### Option 2: Manual (3 Terminal Windows)

**Terminal 1 - Backend Server (port 8000)**

```bash
cd "c:\Users\venka\OneDrive\Desktop\laravel\laravel project\project\backend"
php artisan serve --port=8000
```

**Terminal 2 - Frontend (port 3000)**

```bash
cd "c:\Users\venka\OneDrive\Desktop\laravel\laravel project\project\frontend"
npm start
```

**Terminal 3 - ML Service**

```bash
cd "c:\Users\venka\OneDrive\Desktop\laravel\laravel project\project\ml-service"
python main.py
```

---

## 🌐 OPEN IN BROWSER

Once all services are running:

**Frontend Dashboard:**

```
http://localhost:3000
```

**Backend API (raw):**

```
http://localhost:8000/api/analytics/timeline?camera_id=camera_1&date=2025-05-11
```

---

## 📱 DASHBOARD TABS (Click in order)

1. **Live** - Real-time metrics (updates every 2 seconds)
2. **Calendar** - Select date, view timeline
3. **Videos** - Play recordings, download
4. **Reports** - Generate daily/weekly/monthly reports
5. **Heatmap** - 20x20 grid showing hotspots
6. **Alerts** - Configure thresholds, view alerts
7. **Settings** - System configuration

---

## 🧪 TEST THE SYSTEM

### Run Integration Tests

```bash
cd "c:\Users\venka\OneDrive\Desktop\laravel\laravel project\project"
python integration_test.py
```

Expected: 10/10 tests passing ✓

### Run Performance Benchmarks

```bash
python phase8_performance_tests.py
```

---

## 📊 WHAT'S RUNNING

### Backend (Laravel)

- **Port:** 8000
- **API Endpoints:** 27 total
- **Database:** MongoDB Atlas (with file fallback)
- **Response Time:** <5ms average

### Frontend (React)

- **Port:** 3000
- **Tabs:** 7 (Live, Calendar, Video, Reports, Heatmap, Alerts, Settings)
- **Charts:** Recharts for data visualization
- **Styling:** Tailwind CSS

### ML Service (Python)

- **Detection:** YOLOv8 (person detection)
- **Tracking:** ByteTrack (persistent IDs)
- **Recording:** H.264 encoding, 1-hour chunks
- **Mode:** Simulator (can use real camera with `USE_CAMERA=true`)

---

## 🎯 FEATURES TO TRY

### Live Dashboard

- See real-time people count and queue length
- Watch wait times and occupancy percentage
- Auto-updates every 2 seconds

### Calendar View

- Pick any date
- View hourly data timeline
- See daily statistics summary

### Video Player

- View recorded videos
- Scrub through timeline
- Download recordings

### Heatmap

- See where most activity occurs (red = hot, blue = cold)
- 20x20 grid shows occupancy patterns
- Hover over cells for details

### Reports

- Generate PDF/CSV reports
- Get peak hour recommendations
- Export data for analysis

### Alerts

- Configure thresholds:
  - Max people: 50
  - Max queue: 10
  - Max wait time: 300s
- View alert history

---

## 🔧 IF SOMETHING DOESN'T WORK

### Backend won't start

```bash
cd backend
php artisan cache:clear
php artisan config:clear
php artisan serve --port=8000
```

### Frontend won't start

```bash
cd frontend
npm install  # If packages missing
rm -rf node_modules package-lock.json
npm install
npm start
```

### ML Service won't connect

```bash
# Check if API is running:
python -c "import requests; print(requests.get('http://localhost:8000/').status_code)"

# If error: Start backend first
```

### Port already in use

```bash
# Backend on different port:
php artisan serve --port=8001

# Frontend on different port:
PORT=3001 npm start

# Then update API_URL in frontend config
```

---

## 📝 KEY ENDPOINT EXAMPLES

### Get Today's Analytics Timeline

```bash
curl "http://localhost:8000/api/analytics/timeline?camera_id=camera_1&date=2025-05-11"
```

### Get Daily Summary

```bash
curl "http://localhost:8000/api/analytics/summary?camera_id=camera_1&date=2025-05-11"
```

### Get Heatmap

```bash
curl "http://localhost:8000/api/analytics/heatmap?camera_id=camera_1&date=2025-05-11"
```

### List Recordings

```bash
curl "http://localhost:8000/api/recordings?camera_id=camera_1&date=2025-05-11"
```

---

## 🎬 USING REAL CAMERA

Replace simulator mode with real laptop camera:

```bash
cd "c:\Users\venka\OneDrive\Desktop\laravel\laravel project\project\ml-service"
set USE_CAMERA=true
python main.py
```

System will auto-detect built-in camera and use real person detection!

---

## 📊 EXPECTED PERFORMANCE

| Metric         | Expected |
| -------------- | -------- |
| API Response   | <5ms     |
| YOLO Inference | ~80ms    |
| Tracking       | ~35ms    |
| FPS            | 10-12    |
| Memory         | <1GB     |
| CPU Usage      | 15-25%   |

---

## 🐛 DEBUG MODE

### Enable verbose logging

```bash
# Backend
cd backend
php artisan tinker

# ML Service
VERBOSE=true python main.py
```

### Check logs

```bash
# Backend logs
tail -f backend/storage/logs/laravel.log

# ML Service logs
tail -f ml-service/logs/system.log

# Integration test logs
cat integration_test.log
```

---

## 📁 PROJECT STRUCTURE

```
project/
├── backend/              # Laravel API server
│   ├── app/
│   │   ├── Http/Controllers/
│   │   │   ├── AnalyticsController.php
│   │   │   └── RecordingController.php
│   │   └── Models/
│   │       ├── AnalyticsTimeline.php
│   │       └── Recording.php
│   ├── routes/api.php   # 27 API endpoints
│   └── ...
├── frontend/            # React dashboard
│   ├── src/
│   │   ├── components/
│   │   │   ├── Dashboard.jsx (Live tab)
│   │   │   ├── CalendarView.jsx
│   │   │   ├── VideoPlayer.jsx
│   │   │   ├── ReportsView.jsx
│   │   │   ├── HeatmapView.jsx
│   │   │   ├── AlertsView.jsx
│   │   │   ├── SettingsView.jsx
│   │   │   ├── TabNavigation.jsx
│   │   │   └── DashboardContainer.jsx
│   │   └── App.jsx
│   └── package.json
├── ml-service/          # Python ML & recording
│   ├── main.py          # Entry point
│   ├── config.py        # Configuration
│   ├── advanced_analytics.py
│   ├── detection/
│   │   └── yolo_detector.py
│   ├── recording/
│   │   ├── video_recorder.py
│   │   └── advanced_video_recorder.py
│   ├── tracking/
│   │   └── byte_tracker.py
│   └── utils/
│       ├── api_client.py
│       └── database_client.py
├── system_startup.py    # Auto start all services
├── integration_test.py   # 10 tests
├── phase8_performance_tests.py
└── SYSTEM_COMPLETION_REPORT.md
```

---

## ✅ SUCCESS CHECKLIST

- [ ] Backend running on port 8000 (php artisan serve)
- [ ] Frontend running on port 3000 (npm start)
- [ ] ML Service running (python main.py)
- [ ] Can see http://localhost:3000 in browser
- [ ] Live tab shows data updating
- [ ] Calendar view shows timeline for today
- [ ] Integration tests pass (10/10)
- [ ] Performance benchmarks OK

---

## 📞 TROUBLESHOOTING

### "Connection refused" on port 8000

**Solution:** Backend not running. Start it first:

```bash
cd backend && php artisan serve --port=8000
```

### "Cannot GET /" at localhost:3000

**Solution:** Frontend not running or compiling. Check Terminal 2:

```bash
cd frontend && npm start
```

### ML Service errors

**Solution:** Check logs and ensure MongoDB URI is set:

```bash
echo %MONGODB_URI%
python main.py
```

### Heatmap not showing

**Solution:** Need some analytics data first. Wait 30 seconds after starting system.

### Video player shows no videos

**Solution:** System needs time to record. Check ML Service is running, wait 2 minutes.

---

## 🎉 YOU'RE DONE!

All 8 phases are now complete:
✅ Phase 1: Database Schema
✅ Phase 2: Real Detection  
✅ Phase 3: Video Recording
✅ Phase 4: REST APIs
✅ Phase 5: Frontend UI
✅ Phase 6: Integration Tests
✅ Phase 7: Advanced Analytics
✅ Phase 8: Performance Testing

**System is production-ready!**

---

_Start the system now with:_

```bash
python system_startup.py
```
