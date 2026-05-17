from models.patient import PatientInput, IntakeResult
from utils.llm_client import ask_llm
from typing import List

RED_FLAG_KEYWORDS = [
    "chest pain", "shortness of breath", "difficulty breathing",
    "loss of consciousness", "severe headache", "sudden numbness",
    "coughing blood", "uncontrolled bleeding", "stroke", "seizure",
    "suicidal", "overdose", "allergic reaction", "swelling throat"
]

SYSTEM_PROMPT = """
You are a medical intake assistant AI. Your job is to:
1. Read a patient's submitted symptoms and information.
2. Write a clear, structured plain-English summary for a doctor.
3. Identify any immediately concerning or red-flag symptoms.
4. Be factual, calm, and clinical in tone.
Do NOT diagnose the patient. Only summarize and flag.
"""

def detect_red_flags(symptoms: List[str], notes: str = "") -> List[str]:
   
    flags = []
    all_text = " ".join(symptoms).lower() + " " + notes.lower()
    for keyword in RED_FLAG_KEYWORDS:
        if keyword in all_text:
            flags.append(keyword)
    return flags


def run_intake_agent(patient_data: PatientInput) -> IntakeResult:
  
    print(f"[Intake Agent] Processing patient: {patient_data.full_name}")

    red_flags = detect_red_flags(
        patient_data.symptoms,
        patient_data.additional_notes or ""
    )

    user_prompt = f"""
    Patient Name: {patient_data.full_name}
    Age: {patient_data.age}
    Gender: {patient_data.gender}
    Symptoms: {", ".join(patient_data.symptoms)}
    Duration: {patient_data.symptom_duration}
    Severity (self-reported): {patient_data.severity}
    Current Medications: {", ".join(patient_data.current_medications) or "None"}
    Known Allergies: {", ".join(patient_data.known_allergies) or "None"}
    Medical History: {", ".join(patient_data.medical_history) or "None"}
    Additional Notes: {patient_data.additional_notes or "None"}

    Please write a structured intake summary for the attending physician.
    """
    try:        
        parsed_summary = ask_llm(SYSTEM_PROMPT, user_prompt)
    except Exception as e:        
        print(f"[Intake Agent] LLM call failed: {e}")        
        parsed_summary = "AI summary unavailable. Please review patient data manually."
        
    required_fields = [
        patient_data.full_name,
        patient_data.symptoms,
        patient_data.age
    ]
    intake_status = "complete" if all(required_fields) else "incomplete"

    print(f"[Intake Agent] Done. Red flags found: {red_flags or 'None'}")

    return IntakeResult(
        patient=patient_data,
        parsed_summary=parsed_summary,
        red_flags=red_flags,
        intake_status=intake_status
    )
