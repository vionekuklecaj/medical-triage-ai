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
