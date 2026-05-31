# VigilAI Proxy

VigilAI Proxy is a local security gateway and logging proxy for LLM APIs. It intercepts requests sent to LLMs to check for prompt injections and sensitive PII, logs metrics (like cost and latency) to a local SQLite database, and provides a web dashboard for configuration and playground testing.

---

## Features

- **Prompt Injection Detection**: Blocks prompt injection attacks before they reach the model.
- **PII Redaction/Blocking**: Scans for emails, phone numbers, SSNs, credit cards, and IP addresses. Can either redact them or block the request.
- **Output Safety Filters**: Flags model outputs for toxicity or repetition loops.
- **Local Logging**: Stores logs, token counts, estimated costs, and latency details in an SQLite database.
- **Developer Dashboard**: A local dashboard to view logs, configure guardrail settings, and test prompts in a playground.
- **Mock Mode**: Built-in mock LLM generator for testing without an API key.

---

## Quick Start

### 1. Installation

```bash
# Clone the repository
git clone https://github.com/abdullah-153/VigilAI-Proxy.git
cd VigilAI-Proxy

# Create and activate virtual env
python -m venv venv

# Windows:
.\venv\Scripts\Activate.ps1

# Unix/macOS:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Run the Proxy

```bash
python -m uvicorn app.main:app --reload
```

The web dashboard will be available at [http://localhost:8000](http://localhost:8000).

---

## API Usage

The proxy acts as an intermediary. To send a secure request through the gateway:

```bash
curl -X POST http://localhost:8000/api/proxy/chat \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "Hello world",
    "model": "openai/gpt-4o-mini",
    "stream": false
  }'
```

### Response Format
```json
{
  "response": "Hello! How can I help you today?",
  "status": "ALLOWED",
  "violated_rules": [],
  "latency_ms": 120.5,
  "cost_usd": 0.000015,
  "tokens": 15
}
```

---

## Directory Structure

- `/app` - FastAPI application, database schema, and guardrail logic.
- `/frontend` - HTML/JS dashboard source code.
- `/tests` - Pytest integration and unit tests.
- `vigilai_config.json` - Security policy configuration file.
