# AI Medical Intake & Triage System

A multi-agent pipeline. The **Lead Orchestrator** (`main.py`) calls three agent
services over HTTP, collects their results, and generates a doctor-ready report
(PDF + JSON).

## Architecture

This system is **microservices**, not monolithic. The orchestrator
(`agents/lead_agent.py`) makes HTTP calls to each agent — it does not import
them as functions. Every agent therefore runs as its own FastAPI service on its
own port.

| Component        | File                          | Port | Endpoint      | Input          | Output             |
|------------------|-------------------------------|------|---------------|----------------|--------------------|
| Intake (P1)      | `agents/intake_api.py`        | 8001 | `/intake`     | `PatientInput` | `IntakeResult`     |
| Triage (P2)      | `agents/triage_api.py`        | 8002 | `/triage`     | `IntakeResult` | `TriageResult`     |
| Drug History (P3)| `agents/drug_history_api.py`  | 8003 | `/drug-check` | `PatientInput` | `DrugHistoryResult`|
| Lead / Report(P4)| `main.py`                     | 8000 | `/run`        | `PatientInput` | `FinalReport`      |

The ports and request/response shapes are hardcoded in `lead_agent.py`. Do not
change one side without the other.

## Running

From the project root (the folder containing `main.py`):

**Windows (all four at once):**
```
start_all.bat
```

**Manually / cross-platform (one terminal each):**
```
uvicorn agents.intake_api:app       --host 0.0.0.0 --port 8001 --reload
uvicorn agents.triage_api:app       --host 0.0.0.0 --port 8002 --reload
uvicorn agents.drug_history_api:app --host 0.0.0.0 --port 8003 --reload
python main.py
```

All three agent services must be up before you POST to the orchestrator.

## Usage

Send patient data to the orchestrator:
```
POST http://localhost:8000/run
```
Or use the Swagger UI at http://localhost:8000/docs

Reports are written to `output/reports/`.

## Known behavior worth noting

In `lead_agent.py`, triage only runs if intake succeeds
(`_call_triage(intake) if intake else None`). If the intake service is down,
the triage section of the report will be empty **even if the triage service is
healthy**. When debugging a missing section, check intake first.

Drug history is called independently of intake, so it is unaffected by this.