from pydantic import BaseModel
from typing import Optional, List

class PatientInput(BaseModel):
    full_name: str
    age: int
    gender: str
    symptoms: List[str]
    symptom_duration: str
    severity: str
    current_medications: List[str]
    known_allergies: List[str]
    medical_history: List[str]
    additional_notes: Optional[str] = None


class IntakeResult(BaseModel):
    patient: PatientInput
    parsed_summary: str
    red_flags: List[str]
    intake_status: str


class TriageResult(BaseModel):
    urgency_level: str          # "low", "medium", "high", "critical"
    urgency_score: int          # 1–10
    reasoning: str
    recommended_action: str
    critical_flags: List[str]


class DrugHistoryResult(BaseModel):
    interactions_found: List[str]
    risk_level: str             # "none", "moderate", "severe"
    history_flags: List[str]
    recommendations: str


class FinalReport(BaseModel):
    patient_name: str
    timestamp: str
    intake: Optional[IntakeResult] = None
    triage: Optional[TriageResult] = None
    drug_history: Optional[DrugHistoryResult] = None
    pdf_path: str
    json_path: str
