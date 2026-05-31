import time
import json
from fastapi import FastAPI, Depends, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta

from backend.config import active_config, ProxyConfig
from backend.database import init_db, get_db, ProxyLog, add_proxy_log
from backend.guardrails import detect_and_handle_pii, evaluate_prompt_injection, evaluate_toxicity, evaluate_hallucination
from backend.mock_llm import mock_completion_sync, mock_completion_stream

# Import litellm safely
try:
    import litellm
except ImportError:
    litellm = None

app = FastAPI(title="VigilAI Security Proxy & Observability")

# Enable CORS for local cross-origin frontend hosting
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize database tables on startup
init_db()

# Pydantic schemas for request validations
class ChatRequest(BaseModel):
    prompt: str
    model: Optional[str] = None
    temperature: Optional[float] = None
    stream: Optional[bool] = False

# Configuration update schema
class ConfigUpdate(BaseModel):
    enable_prompt_injection: bool
    enable_pii_detection: bool
    enable_toxicity_filter: bool
    enable_hallucination_guard: bool
    pii_action: str
    scan_email: bool
    scan_ssn: bool
    scan_credit_card: bool
    scan_phone: bool
    scan_ip: bool
    injection_sensitivity: float
    toxicity_threshold: float
    upstream_model: str
    openai_api_key: str
    mock_llm_mode: bool

@app.get("/api/config")
def get_config():
    """Retrieve the current active configurations."""
    return active_config.model_dump()

@app.post("/api/config")
def update_config(payload: ConfigUpdate):
    """Updates the active configurations and persists them."""
    global active_config
    for key, value in payload.model_dump().items():
        setattr(active_config, key, value)
    active_config.save()
    return {"status": "success", "config": active_config.model_dump()}

@app.get("/api/logs")
def get_logs(
    db: Session = Depends(get_db),
    status: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0)
):
    """Retrieves paginated logs from SQLite database with filtering options."""
    query = db.query(ProxyLog)
    
    if status and status != "ALL":
        query = query.filter(ProxyLog.status == status)
        
    if search:
        query = query.filter(
            ProxyLog.original_prompt.contains(search) | 
            ProxyLog.response.contains(search)
        )
        
    total_count = query.count()
    logs = query.order_by(ProxyLog.timestamp.desc()).offset(offset).limit(limit).all()
    
    formatted_logs = []
    for log in logs:
        try:
            violated = json.loads(log.violated_rules)
        except Exception:
            violated = []
            
        formatted_logs.append({
            "id": log.id,
            "timestamp": log.timestamp.isoformat(),
            "model_used": log.model_used,
            "original_prompt": log.original_prompt,
            "processed_prompt": log.processed_prompt,
            "response": log.response,
            "status": log.status,
            "latency_ms": log.latency_ms,
            "cost_usd": log.cost_usd,
            "input_tokens": log.input_tokens,
            "output_tokens": log.output_tokens,
            "violated_rules": violated,
            "client_ip": log.client_ip
        })
        
    return {
        "total": total_count,
        "logs": formatted_logs
    }

@app.get("/api/metrics")
def get_metrics(db: Session = Depends(get_db)):
    """Computes aggregate analytics KPIs and telemetry for the HUD charts."""
    logs = db.query(ProxyLog).all()
    
    total = len(logs)
    if total == 0:
        return {
            "total_requests": 0,
            "allowed_requests": 0,
            "blocked_requests": 0,
            "block_rate_pct": 0.0,
            "avg_latency_ms": 0.0,
            "total_cost_usd": 0.0,
            "total_tokens": 0,
            "blocked_rules_breakdown": {},
            "recent_latency_chart": []
        }
        
    allowed = sum(1 for l in logs if l.status == "ALLOWED")
    blocked = total - allowed
    block_rate = (blocked / total) * 100
    
    avg_latency = sum(l.latency_ms for l in logs) / total
    total_cost = sum(l.cost_usd for l in logs)
    total_tokens = sum(l.input_tokens + l.output_tokens for l in logs)
    
    # Violations distribution
    rules_count = {}
    for l in logs:
        if l.status != "ALLOWED":
            try:
                violated = json.loads(l.violated_rules)
                for r in violated:
                    rules_count[r] = rules_count.get(r, 0) + 1
            except Exception:
                rules_count[l.status] = rules_count.get(l.status, 0) + 1
                
    # Sort last 12 entries for timeline chart
    sorted_logs = sorted(logs, key=lambda x: x.timestamp, reverse=True)[:12]
    recent_chart = [{
        "timestamp": l.timestamp.strftime("%H:%M:%S"),
        "latency_ms": l.latency_ms,
        "status": l.status,
        "cost_usd": l.cost_usd
    } for l in reversed(sorted_logs)]
    
    return {
        "total_requests": total,
        "allowed_requests": allowed,
        "blocked_requests": blocked,
        "block_rate_pct": round(block_rate, 2),
        "avg_latency_ms": round(avg_latency, 1),
        "total_cost_usd": round(total_cost, 6),
        "total_tokens": total_tokens,
        "blocked_rules_breakdown": rules_count,
        "recent_latency_chart": recent_chart
    }

def run_real_llm_completion(prompt: str, model: str, temp: float, api_key: str, stream: bool = False):
    """Invokes LiteLLM completion wrapper to contact upstream model."""
    if not litellm:
        raise Exception("LiteLLM is not installed on this server environment.")
    
    # Setup key locally for the call if provided, otherwise default to env
    local_env = {}
    if api_key:
        local_env["OPENAI_API_KEY"] = api_key
        
    # Execute litellm completion
    return litellm.completion(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        temperature=temp,
        stream=stream,
        api_key=api_key if api_key else None
    )

@app.post("/api/proxy/chat")
async def secure_proxy_chat(request: Request, payload: ChatRequest):
    """
    Main proxy checkpoint route.
    Runs pre-evaluation guardrails, routes requests, processes replies,
    logs results, and supports secure streaming.
    """
    start_time = time.time()
    client_ip = request.client.host if request.client else None
    prompt = payload.prompt
    
    # Defaults override
    target_model = payload.model or active_config.upstream_model
    temp = payload.temperature if payload.temperature is not None else active_config.default_temperature
    
    violated_rules = []
    processed_prompt = prompt
    
    # ==========================================
    # PRE-EXECUTION GUARDRAILS
    # ==========================================
    
    # 1. Prompt Injection Check
    injection_score, injection_reasons, is_injection_blocked = evaluate_prompt_injection(prompt)
    if is_injection_blocked:
        violated_rules.append(f"Prompt Injection (Score: {injection_score:.2f})")
        latency = (time.time() - start_time) * 1000
        block_msg = f"[SECURE GATEWAY BLOCKED]: Prompt Injection attack vector detected. Rule: {injection_reasons[0]}"
        add_proxy_log(
            model_used=target_model,
            original_prompt=prompt,
            processed_prompt=prompt,
            response=block_msg,
            status="BLOCKED_INJECTION",
            latency_ms=latency,
            cost_usd=0.0,
            input_tokens=0,
            output_tokens=0,
            violated_rules=violated_rules,
            client_ip=client_ip
        )
        if payload.stream:
            async def err_generator():
                yield f"data: {json.dumps({'error': block_msg, 'status': 'BLOCKED_INJECTION'})}\n\n"
            return StreamingResponse(err_generator(), media_type="text/event-stream")
        else:
            return {
                "response": block_msg,
                "status": "BLOCKED_INJECTION",
                "violated_rules": violated_rules,
                "latency_ms": latency
            }
            
    # 2. PII Scan Check
    processed_prompt, pii_detected, is_pii_blocked = detect_and_handle_pii(prompt)
    if is_pii_blocked:
        violated_rules.append(f"PII Leakage Blocked: {', '.join(pii_detected)}")
        latency = (time.time() - start_time) * 1000
        block_msg = f"[SECURE GATEWAY BLOCKED]: Request contains sensitive PII fields ({', '.join(pii_detected)})."
        add_proxy_log(
            model_used=target_model,
            original_prompt=prompt,
            processed_prompt=prompt,
            response=block_msg,
            status="BLOCKED_PII",
            latency_ms=latency,
            cost_usd=0.0,
            input_tokens=0,
            output_tokens=0,
            violated_rules=violated_rules,
            client_ip=client_ip
        )
        if payload.stream:
            async def err_generator():
                yield f"data: {json.dumps({'error': block_msg, 'status': 'BLOCKED_PII'})}\n\n"
            return StreamingResponse(err_generator(), media_type="text/event-stream")
        else:
            return {
                "response": block_msg,
                "status": "BLOCKED_PII",
                "violated_rules": violated_rules,
                "latency_ms": latency
            }

    # ==========================================
    # LLM EXECUTION LAYER
    # ==========================================
    
    # Check if the prompt was redacted
    if processed_prompt != prompt:
        violated_rules.append("PII Redacted")

    if payload.stream:
        # Generate Streaming Response
        async def stream_generator():
            full_response_buffer = ""
            try:
                if active_config.mock_llm_mode:
                    # Serve mock stream
                    for chunk in mock_completion_stream(processed_prompt):
                        content = chunk["choices"][0]["delta"].get("content", "")
                        full_response_buffer += content
                        yield f"data: {json.dumps({'chunk': content})}\n\n"
                else:
                    # Serve real LiteLLM stream
                    response_stream = run_real_llm_completion(
                        processed_prompt, target_model, temp, active_config.openai_api_key, stream=True
                    )
                    for chunk in response_stream:
                        content = chunk.choices[0].delta.content or ""
                        full_response_buffer += content
                        yield f"data: {json.dumps({'chunk': content})}\n\n"
            except Exception as e:
                err_msg = f"Upstream LLM error: {str(e)}"
                yield f"data: {json.dumps({'error': err_msg, 'status': 'ERROR'})}\n\n"
                return

            # ==========================================
            # POST-EXECUTION GUARDRAILS (FOR STREAM)
            # ==========================================
            final_status = "ALLOWED"
            latency = (time.time() - start_time) * 1000
            
            # Estimate tokens and costs (for streaming logs)
            in_tokens = len(processed_prompt.split()) * 2
            out_tokens = len(full_response_buffer.split()) * 2
            # LiteLLM cost calculation fallback: simple estimate or read model pricing
            cost_est = (in_tokens * 0.00000015) + (out_tokens * 0.0000006)
            
            # Post-check toxicity
            tox_score, tox_reasons, is_toxic = evaluate_toxicity(full_response_buffer)
            if is_toxic:
                final_status = "BLOCKED_TOXICITY"
                violated_rules.append(f"Toxicity Filter (Score: {tox_score:.2f})")
                yield f"data: {json.dumps({'warning': '[POST-STREAM WARNING: Output flagged for containing toxic content]', 'status': 'BLOCKED_TOXICITY'})}\n\n"
                
            # Post-check hallucinations
            is_hall, hall_reasons = evaluate_hallucination(processed_prompt, full_response_buffer)
            if is_hall:
                if final_status == "ALLOWED":
                    final_status = "BLOCKED_HALLUCINATION"
                violated_rules.append("Response Hallucination Detected")
                yield f"data: {json.dumps({'warning': '[POST-STREAM WARNING: Output flagged for potential hallucination loop]', 'status': 'BLOCKED_HALLUCINATION'})}\n\n"

            # Save the logged stream record
            add_proxy_log(
                model_used=target_model,
                original_prompt=prompt,
                processed_prompt=processed_prompt,
                response=full_response_buffer,
                status=final_status,
                latency_ms=latency,
                cost_usd=cost_est,
                input_tokens=in_tokens,
                output_tokens=out_tokens,
                violated_rules=violated_rules,
                client_ip=client_ip
            )
            yield "data: [DONE]\n\n"

        return StreamingResponse(stream_generator(), media_type="text/event-stream")

    else:
        # Sync Response Execution
        try:
            if active_config.mock_llm_mode:
                completion = mock_completion_sync(processed_prompt)
                response_text = completion["choices"][0]["message"]["content"]
                in_tokens = completion["usage"]["prompt_tokens"]
                out_tokens = completion["usage"]["completion_tokens"]
                cost = (in_tokens * 0.00000015) + (out_tokens * 0.0000006)
            else:
                completion = run_real_llm_completion(
                    processed_prompt, target_model, temp, active_config.openai_api_key, stream=False
                )
                response_text = completion.choices[0].message.content
                in_tokens = completion.usage.prompt_tokens
                out_tokens = completion.usage.completion_tokens
                # Extract cost if populated by LiteLLM tracker
                cost = getattr(completion, "_response_metadata", {}).get("cost", 0.0)
                if cost == 0.0:
                    cost = (in_tokens * 0.00000015) + (out_tokens * 0.0000006)
        except Exception as e:
            raise HTTPException(status_code=502, detail=f"Upstream LLM Connection Failed: {str(e)}")

        # ==========================================
        # POST-EXECUTION GUARDRAILS (SYNC RESPONSE)
        # ==========================================
        final_status = "ALLOWED"
        
        # 1. Output Toxicity Check
        tox_score, tox_reasons, is_toxic = evaluate_toxicity(response_text)
        if is_toxic:
            final_status = "BLOCKED_TOXICITY"
            violated_rules.append(f"Toxicity Filter (Score: {tox_score:.2f})")
            response_text = f"[SECURE GATEWAY BLOCKED]: LLM response contains toxic words or violates safety policy. Rule: {tox_reasons[0]}"
            
        # 2. Output Hallucination Check
        is_hall, hall_reasons = evaluate_hallucination(processed_prompt, response_text)
        if is_hall:
            if final_status == "ALLOWED":  # toxicity has higher priority
                final_status = "BLOCKED_HALLUCINATION"
            violated_rules.append("Response Hallucination Detected")
            response_text = f"[SECURE GATEWAY BLOCKED]: LLM response output failed internal consistency validation: {hall_reasons[0]}"

        latency = (time.time() - start_time) * 1000
        
        # Save transaction log
        add_proxy_log(
            model_used=target_model,
            original_prompt=prompt,
            processed_prompt=processed_prompt,
            response=response_text,
            status=final_status,
            latency_ms=latency,
            cost_usd=cost,
            input_tokens=in_tokens,
            output_tokens=out_tokens,
            violated_rules=violated_rules,
            client_ip=client_ip
        )
        
        return {
            "response": response_text,
            "status": final_status,
            "violated_rules": violated_rules,
            "latency_ms": latency,
            "cost_usd": cost,
            "tokens": in_tokens + out_tokens
        }

# Mount static files folder to serve the frontend web-app
app.mount("/", StaticFiles(directory="frontend", html=True), name="static")
