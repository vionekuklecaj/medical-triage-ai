import httpx
import json
import os
from datetime import datetime
from models.patient import (
    PatientInput, IntakeResult, TriageResult, DrugHistoryResult, FinalReport
)
from utils.report_generator import generate_pdf_report

INTAKE_URL  = "http://localhost:8001/intake"
TRIAGE_URL  = "http://localhost:8002/triage"
DRUG_URL    = "http://localhost:8003/drug-check"
TIMEOUT     = 30


def _call_intake(patient: PatientInput) -> IntakeResult | None:
    try:
        r = httpx.post(INTAKE_URL, json=patient.model_dump(), timeout=TIMEOUT)
        r.raise_for_status()
        return IntakeResult(**r.json())
    except Exception as e:
        print(f"[Lead Agent] Intake agent unreachable: {e}")
        return None


def _call_triage(intake: IntakeResult) -> TriageResult | None:
    try:
        r = httpx.post(TRIAGE_URL, json=intake.model_dump(), timeout=TIMEOUT)
        r.raise_for_status()
        return TriageResult(**r.json())
    except Exception as e:
        print(f"[Lead Agent] Triage agent unreachable: {e}")
        return None


def _call_drug_history(patient: PatientInput) -> DrugHistoryResult | None:
    try:
        r = httpx.post(DRUG_URL, json=patient.model_dump(), timeout=TIMEOUT)
        r.raise_for_status()
        return DrugHistoryResult(**r.json())
    except Exception as e:
        print(f"[Lead Agent] Drug history agent unreachable: {e}")
        return None


def run_lead_agent(patient: PatientInput) -> FinalReport:
    print(f"[Lead Agent] Starting pipeline for: {patient.full_name}")

    intake      = _call_intake(patient)
    triage      = _call_triage(intake) if intake else None
    drug_history = _call_drug_history(patient)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_name = patient.full_name.replace(" ", "_")
    os.makedirs("output/reports", exist_ok=True)
    pdf_path  = f"output/reports/{safe_name}_{timestamp}.pdf"
    json_path = f"output/reports/{safe_name}_{timestamp}.json"

    report = FinalReport(
        patient_name=patient.full_name,
        timestamp=timestamp,
        intake=intake,
        triage=triage,
        drug_history=drug_history,
        pdf_path=pdf_path,
        json_path=json_path,
    )

    generate_pdf_report(report, pdf_path)

    with open(json_path, "w") as f:
        json.dump(report.model_dump(), f, indent=2, default=str)

    print(f"[Lead Agent] PDF  → {pdf_path}")
    print(f"[Lead Agent] JSON → {json_path}")
    return report
