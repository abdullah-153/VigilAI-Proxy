import re
import base64
from typing import Dict, Tuple, List
from app.config import active_config

# Regex patterns for PII scanner
EMAIL_REGEX = re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b')
SSN_REGEX = re.compile(r'\b\d{3}-\d{2}-\d{4}\b')
PHONE_REGEX = re.compile(r'\b(?:\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b')
IP_REGEX = re.compile(
    r'\b(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\b|'  # IPv4
    r'\b(?:[0-9a-fA-F]{1,4}:){7,7}[0-9a-fA-F]{1,4}\b'  # IPv6
)
# General Credit Card regex pattern
CC_REGEX = re.compile(r'\b(?:\d[ -]*?){13,16}\b')

# Prominent prompt injection attack keywords and patterns
JAILBREAK_PATTERNS = [
    r"ignore (?:all )?(?:previous )?(?:rules|instructions|directives|guidelines)",
    r"bypass (?:security|filters|restrictions)",
    r"system override",
    r"you are now (?:unrestricted|free|dan)",
    r"dan mode",
    r"do anything now",
    r"ignore the restrictions above",
    r"roleplay as",
    r"hypothetically speaking",
    r"write an exploit",
    r"how to hack",
    r"jailbreak",
    r"acting as an evil AI",
    r"ignore everything before",
    r"as a simulated terminal",
    r"developer mode active"
]

# Toxicity keyword subsets
TOXIC_KEYWORDS = {
    "hate speech", "slurs", "kill yourself", "die", "bomb", "exploding",
    "retard", "faggot", "nigger", "cunt", "motherfucker", "bastard", "bitch",
    "exploit children", "make a weapon", "synthesize meth", "illegal drugs"
}

def verify_luhn(card_number: str) -> bool:
    """Verifies credit card using Luhn algorithm to prevent false positives."""
    # Strip spaces and dashes
    digits = [int(c) for c in card_number if c.isdigit()]
    if len(digits) < 13 or len(digits) > 19:
        return False
    odd_digits = digits[-1::-2]
    even_digits = digits[-2::-2]
    total_sum = sum(odd_digits)
    for digit in even_digits:
        doubled = digit * 2
        total_sum += doubled if doubled < 10 else doubled - 9
    return total_sum % 10 == 0

def detect_and_handle_pii(text: str) -> Tuple[str, List[str], bool]:
    """
    Scans text for configured PII entities.
    Returns: (processed_text, detected_types, should_block)
    """
    detected_types = []
    processed_text = text
    should_block = False
    
    if not active_config.enable_pii_detection:
        return text, [], False

    # 1. Scan Emails
    if active_config.scan_email:
        emails = EMAIL_REGEX.findall(processed_text)
        if emails:
            detected_types.append("Email Address")
            if active_config.pii_action == "redact":
                processed_text = EMAIL_REGEX.sub("[REDACTED_EMAIL]", processed_text)
            else:
                should_block = True

    # 2. Scan SSNs
    if active_config.scan_ssn:
        ssns = SSN_REGEX.findall(processed_text)
        if ssns:
            detected_types.append("Social Security Number (SSN)")
            if active_config.pii_action == "redact":
                processed_text = SSN_REGEX.sub("[REDACTED_SSN]", processed_text)
            else:
                should_block = True

    # 3. Scan Phones
    if active_config.scan_phone:
        phones = PHONE_REGEX.findall(processed_text)
        if phones:
            detected_types.append("Phone Number")
            if active_config.pii_action == "redact":
                processed_text = PHONE_REGEX.sub("[REDACTED_PHONE]", processed_text)
            else:
                should_block = True

    # 4. Scan IPs
    if active_config.scan_ip:
        ips = IP_REGEX.findall(processed_text)
        if ips:
            detected_types.append("IP Address")
            if active_config.pii_action == "redact":
                processed_text = IP_REGEX.sub("[REDACTED_IP]", processed_text)
            else:
                should_block = True

    # 5. Scan Credit Cards (with Luhn check verification)
    if active_config.scan_credit_card:
        candidates = CC_REGEX.findall(processed_text)
        validated_cc_found = False
        for cand in candidates:
            clean_cand = re.sub(r'[\s-]', '', cand)
            if verify_luhn(clean_cand):
                validated_cc_found = True
                if active_config.pii_action == "redact":
                    # Escape special regex chars if any, replace specific sequence
                    esc_cand = re.escape(cand)
                    processed_text = re.sub(esc_cand, "[REDACTED_CREDIT_CARD]", processed_text)
        if validated_cc_found:
            detected_types.append("Credit Card Number")
            if active_config.pii_action == "block":
                should_block = True

    return processed_text, detected_types, should_block

def scan_base64_payloads(text: str) -> List[str]:
    """Helper to detect base64 strings and decode them to check for prompt injection."""
    decoded_payloads = []
    # Match strings that look like base64 blocks (longer than 12 chars, multiples of 4, standard characters)
    b64_pattern = re.compile(r'\b[A-Za-z0-9+/]{12,}=*\b')
    candidates = b64_pattern.findall(text)
    
    for cand in candidates:
        try:
            decoded = base64.b64decode(cand).decode("utf-8", errors="ignore")
            # If the decoded string looks like plain English readable text
            if len(decoded) > 8 and any(word in decoded.lower() for word in ["system", "ignore", "instructions", "bypass"]):
                decoded_payloads.append(decoded)
        except Exception:
            continue
    return decoded_payloads

def evaluate_prompt_injection(text: str) -> Tuple[float, List[str], bool]:
    """
    Evaluates prompt injection vulnerability risk score.
    Returns: (score, reasons, should_block)
    """
    if not active_config.enable_prompt_injection:
        return 0.0, [], False

    reasons = []
    score = 0.0
    text_lower = text.lower()
    
    # 1. Match Heuristic Regex Patterns
    for pattern in JAILBREAK_PATTERNS:
        match = re.search(pattern, text_lower)
        if match:
            score += 0.65
            reasons.append(f"Matched adversarial pattern: '{pattern}'")

    # 2. Check decoded Base64 content
    decoded_texts = scan_base64_payloads(text)
    for decoded in decoded_texts:
        score += 0.4
        reasons.append("Base64 encoded adversarial instruction payload detected.")
        # Re-run pattern scan on decoded payload
        for pattern in JAILBREAK_PATTERNS:
            if re.search(pattern, decoded.lower()):
                score += 0.2
                reasons.append(f"Decoded Base64 matched pattern: '{pattern}'")

    # 3. Heuristic checks for instruction overrides (e.g. CAPS ratio, key override phrases)
    if "system" in text_lower and "instructions" in text_lower:
        score += 0.15
        reasons.append("Instruction reference keywords detected.")
    
    # Cap score at 1.0
    score = min(score, 1.0)
    
    # Sensitivity threshold check
    # active_config.injection_sensitivity sets sensitivity. Higher sensitivity = lower threshold to block.
    # Sensitivity: 0.1 (block on > 0.9 score), 0.5 (block on > 0.5 score), 0.9 (block on > 0.1 score)
    threshold = max(0.05, 1.0 - active_config.injection_sensitivity)
    should_block = score >= threshold if score > 0 else False
    
    return score, reasons, should_block

def evaluate_toxicity(text: str) -> Tuple[float, List[str], bool]:
    """
    Evaluates toxicity score in LLM response output.
    Returns: (score, reasons, should_block)
    """
    if not active_config.enable_toxicity_filter:
        return 0.0, [], False

    reasons = []
    score = 0.0
    text_lower = text.lower()
    
    matched_words = []
    for word in TOXIC_KEYWORDS:
        if word in text_lower:
            matched_words.append(word)
            
    if matched_words:
        # Increase score proportionally to matched phrases
        score = min(1.0, 0.25 * len(matched_words) + 0.3)
        reasons.append(f"Toxic keywords detected: {', '.join(matched_words)}")
        
    # Heuristics: excessive capitalized shouting matches (potential toxicity)
    words = text.split()
    if len(words) > 10:
        caps_words = [w for w in words if w.isupper() and len(w) > 1]
        caps_ratio = len(caps_words) / len(words)
        if caps_ratio > 0.4:
            score += 0.2
            reasons.append(f"Excessive upper-case shouting detected ({int(caps_ratio*100)}% words).")

    score = min(score, 1.0)
    
    # Sensitivity threshold check
    # active_config.toxicity_threshold determines blocking limit (direct threshold)
    should_block = score >= active_config.toxicity_threshold if score > 0 else False
    
    return score, reasons, should_block

def evaluate_hallucination(prompt: str, response: str) -> Tuple[bool, List[str]]:
    """
    Simple self-consistency & refusal check.
    Returns: (is_hallucinating, reasons)
    """
    if not active_config.enable_hallucination_guard:
        return False, []
        
    reasons = []
    is_hallucinating = False
    
    # Heuristic 1: Loop Repetitions (LLM repeating same sentence or words in circles)
    # Check if a single phrase of 4 words repeats consecutively 3+ times
    words = response.lower().split()
    if len(words) > 12:
        for idx in range(len(words) - 8):
            phrase = words[idx:idx+4]
            # check if next blocks match
            if words[idx+4:idx+8] == phrase and words[idx+8:idx+12] == phrase:
                is_hallucinating = True
                reasons.append("Infinite repetition loop sequence detected (hallucination).")
                break
                
    # Heuristic 2: Direct prompt instruction leaking (LLM echoes the system constraints instead of replying)
    if "you must not leak" in response.lower() or "here is the secret key" in response.lower() and "secret key" not in prompt.lower():
        is_hallucinating = True
        reasons.append("Internal security constraint context leaked in response.")

    return is_hallucinating, reasons
