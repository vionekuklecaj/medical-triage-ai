from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from models.patient import PatientInput, IntakeResult
from agents.intake_agent import run_intake_agent

app = FastAPI(
    title="Patient Intake Agent API",
    description="Handles patient intake and preliminary triage flagging",
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
    return {"status": "Intake Agent is running"}

@app.get("/health")
def health_check():
    return {"status": "healthy", "agent": "intake"}

@app.post("/intake", response_model=IntakeResult) 
def intake(patient: PatientInput):
    try:
        result = run_intake_agent(patient)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

