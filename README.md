# PitWall 🏁  
An explainable, data-driven Formula 1 race strategy explorer.

PitWall is an interactive web application that lets users explore tyre degradation behaviour and pit-stop strategy “what-if” scenarios for upcoming F1 race weekends.  
Rather than black-box predictions, PitWall focuses on **transparent, rule-based modelling** grounded in real historical data, live race metadata, and weather-aware adjustments.

This project is built as an **educational decision-support tool** — designed to help users understand *why* certain strategies work under specific conditions.

---

## Core Features

- 🔍 **Automatic race detection** using live F1 calendar data  
- 🎯 **Pirelli-aware tyre modelling** (slicks, inters, wets with compound mapping)
- 🌡️ **Weather & track temperature controls** with dry / damp / wet modes
- 📉 **Tyre degradation engine** built from real historical stints (FastF1)
- ⏱️ **Strategy simulator** evaluating realistic 1-stop and 2-stop strategies
- 📊 **Interactive visualisations** for degradation curves and stint timelines
- ✨ Polished UI with animations and a dark, pit-wall-inspired aesthetic

---

## Tech Stack

### Backend
- **FastAPI** (Python)
- Modular routers for calendar, weather, tyres, degradation, and simulation
- **FastF1** for historical lap and stint data
- **OpenF1 API** for race calendar and session metadata
- **OpenWeatherMap** for weather forecasts
- Disk-based JSON caching for performance and reproducibility

### Frontend
- **React + Vite + TypeScript**
- **Zustand** for cascading state management
- **Tailwind CSS** (dark-mode-first design)
- **Recharts** for degradation visualisation
- **Framer Motion** for UI transitions and interaction polish

---

## How It Works (High Level)

1. The app detects the **next race weekend** using OpenF1 session data  
2. Weather forecasts are fetched and converted into **track temperature estimates**  
3. Historical stints from FastF1 are used to generate **compound-specific degradation curves**  
4. A piecewise model applies:
   - linear degradation early in the stint  
   - accelerated degradation after a compound-specific “cliff”
5. The strategy engine evaluates multiple realistic pit-stop combinations
6. Results are ranked and visualised with **full explainability**

---

## Running Locally

### Backend (FastAPI)
```bash
cd backend
python -m venv .venv
# Activate venv:
# Windows: .venv\Scripts\activate
# macOS/Linux: source .venv/bin/activate

pip install -r requirements.txt
cp .env.example .env   # add your OpenWeatherMap API key
uvicorn app.main:app --reload --port 8000
```
### Frontend
```bash
cd frontend
npm install
npm run dev
```
The frontend proxies API calls to the backend via Vite (```/api → http://localhost:8000```).

### Design Philosophy
PitWall intentionally avoids machine learning in favour of:
- Explainable logic
- Real historical grounding
- Clear cause-and-effect relationships

This makes the tool suitable for:
- F1 fans wanting to understand race commentary
- Students learning decision systems and modelling
- Junior analysts and engineers
- Sim-racing and strategy enthusiasts

### Known Limitations (Intentional MVP Scope)
- Time-only simulation (no position or overtake modelling)
- Simplified wet-weather crossover logic
- No Safety Car / VSC modelling yet
- Pirelli compound nominations may be config-based per track
- Weather API key required for forecast data

### Data Sources & Credits
- FastF1 – historical race sessions and stints
- OpenF1 – live race calendar and session metadata
- OpenWeatherMap – weather forecasts

### License
MIT
