import os
import json
from pydantic import BaseModel
from typing import Dict, Any

CONFIG_FILE = "vigilai_config.json"

class ProxyConfig(BaseModel):
    # Guardrails Toggles
    enable_prompt_injection: bool = True
    enable_pii_detection: bool = True
    enable_toxicity_filter: bool = True
    enable_hallucination_guard: bool = True
    
    # PII Configuration
    pii_action: str = "redact"  # "redact" or "block"
    scan_email: bool = True
    scan_ssn: bool = True
    scan_credit_card: bool = True
    scan_phone: bool = True
    scan_ip: bool = True
    
    # Thresholds (0.0 to 1.0)
    injection_sensitivity: float = 0.5
    toxicity_threshold: float = 0.6
    
    # LLM Settings
    upstream_model: str = "openai/gpt-4o-mini"
    openai_api_key: str = ""
    default_temperature: float = 0.7
    mock_llm_mode: bool = True  # Default to True so it runs out-of-the-box

    @classmethod
    def load(cls) -> "ProxyConfig":
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, "r") as f:
                    data = json.load(f)
                    # Automatically set mock mode if no api key exists in env or config
                    api_key = data.get("openai_api_key") or os.environ.get("OPENAI_API_KEY", "")
                    if not api_key:
                        data["mock_llm_mode"] = True
                    return cls(**data)
            except Exception as e:
                print(f"Error loading configuration: {e}. Using defaults.")
        
        # Default behavior: if no API key is found, force mock mode to true
        api_key = os.environ.get("OPENAI_API_KEY", "")
        mock_mode = True if not api_key else False
        return cls(openai_api_key=api_key, mock_llm_mode=mock_mode)

    def save(self):
        try:
            with open(CONFIG_FILE, "w") as f:
                json.dump(self.model_dump(), f, indent=4)
        except Exception as e:
            print(f"Error saving configuration: {e}")

# Global configuration instance
active_config = ProxyConfig.load()
