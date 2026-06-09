"""
Drug Interaction & Medical History Agent (Person 3)

Responsibilities:
  - Check the patient's current medications for interactions
  - Flag pre-existing condition risks from medical history
  - Cross-check medications against known allergies
  - Integrate with the public OpenFDA drug label API

IMPORTANT — scope / limitation (read before grading or deploying):
OpenFDA does NOT expose a true pairwise "does drug A interact with drug B"
endpoint. It exposes each drug's FDA label text. This agent therefore works by
fetching the label for each medication and scanning its `drug_interactions`,
`warnings`, `contraindications`, and `boxed_warning` text for mentions of the
patient's *other* medications, allergies, and conditions. This is a sound
text-matching heuristic suitable for a prototype, NOT a validated clinical
decision-support system. Output must always be reviewed by a licensed clinician.

API docs: https://open.fda.gov/apis/drug/label/
"""

import httpx
from typing import List, Optional
from models.patient import PatientInput, DrugHistoryResult

FDA_LABEL_URL = "https://api.fda.gov/drug/label.json"
TIMEOUT = 15

# Label sections most relevant to interaction / risk scanning.
SCANNED_SECTIONS = [
    "drug_interactions",
    "warnings",
    "warnings_and_cautions",
    "contraindications",
    "boxed_warning",
    "precautions",
]

# Curated set of high-risk pre-existing conditions. Keys are matched (as
# substrings) against the patient's medical_history entries. Values explain the
# general concern. Kept deliberately small and conservative.
HIGH_RISK_CONDITIONS = {
    "kidney disease":   "Impaired renal clearance can raise drug levels; dosing may need adjustment.",
    "renal":            "Impaired renal clearance can raise drug levels; dosing may need adjustment.",
    "liver disease":    "Impaired hepatic metabolism affects many drugs; dosing may need adjustment.",
    "hepatic":          "Impaired hepatic metabolism affects many drugs; dosing may need adjustment.",
    "heart failure":    "Fluid-retaining or cardiotoxic drugs may worsen heart failure.",
    "heart disease":    "Cardiac history raises risk with QT-prolonging or stimulant medications.",
    "hypertension":     "Some drugs (e.g. NSAIDs, decongestants) can raise blood pressure.",
    "diabetes":         "Some drugs affect blood glucose control.",
    "asthma":           "Beta-blockers and NSAIDs can trigger bronchospasm in some patients.",
    "copd":             "Respiratory-depressant drugs carry added risk.",
    "pregnancy":        "Many drugs are contraindicated or require caution in pregnancy.",
    "bleeding disorder":"Anticoagulant/antiplatelet drugs raise bleeding risk.",
    "ulcer":            "NSAIDs and steroids raise GI bleeding risk.",
}


def _fetch_label(drug_name: str) -> Optional[dict]:
    """
    Query the OpenFDA drug label API for a single medication. Searches both
    generic and brand name fields. Returns the first matching label record, or
    None on miss / error (so one bad drug never crashes the whole check).
    """
    query = f'openfda.generic_name:"{drug_name}" OR openfda.brand_name:"{drug_name}"'
    try:
        r = httpx.get(
            FDA_LABEL_URL,
            params={"search": query, "limit": 1},
            timeout=TIMEOUT,
        )
        if r.status_code == 404:
            # OpenFDA returns 404 when no records match the search.
            print(f"[Drug Agent] No FDA label found for '{drug_name}'.")
            return None
        r.raise_for_status()
        results = r.json().get("results", [])
        return results[0] if results else None
    except Exception as e:
        print(f"[Drug Agent] OpenFDA lookup failed for '{drug_name}': {e}")
        return None


def _section_text(label: dict, field: str) -> str:
    """Flatten an OpenFDA label section (a list of strings) into lowercase text."""
    val = label.get(field, [])
    if isinstance(val, list):
        return " ".join(str(v) for v in val).lower()
    return str(val).lower()


def _combined_text(label: dict) -> str:
    """Join all scanned label sections into one lowercase blob for matching."""
    return " ".join(_section_text(label, f) for f in SCANNED_SECTIONS)


def check_interactions(medications: List[str]) -> List[str]:
    """
    For each medication, fetch its label and check whether any OTHER current
    medication is mentioned in its interaction/warning text. Returns a
    de-duplicated list of human-readable interaction findings.
    """
    findings: List[str] = []
    seen_pairs = set()

    # Cache labels so we don't fetch the same drug twice.
    labels = {med: _fetch_label(med) for med in medications}

    for med in medications:
        label = labels.get(med)
        if not label:
            continue
        text = _combined_text(label)

        for other in medications:
            if other == med:
                continue
            pair = tuple(sorted([med.lower(), other.lower()]))
            if pair in seen_pairs:
                continue
            if other.lower() in text:
                seen_pairs.add(pair)
                findings.append(
                    f"Potential interaction: '{med}' label references '{other}'."
                )

    return findings


def check_allergies(medications: List[str], allergies: List[str]) -> List[str]:
    """
    Check whether any medication's label text mentions one of the patient's
    known allergies (warnings / contraindications). Surfaced as interaction
    findings because an allergy match is a high-priority safety flag.
    """
    findings: List[str] = []
    if not allergies:
        return findings

    for med in medications:
        label = _fetch_label(med)
        if not label:
            continue
        text = _combined_text(label)
        for allergy in allergies:
            if allergy.lower() in text:
                findings.append(
                    f"ALLERGY ALERT: '{med}' label references known allergy '{allergy}'."
                )
    return findings


def check_medical_history(medications: List[str], history: List[str]) -> List[str]:
    """
    Flag pre-existing condition risks. Two passes:
      1. Match the patient's history against the curated high-risk condition set.
      2. Cross-check each medication's label for mentions of the patient's
         conditions (e.g. a contraindication naming the condition).
    """
    flags: List[str] = []

    # Pass 1 — curated high-risk conditions.
    for condition in history:
        c = condition.lower()
        for key, note in HIGH_RISK_CONDITIONS.items():
            if key in c:
                flags.append(f"{condition}: {note}")
                break

    # Pass 2 — medication labels that explicitly reference a patient condition.
    for med in medications:
        label = _fetch_label(med)
        if not label:
            continue
        text = _combined_text(label)
        for condition in history:
            if condition.lower() in text:
                flags.append(
                    f"'{med}' label references pre-existing condition '{condition}' — review for caution/contraindication."
                )

    # De-duplicate while preserving order.
    seen = set()
    deduped = []
    for f in flags:
        if f not in seen:
            seen.add(f)
            deduped.append(f)
    return deduped


def _assess_risk(interactions: List[str], history_flags: List[str]) -> str:
    """Derive an overall risk level from the findings."""
    has_allergy = any("ALLERGY ALERT" in i for i in interactions)
    score = 0
    score += 3 * len(interactions)
    score += 1 * len(history_flags)
    if has_allergy:
        score += 5

    # NOTE: these strings must match the keys in report_generator.RISK_COLORS
    # ("none" / "moderate" / "severe"), or the PDF risk badge falls back to grey.
    if score == 0:
        return "none"
    if score <= 3:
        return "moderate"
    return "severe"


def _build_recommendations(risk_level: str, interactions: List[str],
                           history_flags: List[str]) -> str:
    """Produce a short, plain-language recommendation string."""
    if risk_level == "severe":
        return ("Severe risk: pharmacist and prescribing physician must review all "
                "flagged interactions and allergy alerts before any medication is "
                "administered or continued.")
    if risk_level == "moderate":
        return ("Moderate risk: clinician should review the flagged conditions and "
                "interactions and consider dose adjustment or monitoring.")
    if not interactions and not history_flags:
        return ("No interactions, allergy conflicts, or high-risk history flags "
                "detected from available FDA label data. Routine review still advised.")
    return "Low risk: note the flags below at the next clinical review."


def run_drug_history_agent(patient: PatientInput) -> DrugHistoryResult:
    """
    Main entry point. Takes patient data and returns a DrugHistoryResult with
    interactions found, an overall risk level, medical-history flags, and a
    recommendation. Matches the contract expected by lead_agent (/drug-check).
    """
    print(f"[Drug Agent] Checking medications & history for: {patient.full_name}")

    meds = patient.current_medications or []
    allergies = patient.known_allergies or []
    history = patient.medical_history or []

    # No medications and no history → nothing to check.
    if not meds and not history:
        print("[Drug Agent] No medications or history provided.")
        return DrugHistoryResult(
            interactions_found=[],
            risk_level="none",
            history_flags=[],
            recommendations="No medications or medical history reported. No checks needed.",
        )

    interactions: List[str] = []
    if meds:
        interactions += check_interactions(meds)
        interactions += check_allergies(meds, allergies)

    history_flags = check_medical_history(meds, history)

    risk_level = _assess_risk(interactions, history_flags)
    recommendations = _build_recommendations(risk_level, interactions, history_flags)

    print(f"[Drug Agent] Done. Risk: {risk_level.upper()} | "
          f"{len(interactions)} interaction(s), {len(history_flags)} history flag(s).")

    return DrugHistoryResult(
        interactions_found=interactions,
        risk_level=risk_level,
        history_flags=history_flags,
        recommendations=recommendations,
    )