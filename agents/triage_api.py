from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from models.patient import IntakeResult, TriageResult
from agents.triage_agent import run_triage_agent

app = FastAPI(
    title="Triage & Urgency Agent API",
    description="Scores symptom severity and classifies urgency from intake results",
    version="1.0.0"
)


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def root():
    return {"status": "Triage Agent is running"}

@app.get("/health")
def health_check():
    return {"status": "healthy", "agent": "triage"}

@app.post("/triage", response_model=TriageResult)
def triage(intake: IntakeResult):
    try:
        result = run_triage_agent(intake)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))