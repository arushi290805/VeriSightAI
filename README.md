# VeriSight AI

VeriSight AI is a KPI intelligence-to-action engine prototype that demonstrates a hybrid deterministic/LLM architecture. The platform parses raw business data, statistically identifies anomalies, builds evidence ledgers deterministically, and synthesizes executive "KPI Stories" securely via Google Gemini.

## Architecture Principles
1. **Statistics and deterministic logic detect and calculate.**
2. **Gemini (LLM) only narrates, retrieves, and parses unstructured input.**
3. **LLMs are strictly restricted from computing math, determining statistical validity, or hallucinating causes without direct evidence.**

## Prerequisites
- Python 3.11+
- Node.js 18+ (Next.js 14)
- A Google Gemini API Key

## Setup Instructions

### 1. Backend (FastAPI)
Navigate to the `backend` folder and set up the Python environment:
```powershell
cd backend
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

Set up your Gemini API keys:
1. Copy `.env.example` to `.env`
2. Add your Gemini API key:
```env
GEMINI_API_KEYS=your_key_here
```

Start the backend server:
```powershell
uvicorn main:app --reload
```
The API will be available at `http://127.0.0.1:8000`. 
*Note: SQLite tables (`app.db`) and synthetic data will auto-generate on startup.*

### 2. Frontend (Next.js)
Open a new terminal window, navigate to the `frontend` folder, and install dependencies:
```powershell
cd frontend
npm install
```

Start the development server:
```powershell
npm run dev
```
The application will be available at `http://localhost:3000/dashboard`.

## Features
- **Semantic Contracts:** YAML-defined KPI behaviors and algebraic relationships (e.g. `price + volume + mix == total_delta`).
- **Detection Engine:** Z-score anomaly mapping utilizing trailing histories (e.g., trailing 28 days for daily metrics), defaulting to mock peer-comparisons for sparse histories.
- **Evidence Ledger:** Deterministic evidence confidence rules identifying if a driver is `correlated_with`, `likely_contributed_to`, or has `causal_evidence`.
- **Telemetry Module:** SQLite-backed tracking wrapper that estimates real-time API dollar cost, response latency, and token consumption.
- **Secure Access Control:** Mock role-based row-level filters securing backend query bounds prior to rendering or generation.
