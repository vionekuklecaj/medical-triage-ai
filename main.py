from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from models.patient import PatientInput, FinalReport
from agents.lead_agent import run_lead_agent

app = FastAPI(
    title="Lead Orchestrator Agent",
    description="Coordinates the full medical intake pipeline and generates doctor-ready reports",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def root():
    return {"status": "Lead Agent is running"}


@app.get("/health")
def health():
    return {"status": "healthy", "agent": "lead"}


@app.post("/run", response_model=FinalReport)
def run_pipeline(patient: PatientInput):
    """
    Accepts patient data, runs the full agent pipeline, and returns
    paths to the generated PDF and JSON reports.
    """
    try:
        report = run_lead_agent(patient)
        return report
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
