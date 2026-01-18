# 🚦 Project Blueprint: Reinforcement Signal Optimizer

This document serves as the **operational guide** for the team. It explains the core logic, user interactions, and the "why" behind every feature. If you are looking to improve the project, start here.

---

## 🏗️ Core Architecture: The "Digital Twin" Duel
The heart of this project is the **Dual Simulation**. We don't just show an AI controlling traffic; we show a **head-to-head battle** between the past (Fixed Timers) and the future (RL Agent).

### How it must function:
1.  **Identical Demand:** Both simulations (Left: Fixed, Right: RL) must receive the exact same vehicles at the exact same time. This is the only way to prove the AI is actually better.
2.  **Lockstep Movement:** Both simulations run in parallel steps. When the user "steps" the simulation, both worlds advance together.
3.  **RL Constraint:** The AI (RL Agent) is allowed to change the traffic lights, but it is **not** allowed to control when cars arrive. It must solve the problem it is given.

---

## 🕹️ User Interactions & Expected Outcomes

### 1. Junction & Time Selection
*   **Action:** User selects a junction (e.g., Silk Board) and a 15-minute time window (e.g., 08:30 AM).
*   **What Happens:** The system looks up real historical CSV data for that junction. It calculates the "Vehicle Arrival Rate" for that specific time and generates a schedule.
*   **Goal for Improvement:** Add more junctions or support importing custom traffic datasets.

### 2. Emergency Vehicle Injection (🚑)
*   **Action:** User clicks the "Inject Emergency" button.
*   **What Happens:** An ambulance or fire truck is immediately spawned at a random entry point in **BOTH** simulations simultaneously.
*   **What to Observe:** 
    *   The **Fixed Timer** will ignore it; the ambulance will wait in the queue like any other car.
    *   The **RL Agent** should (ideally) detect the congestion and clear the green light early to let the ambulance through.
*   **Goal for Improvement:** Implement "Green Wave" logic where the AI coordinates multiple lights to clear a path.

### 3. Dynamic Weather Effects (⛈️)
*   **Action:** User selects "Rain" or "Storm".
*   **What Happens:** A speed multiplier is applied to every vehicle in both simulations (e.g., vehicles move 30% slower).
*   **What to Observe:** How does the "Wait Time" metric react? AI should realize cars take longer to clear the junction and adjust the green-light duration accordingly.
*   **Goal for Improvement:** Add "Friction" logic where cars take longer to accelerate or brake during rain.

---

## 📊 Measuring Success (The Dashboard)
For the project to be successful, the following metrics must be updated in real-time on the frontend:

1.  **Queue Length:** Total number of vehicles currently stopped.
2.  **Waiting Time:** The average delay per vehicle. This is our "North Star" metric.
3.  **Throughput:** Total number of vehicles that have successfully exited the junction.
4.  **Efficiency Delta:** A live percentage showing if the RL Agent is currently +X% faster or -X% slower than the baseline safely.

---

## 🚀 Future Roadmap: What to Improve Next
If you are looking to add value to this project, here are the high-priority areas:

*   **Multi-Agent Coordination:** Moving from controlling **one** junction to a **network** of junctions (e.g., the entire Silk Board to KR Puram corridor).
*   **Smart Pedestrians:** Adding pedestrian crossing buttons and measuring "Pedestrian Delay."
*   **Predictive Demand:** Using the CSV data to *predict* the next hour's traffic and pre-loading a policy.
*   **V2V Communication:** simulate "Connected Vehicles" that tell the traffic light exactly how far away they are.

---

**Everything in this project is built to answer one question:**
> "If we replaced the timers in Bangalore with AI tomorrow, how many minutes would the average commuter save?"
