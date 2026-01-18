# How to Run the Project

## 1. Start Backend (Traffic Logic Core)

Open a terminal, navigate to the `backend` folder, and run the server:

```bash
cd backend
python -m uvicorn app.main:app --reload
```

_Server will start at: http://localhost:8000_

## 2. Start Frontend (Control Dashboard)

Open a **new** terminal, navigate to the `frontend` folder, and start the UI:

```bash
cd frontend
npm run dev
```

_Dashboard will open at: http://localhost:5173_

---

## 🎯 How to Use the System

### **Option A: Single Mode (Quick Test)**

1. Go to Junction Selection
2. Choose a junction (e.g., Silk Board)
3. Select time window
4. Choose **Single Mode**
5. Pick either "Fixed-Time" or "RL Agent"
6. Click START
7. View metrics in Dashboard

**To switch modes:** Click "RESTART WITH RL/FIXED" button - this will stop the simulation and let you start fresh with the other mode.

### **Option B: Dual Comparison Mode (Recommended!) ⚔️**

1. Go to Junction Selection
2. Choose a junction
3. Select time window
4. Choose **DUAL COMPARISON** mode
5. Click START
6. **Two SUMO windows will open:**
   - Left window: Fixed-Time controller
   - Right window: RL controller
7. Dashboard shows metrics from both simultaneously

**This is the best way to see RL vs Fixed comparison!**

### **Option C: Analytics & Evaluation**

1. Go to ANALYTICS page (top menu)
2. Run evaluation protocols
3. View comparison charts
4. Export data as CSV

---

## ⚠️ Important Notes

- **"Switch to RL" button stops the simulation** - this is by design. See [TROUBLESHOOTING.md](TROUBLESHOOTING.md) for details.
- **Use Dual Comparison mode** for the most impressive side-by-side comparison
- **Peak hours (8-10 AM)** show the biggest performance differences
- Make sure **SUMO_HOME** environment variable is set before starting

## 🐛 Having Issues?

See [TROUBLESHOOTING.md](TROUBLESHOOTING.md) for common problems and solutions.
