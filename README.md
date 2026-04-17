# DataChat MVP

A simple, working local MVP to chat with your CSV or Excel datasets using FastAPI, React, and Gemini AI.

## Project Structure

```text
backend/         # FastAPI server
frontend/        # React + Vite client
README.md        # This file
.gitignore
```

## Prerequisites

- [Python 3.10+](https://www.python.org/downloads/)
- [Node.js 18+](https://nodejs.org/)
- A Google Gemini API Key

## Local Setup (Windows PowerShell)

### 1. Backend Setup

Open a new PowerShell window:

```powershell
# Navigate to backend
cd backend

# Create Virtual Environment
python -m venv venv

# Activate Environment
.\venv\Scripts\Activate.ps1

# If you get an execution policy error, run:
# Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
# .\venv\Scripts\Activate.ps1

# Install Dependencies
pip install -r requirements.txt

# Configure Environment
# Open backend/.env and add your GEMINI_API_KEY
# Default model fallback logic will handle version mismatches automatically.

# Run Server
uvicorn app.main:app --reload
```

- **Backend URL:** [http://localhost:8000](http://localhost:8000)
- **API Docs:** [http://localhost:8000/docs](http://localhost:8000/docs)

### 2. Frontend Setup

Open a second PowerShell window:

```powershell
# Navigate to frontend
cd frontend

# Install Dependencies
npm install

# Run Dev Server
npm run dev
```

- **Frontend URL:** [http://localhost:5173](http://localhost:5173)

## How it Works

1. **Upload:** Upload a `.csv` or `.xlsx` file. The backend profiles the data using Pandas to extract column names, types, and sample statistics.
2. **Profile:** A compact structured context is generated.
3. **Chat:** When you ask a question:
   - The backend first tries to answer directly via Python (e.g., "how many rows?").
   - If complexity is high, it sends the compact context + your question to Gemini.
4. **Model Discovery:** The backend automatically lists available Gemini models and selects the best one (Flash/Pro) that supports content generation, avoiding "404 model not found" errors.

## Troubleshooting

- **Gemini 404 Errors:** The app uses `client.models.list()` at startup to pick a working model. Ensure your API key is valid.
- **File Upload Errors:** Ensure the file is not open in Excel while uploading (Excel sometimes locks files).
- **CORS Issues:** If the frontend can't talk to the backend, verify `CORS_ORIGINS` in `backend/.env` matches your frontend URL.
