import time
import random
from typing import Generator, Dict, Any

MOCK_ANSWERS = {
    "hello": "Hello! I am a simulated LLM endpoint running securely behind the VigilAI Proxy. Your connection is fully protected by our pre-execution and post-execution guardrail pipelines.",
    "recruiters": "Recruiters love the VigilAI Proxy project because it addresses the two most critical bottlenecks in enterprise GenAI adoption:\n1. **AI Safety & Compliance**: Guarding against prompt injection, data leaks (PII), and toxic outputs.\n2. **Observability**: Providing total transparency into cost, latency, tokens, and guardrail exceptions.\nIt demonstrates proficiency in FastAPI, SQLite database architecture, LiteLLM integrations, and cybersecurity fundamentals.",
    "pii": "This response contains mock sensitive data for scanning tests. For instance, my email is test.user@example.com and you can reach support at (555) 019-2834. Note: these values should be redacted if PII scanning is enabled!",
    "system": "The VigilAI Proxy is currently running in Secure Gateway Mode. All connections are routed through active filters. Model config: gpt-4o-mini. Latency latency budget: <150ms target."
}

def get_mock_response(prompt: str) -> str:
    prompt_lower = prompt.lower()
    for key, response in MOCK_ANSWERS.items():
        if key in prompt_lower:
            return response
            
    # Generic developer response
    return (
        f"Thank you for querying the VigilAI secure proxy playground.\n\n"
        f"You sent: \"{prompt}\"\n\n"
        f"This response is served by the local Mock LLM service. In production, this layer is handled "
        f"by LiteLLM, routing traffic to OpenAI, Anthropic, or local open-source models (via Ollama) "
        f"while generating token counts and cost telemetry logged directly into your DB for analysis."
    )

def mock_completion_stream(prompt: str, delay: float = 0.03) -> Generator[Dict[str, Any], None, None]:
    """Simulates a LiteLLM streaming completion delta response."""
    full_text = get_mock_response(prompt)
    words = full_text.split(" ")
    
    # Simulate a small startup delay
    time.sleep(0.15)
    
    for i, word in enumerate(words):
        # Re-add spaces except for the last word
        chunk_text = word if i == len(words) - 1 else word + " "
        yield {
            "choices": [
                {
                    "delta": {
                        "content": chunk_text
                    }
                }
            ]
        }
        time.sleep(delay + random.uniform(-0.01, 0.02))

def mock_completion_sync(prompt: str) -> Dict[str, Any]:
    """Simulates a LiteLLM synchronous completion response."""
    text = get_mock_response(prompt)
    input_tokens = len(prompt.split()) * 2
    output_tokens = len(text.split()) * 2
    
    return {
        "choices": [
            {
                "message": {
                    "content": text
                }
            }
        ],
        "usage": {
            "prompt_tokens": input_tokens,
            "completion_tokens": output_tokens,
            "total_tokens": input_tokens + output_tokens
        }
    }
