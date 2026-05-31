# VigilAI Proxy

VigilAI Proxy is a security gateway and observability ledger for Large Language Models (LLMs). It acts as a reverse proxy middleware positioned between client applications and upstream LLM providers (e.g., OpenAI or local endpoints via LiteLLM). VigilAI intercepts prompt payloads, executes pre-routing safety scans (for prompt injection and PII leakage), processes upstream completions, runs post-execution output filters (for toxicity and hallucination loops), and commits metadata and transaction analytics to a local SQLite database for auditing.

The system features a developer console dashboard that allows administrators to monitor performance telemetry in real time, configure guardrail sensitivities, and test security rules interactively.

---

## Architecture Overview

```
 [Client Application]
          │
          ▼
 [FastAPI Gateway]
          │
          ├─► [Pre-Execution Scan] ──► PII Scanner & Jailbreak Classifier
          │
          ▼
   [LiteLLM Router] ────────────────► Upstream LLM Provider
          │
          ▼
 [Post-Execution Scan] ─────────────► Toxicity & Hallucination Filter
          │
          ├─► [Database Ledger] ────► SQLite Storage
          │
          ▼
 [Client Application]
```

---

## Features

### 1. Pre-Route Safety Scanners
* **Prompt Injection Shield**: Identifies command overrides, system prompt extraction, Base64 obfuscation vectors, and adversarial instructions using a weighted rule matrix.
* **PII Leakage Scanner**: Scans inputs for email addresses, IPv4/IPv6 addresses, telephone numbers, Social Security Numbers (SSNs), and Credit Card Numbers (validated using the Luhn checksum algorithm). Rules can be configured to block request routing or redact detected fields.

### 2. Post-Route Output Filters
* **Toxicity Classifier**: Inspects model response buffers for profanity, hate speech, and explicit content.
* **Hallucination Loop Guard**: Evaluates generated text for repetition patterns and structural loop cycles to prevent runaway token consumption.

### 3. Unified Integration
* Uses `LiteLLM` to interface with upstream LLM APIs, providing model transparency and fallback routing.
* Tracks input and output tokens to calculate execution costs.

### 4. Telemetry and Settings Hub
* Persists configuration schemas to a centralized JSON schema.
* Includes an offline simulator mode to mock LLM outputs for sandbox testing without upstream API credentials.
* Logs latency, payload parameters, rule flags, and pricing telemetry.

---

## Project Structure

```
VigilAI-Proxy/
├── app/
│   ├── __init__.py
│   ├── config.py       # Configuration schemas and JSON persistence
│   ├── database.py     # SQLAlchemy models and SQLite connection
│   ├── guardrails.py   # PII, injection, toxicity, and loop checkers
│   ├── main.py         # FastAPI application and proxy endpoints
│   └── mock_llm.py     # Mock stream and sync responders
├── frontend/           # HTML, CSS, and JS files for the dashboard
├── tests/              # Pytest suite files
├── requirements.txt    # Application dependencies
└── vigilai_config.json # Local settings file
```

---

## Installation and Setup

### Prerequisites
* Python 3.12+

### 1. Initialize and Activate Virtual Environment
```bash
python -m venv venv
```

* **Windows PowerShell**:
  ```powershell
  .\venv\Scripts\Activate.ps1
  ```
* **Windows Command Prompt**:
  ```cmd
  .\venv\Scripts\activate.bat
  ```
* **macOS / Linux**:
  ```bash
  source venv/bin/activate
  ```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Run FastAPI Gateway
```bash
python -m uvicorn app.main:app --reload
```

The gateway exposes:
* Dashboard UI: [http://localhost:8000](http://localhost:8000)
* API Swagger Docs: [http://localhost:8000/docs](http://localhost:8000/docs)

---

## Sandbox Testing

* **Offline Mock Mode**: By default, `mock_llm_mode` is enabled. You can submit prompts in the playground to view telemetry changes and logs without external keys.
* **Upstream LLM Mode**: To test with real OpenAI models:
  1. Open the **Security Matrix** configuration pane.
  2. Disable **Offline Mock LLM Simulator**.
  3. Enter an active `OPENAI_API_KEY`.
  4. Save the configuration and run prompts in the playground.
