import streamlit as st
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models.patient import PatientInput
from agents.intake_agent import run_intake_agent

st.set_page_config(
    page_title="Medical Intake System",
    page_icon="[+]",
    layout="centered"
)

st.title("Patient Intake Form")
st.markdown("Please fill in your information accurately. This will be reviewed by a medical professional.")
st.divider()

with st.form("intake_form"):
    col1, col2 = st.columns(2)

    with col1:
        full_name = st.text_input("Full Name", placeholder="John Doe")
        age = st.number_input("Age", min_value=0, max_value=120, value=30)

    with col2:
        gender = st.selectbox("Gender", ["Male", "Female", "Other", "Prefer not to say"])
        severity = st.selectbox("How severe are your symptoms?", ["Mild", "Moderate", "Severe"])

    symptoms_raw = st.text_area(
        "Describe your symptoms (one per line)",
        placeholder="chest pain\nshortness of breath\nfatigue"
    )

    duration = st.text_input("How long have you had these symptoms?", placeholder="e.g. 2 days, 1 week")

    medications_raw = st.text_area(
        "Current Medications (one per line)",
        placeholder="Metformin 500mg\nLisinopril 10mg"
    )

    allergies_raw = st.text_input(
        "Known Allergies (comma-separated)",
        placeholder="Penicillin, Latex"
    )

    history_raw = st.text_area(
        "Medical History (one per line)",
        placeholder="Type 2 Diabetes\nHypertension"
    )

    notes = st.text_area("Additional Notes (optional)", placeholder="Anything else the doctor should know...")

    submitted = st.form_submit_button("Submit Intake Form", type="primary", use_container_width=True)


if submitted:
    
    if not full_name or not symptoms_raw or not duration:
        st.error("Please fill in your name, symptoms, and duration before submitting.")
    else:
        
        symptoms = [s.strip() for s in symptoms_raw.strip().splitlines() if s.strip()]
        medications = [m.strip() for m in medications_raw.strip().splitlines() if m.strip()]
        allergies = [a.strip() for a in allergies_raw.split(",") if a.strip()]
        history = [h.strip() for h in history_raw.strip().splitlines() if h.strip()]

        patient = PatientInput(
            full_name=full_name,
            age=int(age),
            gender=gender,
            symptoms=symptoms,
            symptom_duration=duration,
            severity=severity.lower(),
            current_medications=medications,
            known_allergies=allergies,
            medical_history=history,
            additional_notes=notes if notes else None
        )

        with st.spinner("Processing your intake form with AI..."):
            result = run_intake_agent(patient)

        st.divider()
        st.subheader("Intake Summary")

        if result.red_flags:
            st.error(f"Red Flags Detected: {', '.join(result.red_flags)}")
            st.warning("This patient may require urgent attention.")

        st.success(f"Intake Status: {result.intake_status.upper()}")

        st.markdown("**AI-Generated Clinical Summary:**")
        st.info(result.parsed_summary)

        st.session_state["intake_result"] = result
        st.caption("Intake result saved. Ready to pass to Triage Agent.")
