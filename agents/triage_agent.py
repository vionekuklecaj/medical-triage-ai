from models.patient import IntakeResult, TriageResult
from utils.llm_client import ask_llm
from typing import List
import re

# Symptoms that immediately indicate critical/life-threatening urgency
CRITICAL_SYMPTOM_PATTERNS = [
    "chest pain", "shortness of breath", "difficulty breathing",
    "loss of consciousness", "unresponsive", "stroke", "seizure",
    "coughing blood", "uncontrolled bleeding", "swelling throat",
    "allergic reaction", "anaphylaxis", "overdose", "suicidal",
    "sudden numbness", "severe headache", "heart attack"
]

SYSTEM_PROMPT = """
You are a medical triage AI assistant. Your job is to assess the urgency of a patient's condition
based on their intake summary and symptoms.

You must respond ONLY in the following exact format — no extra text, no explanation outside the fields:

URGENCY_LEVEL: <one of: low / medium / high / critical>
URGENCY_SCORE: <integer from 1 to 10>
RECOMMENDED_ACTION: <one sentence describing what should happen next>
CRITICAL_FLAGS: <comma-separated list of critical symptoms found, or "none">

Urgency level guide:
- critical (9-10): Life-threatening. Immediate emergency intervention required.
- high (7-8): Serious condition. Needs urgent medical attention within the hour.
- medium (4-6): Moderate concern. Should be seen by a doctor today.
- low (1-3): Non-urgent. Can wait for a scheduled appointment.

Do NOT diagnose the patient. Only assess urgency based on the reported symptoms and history.
"""


def detect_critical_flags(intake: IntakeResult) -> List[str]:
    """
    Quick keyword scan before sending to LLM — catches obvious critical flags fast.
    """
    flags = []
    all_text = (
        " ".join(intake.patient.symptoms) + " " +
        (intake.patient.additional_notes or "") + " " +
        " ".join(intake.red_flags)
    ).lower()

    for pattern in CRITICAL_SYMPTOM_PATTERNS:
        if pattern in all_text:
            flags.append(pattern)

    return list(set(flags))  # deduplicate


def parse_triage_response(response_text: str, fallback_flags: List[str]) -> TriageResult:
    """
    Parses the structured LLM response into a TriageResult object.
    Falls back to 'high' urgency if parsing fails, to err on the side of caution.
    """
    try:
        urgency_level_match = re.search(r"URGENCY_LEVEL:\s*(\w+)", response_text, re.IGNORECASE)
        urgency_score_match = re.search(r"URGENCY_SCORE:\s*(\d+)", response_text, re.IGNORECASE)
        action_match = re.search(r"RECOMMENDED_ACTION:\s*(.+)", response_text, re.IGNORECASE)
        flags_match = re.search(r"CRITICAL_FLAGS:\s*(.+)", response_text, re.IGNORECASE)

        urgency_level = urgency_level_match.group(1).lower() if urgency_level_match else "high"
        urgency_score = int(urgency_score_match.group(1)) if urgency_score_match else 7
        recommended_action = action_match.group(1).strip() if action_match else "Seek immediate medical evaluation."

        raw_flags = flags_match.group(1).strip() if flags_match else "none"
        if raw_flags.lower() == "none":
            critical_flags = fallback_flags
        else:
            critical_flags = [f.strip() for f in raw_flags.split(",")]

        # Validate urgency level is one of the expected values
        valid_levels = {"low", "medium", "high", "critical"}
        if urgency_level not in valid_levels:
            urgency_level = "high"

        # Clamp score between 1-10
        urgency_score = max(1, min(10, urgency_score))

        return TriageResult(
            urgency_level=urgency_level,
            urgency_score=urgency_score,
            recommended_action=recommended_action,
            critical_flags=critical_flags
        )

    except Exception as e:
        print(f"[Triage Agent] Failed to parse LLM response: {e}")
        # Safe fallback — assume high urgency if we can't parse
        return TriageResult(
            urgency_level="high",
            urgency_score=7,
            recommended_action="Unable to parse triage response. Manual review required immediately.",
            critical_flags=fallback_flags
        )


def run_triage_agent(intake_result: IntakeResult) -> TriageResult:
    """
    Main triage function. Takes the output of the Intake Agent and returns
    a TriageResult with urgency level, score, recommended action, and critical flags.
    """
    patient = intake_result.patient
    print(f"[Triage Agent] Triaging patient: {patient.full_name}")

    # Pre-scan for critical flags before LLM call
    critical_flags = detect_critical_flags(intake_result)

    user_prompt = f"""
Patient Name: {patient.full_name}
Age: {patient.age}
Gender: {patient.gender}
Symptoms: {", ".join(patient.symptoms)}
Duration: {patient.symptom_duration}
Self-Reported Severity: {patient.severity}
Current Medications: {", ".join(patient.current_medications) if patient.current_medications else "None"}
Known Allergies: {", ".join(patient.known_allergies) if patient.known_allergies else "None"}
Medical History: {", ".join(patient.medical_history) if patient.medical_history else "None"}
Additional Notes: {patient.additional_notes or "None"}

Intake Summary (from Intake Agent):
{intake_result.parsed_summary}

Red Flags Detected by Intake Agent: {", ".join(intake_result.red_flags) if intake_result.red_flags else "None"}

Based on all the above, assess the urgency of this patient's condition.
"""

    try:
        response_text = ask_llm(SYSTEM_PROMPT, user_prompt)
        print(f"[Triage Agent] LLM response received.")
        triage_result = parse_triage_response(response_text, critical_flags)

    except Exception as e:
        print(f"[Triage Agent] LLM call failed: {e}")
        # Safe fallback
        triage_result = TriageResult(
            urgency_level="high",
            urgency_score=7,
            recommended_action="AI triage unavailable. Please assess this patient manually and urgently.",
            critical_flags=critical_flags
        )

    print(f"[Triage Agent] Done. Urgency: {triage_result.urgency_level.upper()} (score: {triage_result.urgency_score}/10)")
    return triage_result