# PitWall 🏁  
**A transparent, data-driven Formula 1 race strategy explorer.**

PitWall is an end-to-end Formula 1 race strategy analysis tool that explores why certain strategies work — not just which one is fastest.

Unlike black-box prediction models, PitWall uses **explicit rules, real historical data, and deterministic simulations** to surface trade-offs between theoretical pace, historical race behaviour, and execution risk. Every recommendation is explainable.

---
## ✨ What PitWall Does
PitWall lets users explore race-weekend “what-if” scenarios by combining:
- Physics-based tyre degradation modelling
- Real historical race data (FastF1)
- Live or manual weather inputs
- Transparent rule-based reasoning

It answers questions like:
- *What strategy is fastest in clean air?*
- *What strategies usually happen at this circuit?*
- *How risky is this plan historically?*
- *Where does this strategy break if conditions change?*

## 🧠 Design Philosophy
PitWall is **not** a prediction engine.

It is a decision-support system designed around three layered lenses:

### 1️⃣ Theoretical Optimum

Physics-based simulation using:
- Tyre degradation curves (piecewise linear + cliff)
- Stint length limits
- Pit loss
- Total race time minimisation

>“What is fastest in ideal conditions?”

### 2️⃣ Historical Reality

Computed from real race data using FastF1:
- First-stop lap distributions (median + IQR)
- Stop count distributions (1-stop vs 2-stop vs chaos)
- Common strategy sequences
- Undercut / overcut effectiveness
- Out-lap penalties and traffic proxies
- Safety Car lap histograms (where data permits)

>“What actually happens here?”

Historical signals influence strategy ranking — they never override physics.

### 3️⃣ Execution Risk

How fragile a strategy is once the race starts:
- Distance from historical norms
- Number of cliff laps
- Dependency on undercuts
- Sensitivity to safety cars or weather volatility

>“How robust is this plan when reality intervenes?”


## 🏗️ Architecture & Tech Stack

### Backend
- **FastAPI** (Python)
- Modular routers for ```calendar```, ```weather```, ```tyres```, ```degradation```, ```simulation```, ```historical```
- **FastF1** for historical lap and stint data
- **OpenF1 API** for race calendar and session metadata
- **OpenWeatherMap** for weather forecasts
- Disk-based JSON caching for performance and reproducibility

### Frontend
- **React + Vite + TypeScript**
- **Zustand** for cascading state management
- **Tailwind CSS** (dark-mode-first design)
- **Recharts** + custom timelines for degradation and stints
- **Framer Motion** for UI transitions and interaction polish

## 📊 Key Features

#### Dynamic Race Context
- Auto-detects upcoming race via OpenF1
- Circuit metadata, lap count, pit loss, sprint flags
- Countdown to race weekend

#### Tyre Degradation Engine
- Real historical stints extracted via FastF1
- Per-compound degradation rate, cliff onset, and cliff severity
- Temperature-adjusted degradation
- Visual degradation curves with cliff markers

#### Strategy Simulator
- Evaluates realistic 1-stop and 2-stop strategies
- Supports dry, damp, and wet conditions
- Handles intermediate → slick crossover logic
- Outputs ranked strategies with full stint breakdowns

#### Historical Strategy Intelligence
- Circuit-specific historical profiles (cached)
- First-stop windows (median + IQR)
- Stop count distributions
- Common strategy sequences
- Undercut success rates and typical gains
- Historical signals apply small, transparent adjustments to strategy ranking

#### Strategy Explanations (Deterministic)
- Rule-based explanation layer (no ML required)
- Every explanation is generated only from simulation outputs and historical metrics
- Clearly labels simulated conditions vs live weather
- No predictions, no assumptions, no hallucinations

## 🔍 Transparency by Design
PitWall prioritises explainability:
- Every number shown is computed or sourced
- Historical data includes sample sizes and caveats
- If data is insufficient, PitWall says so
- Explanations reflect what was simulated, not what “might happen”

This mirrors how real race engineers reason under uncertainty.


## 🚫 What PitWall Intentionally Does *Not* Do (Yet)
- No live timing or position simulation
- No driver-specific performance modelling
- No Monte Carlo randomness in baseline recommendations
- No opaque machine-learning predictions

These are conscious design choices to preserve clarity and trust.


## 🧪 Data Sources & Credits
- FastF1 – historical race sessions and stints
- OpenF1 – live race calendar and session metadata
- OpenWeatherMap – weather forecasts


## 🚀 Getting Started

### Backend (FastAPI)
```bash
cd backend
pip install -r requirements.txt
uvicorn main:app --reload
```
### Frontend
```bash
cd frontend
npm install
npm run dev
```
The frontend proxies API calls to the backend via Vite (```/api → http://localhost:8000```).
Optional environment variables:
```bash
# Backend
OPENWEATHER_API_KEY=your_key_here

# Frontend (optional – explanation works without it)
VITE_OPENAI_API_KEY=optional
```
## 📌 Project Status
PitWall is a complete, working v1 focused on correctness, realism, and explainability.

Future extensions could include:
- Strategy robustness scoring
- Live race re-planning
- Driver-specific modelling
- Monte Carlo variability (opt-in)
--- 
### License
MIT
