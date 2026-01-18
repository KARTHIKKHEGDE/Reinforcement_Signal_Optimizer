# 🚀 Quick Start Guide

## ✅ **Current Status**: Backend Running Successfully!

The backend server is currently running at: **http://localhost:8000**

---

## 📋 How to Run the Project

### Option 1: Use Startup Scripts (Windows - Easiest!)

#### Backend:

```bash
cd backend
.\start_backend.bat
```

#### Frontend:

```bash
cd frontend
npm run dev
```

### Option 2: Manual Activation (All Platforms)

#### Backend (Windows):

```bash
cd backend
.\venv\Scripts\activate
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

#### Backend (Mac/Linux):

```bash
cd backend
source venv/bin/activate
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

#### Frontend:

```bash
cd frontend
npm run dev
```

---

## 🆕 Dual Comparison Feature

The dual comparison feature is now **working**! Here's what was fixed:

### What Changed:

1. ✅ Created dedicated `/dual` route in frontend
2. ✅ Created `DualComparison.tsx` component for side-by-side visualization
3. ✅ Created `dualSocket.ts` WebSocket service for dual simulation streaming
4. ✅ Updated navigation from Junction Selection to use the new dual page
5. ✅ Traffic multiplier feature removed (restored to original behavior)

### How to Use Dual Comparison:

1. **Start Backend** (if not already running):

   ```bash
   cd backend
   .\start_backend.bat   # Windows
   # OR
   source venv/bin/activate && python -m uvicorn app.main:app --reload  # Mac/Linux
   ```

2. **Start Frontend**:

   ```bash
   cd frontend
   npm run dev
   ```

3. **In the Browser**:
   - Go to http://localhost:5173
   - Click "START SIMULATION"
   - Select "⚔️ DUAL COMPARISON" mode
   - Choose a junction (e.g., Silk Board)
   - Set time window (e.g., 7 AM to 8 AM)
   - Click "START DUAL SIMULATION"
   - You'll be redirected to `/dual` page showing both simulations side-by-side!

---

## 📊 What You'll See

The dual comparison page shows:

- **Left Panel**: Fixed Time Controller metrics
- **Right Panel**: RL Agent metrics
- **Top Cards**: Real-time comparison (wait time diff, queue diff, throughput)
- **Color Coding**: Green = RL winning, Red = Fixed winning

---

## 🔧 Troubleshooting

### Backend won't start?

- Make sure virtual environment is activated
- Check if port 8000 is available: `netstat -ano | findstr :8000`
- Install dependencies: `pip install -r requirements.txt`

### Frontend won't connect?

- Verify backend is running at http://localhost:8000
- Check browser console for WebSocket errors
- Make sure ports 5173 (frontend) and 8000 (backend) are open

### Dual comparison not showing data?

- Check that backend is running
- Verify both SUMO instances started (check terminal logs)
- Open browser DevTools → Network → WS tab to see WebSocket connection
- Look for connection to `ws://localhost:8000/ws/dual`

---

## 🎯 Key Files Modified

### Frontend:

- `src/pages/DualComparison.tsx` - New dual comparison page
- `src/services/dualSocket.ts` - Dual WebSocket service
- `src/App.tsx` - Added `/dual` route
- `src/pages/JunctionSelection.tsx` - Navigate to `/dual` for dual mode

### Backend:

- `backend/app/routes/dual_simulation.py` - Already had dual endpoints
- `backend/app/dual_websocket.py` - Already had dual WebSocket manager
- **Traffic multiplier removed from**:
  - `backend/app/demand/demand_generator.py`
  - `backend/app/routes/simulation.py`

---

## 📝 Notes

- Backend startup scripts created: `start_backend.bat` (Windows) and `start_backend.sh` (Mac/Linux)
- Virtual environment is located at: `backend/venv/`
- The dual simulation runs TWO separate SUMO instances for fair comparison
- Both simulations use the same vehicle demand from CSV files

---

Need help? Check the terminal logs for detailed error messages!
