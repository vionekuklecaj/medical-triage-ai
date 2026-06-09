from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from models.patient import PatientInput, DrugHistoryResult
from agents.drug_history_agent import run_drug_history_agent

app = FastAPI(
    title="Drug Interaction & Medical History Agent API",
    description="Checks medications for interactions and flags pre-existing condition risks",
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
    return {"status": "Drug History Agent is running"}

@app.get("/health")
def health_check():
    return {"status": "healthy", "agent": "drug_history"}

@app.post("/drug-check", response_model=DrugHistoryResult)
def drug_check(patient: PatientInput):
    try:
        result = run_drug_history_agent(patient)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))