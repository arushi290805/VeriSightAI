# VeriSight AI

VeriSight AI is a KPI intelligence-to-action engine prototype that demonstrates a
hybrid deterministic/LLM architecture. The platform parses raw business data,
statistically identifies anomalies, builds evidence ledgers deterministically,
and synthesizes executive "KPI Stories" securely via Google Gemini.

For a full description of the project features and architecture, visit the
[project documentation](https://github.com/example/verisight-ai).

Submit bug reports and feature suggestions, or track changes in the
[issue queue](https://github.com/example/verisight-ai/issues).


## Table of contents

- Requirements
- Recommended modules
- Installation
- Configuration
- Troubleshooting
- FAQ
- Maintainers


## Requirements

This project requires the following environments and tools to work:

- [Python 3.11+](https://www.python.org/)
- [Node.js 18+ (Next.js 14)](https://nodejs.org/)
- A [Google Gemini API Key](https://aistudio.google.com/)


## Recommended modules

No optional modules are recommended at this time.


## Installation

The installation process is split into backend and frontend setup.

### Backend

Navigate to the `backend` folder and set up the Python environment:

1. `cd backend`
2. `python -m venv venv`
3. `venv\Scripts\activate` (or `source venv/bin/activate` on macOS/Linux)
4. `pip install -r requirements.txt`

### Frontend

Open a new terminal window, navigate to the `frontend` folder, and install
dependencies:

1. `cd frontend`
2. `npm install`


## Configuration

1. Copy `.env.example` to `.env` inside the `backend` directory.
2. Add your Gemini API key: `GEMINI_API_KEYS=your_key_here`
3. Start the backend server by running `uvicorn main:app --reload` in the
   `backend` folder. The API will be available at http://127.0.0.1:8000. Note:
   SQLite tables (`app.db`) and synthetic data will auto-generate on startup.
4. Start the frontend development server by running `npm run dev` in the
   `frontend` folder. The application will be available at
   http://localhost:3000/dashboard.


## Troubleshooting

If the application fails to start or process data, check the following:

- Are you using the correct Node.js version? Ensure you are using v18+.
- Is the Gemini API key valid? Verify that the `.env` file is properly configured.
- Is the backend server running when accessing the frontend? The frontend
  requires the API on port 8000.


## FAQ

**Q: How does the hybrid architecture work?**

**A:** Statistics and deterministic logic detect and calculate metrics. Gemini (LLM)
only narrates, retrieves, and parses unstructured input. LLMs are strictly restricted
from computing math, determining statistical validity, or hallucinating causes without
direct evidence.

**Q: What are the main features of the platform?**

**A:** VeriSight AI features Semantic Contracts, a Detection Engine using Z-score
anomaly mapping, a deterministic Evidence Ledger, a Telemetry Module for tracking
API costs, and Secure Access Control using mock role-based row-level filters.


## Maintainers

- Raghav Ratan Yadav
