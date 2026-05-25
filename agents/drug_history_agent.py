import json
import requests
from models.patient import PatientInput, DrugHistoryResult
from utils.llm_client import ask_llm


# ── OpenFDA helper ────────────────────────────────────────────────────────────

def _truncate(field_values: list, max_chars: int = 400) -> list:
    """Trim long FDA label text so it doesn't overflow the LLM prompt."""
    if not field_values:
        return []
    return [field_values[0][:max_chars]]


def _fetch_fda_data(drug_name: str) -> dict:
    """Query OpenFDA for interaction/warning data on a single drug."""
    url = "https://api.fda.gov/drug/label.json"
    params = {
        "search": f'openfda.brand_name:"{drug_name}" OR openfda.generic_name:"{drug_name}"',
        "limit": 1,
    }
    headers = {"User-Agent": "MedicalTriageAI/1.0"}

    try:
        r = requests.get(url, params=params, timeout=8, headers=headers)
        r.raise_for_status()
        results = r.json().get("results", [])

        if not results:
            params["search"] = drug_name
            r = requests.get(url, params=params, timeout=8, headers=headers)
            r.raise_for_status()
            results = r.json().get("results", [])

        if not results:
            return {"drug_name": drug_name, "note": "No FDA label data found"}

        label = results[0]
        return {
            "drug_name": drug_name,
            "drug_interactions": _truncate(label.get("drug_interactions", [])),
            "warnings": _truncate(label.get("warnings", [])),
            "contraindications": _truncate(label.get("contraindications", [])),
        }

    except Exception as e:
        print(f"[DrugHistoryAgent] OpenFDA error for '{drug_name}': {e}")
        return {"drug_name": drug_name, "note": f"FDA lookup failed: {str(e)}"}


def _fetch_all_fda_data(medications: list[str]) -> list[dict]:
    """Fetch FDA label data for every medication in the list."""
    return [_fetch_fda_data(drug.strip()) for drug in medications if drug.strip()]


# ── Main agent function ───────────────────────────────────────────────────────

def run_drug_history_agent(patient: PatientInput) -> DrugHistoryResult:
    medications = patient.current_medications or []
    allergies = patient.known_allergies or []
    medical_history = patient.medical_history or []

    if not medications:
        return DrugHistoryResult(
            interactions_found=[],
            risk_level="low",
            history_flags=[],
            recommendations="No current medications reported. No drug interaction analysis required.",
        )

    # Step 1 — pull FDA data for each medication
    fda_data = _fetch_all_fda_data(medications)

    # Step 2 — ask the LLM to analyze everything together
    system_prompt = """You are a clinical pharmacist AI assistant.
Your job is to review a patient's medication list, medical history, and FDA drug label data,
then identify drug-drug interactions, contraindications, and allergy risks.
Always respond with valid JSON only — no markdown, no extra text."""

    user_prompt = f"""Patient information:
- Current medications: {', '.join(medications)}
- Known allergies: {', '.join(allergies) if allergies else 'None reported'}
- Medical history: {', '.join(medical_history) if medical_history else 'None reported'}
 
FDA label data retrieved for each medication:
{json.dumps(fda_data, indent=2)}
 
Respond with ONLY this JSON structure:
{{
  "interactions_found": ["<describe each drug-drug interaction found>"],
  "risk_level": "low | moderate | high | critical",
  "history_flags": ["<describe each risk based on medical history or allergies>"],
  "recommendations": "<one paragraph of recommendations for the treating physician>"
}}
 
Rules:
- Name the specific drugs and conditions involved
- If nothing is found, return empty lists
- risk_level must be exactly one of: low, moderate, high, critical"""

    raw = ask_llm(system_prompt, user_prompt)

    # Step 3 — parse the JSON response
    try:
        clean = raw.strip()
        if "```" in clean:
            parts = clean.split("```")
            for part in parts:
                part = part.strip()
                if part.startswith("json"):
                    part = part[4:]
                part = part.strip()
                if part.startswith("{"):
                    clean = part
                    break
        start = clean.find("{")
        end = clean.rfind("}") + 1
        if start != -1 and end > start:
            clean = clean[start:end]
        parsed = json.loads(clean)

        return DrugHistoryResult(
            interactions_found=parsed.get("interactions_found", []),
            risk_level=parsed.get("risk_level", "low"),
            history_flags=parsed.get("history_flags", []),
            recommendations=parsed.get("recommendations", ""),
        )

    except (json.JSONDecodeError, KeyError) as e:
        print(f"[DrugHistoryAgent] Failed to parse LLM response: {e}")
        print(f"[DrugHistoryAgent] Raw response: {raw}")
        return DrugHistoryResult(
            interactions_found=["Analysis error — manual review required"],
            risk_level="moderate",
            history_flags=["LLM response could not be parsed"],
            recommendations="Automated analysis failed. Please perform a manual drug interaction review for this patient.",
        )
