# 🛠️ Troubleshooting Guide

## Common Issues & Solutions

### ❓ "When I click 'Switch to RL', SUMO stops and nothing works"

**This is expected behavior!** The button is designed to **stop the current simulation** and prepare for a restart with a different controller mode.

#### How the System Works:

The project has **two different ways** to compare Fixed vs RL:

#### **Option 1: Single Mode Dashboard** (Current View)

- Run **either** Fixed-Time **or** RL mode
- Switch requires stopping and restarting the simulation
- Best for focused testing of one controller

**Workflow:**

1. Start simulation from Junction Selection
2. Choose either Fixed or RL mode
3. Run simulation and view metrics
4. Click "RESTART WITH RL/FIXED" to switch modes
5. This stops SUMO and returns you to Junction Selection
6. Start a new simulation with the new mode

#### **Option 2: Dual Comparison Mode** ⚔️

- Run **both** Fixed-Time **and** RL simultaneously
- See real-time side-by-side comparison
- Best for direct performance comparison

**Workflow:**

1. Go to Junction Selection
2. Select "⚔️ DUAL COMPARISON" mode
3. Both SUMO windows will open (Fixed on left, RL on right)
4. Dashboard shows metrics from both in real-time

---

## Why Does SUMO Stop When Switching?

The simulation cannot dynamically switch between Fixed-Time and RL controllers while running. This is because:

1. **SUMO needs to restart** with different traffic light controller logic
2. **The RL model needs to be loaded** before the simulation starts
3. **Fair comparison requires identical conditions** (same traffic, weather, timing)

---

## Recommended Usage

### For Testing One Controller:

- Use **Dashboard** view
- Accept that switching = restarting
- Good for quick testing

### For Comparing Performance:

- Use **Dual Comparison** mode from Junction Selection
- Runs both controllers simultaneously
- Get immediate side-by-side metrics
- This is the **preferred method** for evaluation

### For Detailed Analysis:

- Go to **ANALYTICS** page (from top menu)
- Run evaluation protocols
- Export data as CSV
- View historical comparison charts

---

## How to Fix the Confusion

I've updated the button text to be clearer:

- **When simulation is running**: "🔄 RESTART WITH RL" (instead of "SWITCH TO RL")
- **When simulation is stopped**: "⚡ SWITCH TO RL"
- Added confirmation dialog explaining the restart

---

## Quick Reference

| What You Want     | How to Do It                                             |
| ----------------- | -------------------------------------------------------- |
| Test RL only      | Start simulation → Select RL mode                        |
| Test Fixed only   | Start simulation → Select Fixed mode                     |
| Compare both live | Junction Selection → "⚔️ DUAL COMPARISON"                |
| Switch during run | Click "RESTART WITH..." → Confirm → Start new simulation |
| View past results | Go to ANALYTICS page                                     |
| Export data       | ANALYTICS → Export CSV                                   |

---

## Still Having Issues?

Check:

1. ✅ SUMO_HOME environment variable is set correctly
2. ✅ Backend server is running (`python -m uvicorn app.main:app --reload`)
3. ✅ RL models exist in `backend/models/checkpoints/`
4. ✅ SUMO GUI is not already running (close any existing instances)
5. ✅ Ports 8813 and 8814 are not in use by other programs

## Tips for Best Results

- **Use Dual Comparison mode** for the most impressive demo
- **Peak hours (8-10 AM)** show the biggest difference between Fixed and RL
- **Emergency vehicle injection** works best during high traffic
- **Weather effects** are more dramatic with RL controller
