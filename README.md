# VigilAI Proxy (ShieldGuard) 🛡️

**VigilAI Proxy** is an enterprise-grade LLM Security Layer and Observability Gateway. Built as a middleware proxy sitting between users and upstream LLMs (such as OpenAI via LiteLLM or local models via Ollama), it intercepts queries, executes pre-execution safety scans, runs post-completion integrity checks, and logs granular transaction logs (costs, latency, tokens, safety status) to a database for observability auditing.

Featuring a premium developer-HUD single-page web dashboard, VigilAI allows users to interactively test prompt safety via a sandbox playground, configure security policy toggles, and view detailed telemetry audit reports.

---

## Key Features

1. **AI Safety Shield (Guardrails)**
   - **Prompt Injection (Jailbreak) Blocker**: Detects instructions overrides, system prompts leaking, Base64 bypass hacks, and adversarial instructions using heuristic weights.
   - **PII Leakage Scanner**: Identifies emails, IP addresses, phone numbers, SSNs, and credit cards (validated via Luhn Checksum algorithm to prevent false positives). Configurable to either block the transaction or redact fields before routing.
   - **Toxicity Classifier**: Analyzes LLM response outputs for profanity, explicit hate-speech, and slurs.
   - **Hallucination Loop Guard**: Catches infinite repetition loops and context leaking in response generation.

2. **Unified LLM Gateway (LiteLLM)**
   - Uses `LiteLLM` to support 100+ LLM APIs (OpenAI, Anthropic, Gemini, Ollama, etc.) with a single unified format.
   - Automatically computes token usage and exact pricing weights.

3. **Observability Log Ledger**
   - Logs metadata details to SQLite (UUID, timestamps, latency, costs, token usage, redacted details, violated rules).
   - Serves search-indexed, paginated transaction histories.

4. **Persisted Configuration Hub**
   - Instantly adjusts thresholds and toggle settings live from the UI, persisting configuration state to JSON.
   - **Offline Mock LLM Simulator**: Toggles mock execution to run the entire project offline without requiring external API keys.

---

## System Architecture

```
 User (UI)  --->  VigilAI Proxy (FastAPI) --->  [Pre-Execution Guardrails] 
                                                        │ (PII & Injection Scan)
                                                        ▼
 SQLite Log <---  [Post-Execution Guardrails] <--- LiteLLM (OpenAI/Local)
 Ledger            (Toxicity & Loop checks)
```

---

## Tech Stack

- **Backend**: Python 3.12, FastAPI, SQLAlchemy, SQLite, LiteLLM
- **Frontend**: Vanilla HTML5, CSS3, JavaScript ES6 (Cream-Orange dark-tinged HUD theme, Space Grotesk typography)

---

## Installation & Setup

1. **Clone the Repository** and navigate to the directory:
   ```bash
   cd c:\Programming\Portfolio
   ```

2. **Create a Virtual Environment**:
   ```bash
   python -m venv venv
   ```

3. **Activate the Virtual Environment**:
   - **Windows PowerShell**:
     ```powershell
     .\venv\Scripts\Activate.ps1
     ```
   - **Windows Command Prompt**:
     ```cmd
     .\venv\Scripts\activate.bat
     ```
   - **macOS / Linux**:
     ```bash
     source venv/bin/activate
     ```

4. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

5. **Run the FastAPI Server**:
   ```bash
   python -m uvicorn backend.main:app --reload
   ```

6. **Access the Dashboard**:
   - Open your browser and navigate to: [http://localhost:8000](http://localhost:8000)
   - To inspect the API documentation, visit: [http://localhost:8000/docs](http://localhost:8000/docs)

---

## Running Secure Inferences

- By default, the application runs in **Mock LLM Mode** so you do not need an OpenAI API key to view the dashboard functionalities.
- If you have an OpenAI key:
  1. Open the **Guardrail Settings Matrix** on the dashboard.
  2. Uncheck **Offline Mock LLM Simulator**.
  3. Input your key in the **OpenAI API Key** field.
  4. Click **Save Security Policy**.
  5. Go back to the **Interactive Sandbox**, type a prompt, and observe live OpenAI requests with real-time costs and logs!
