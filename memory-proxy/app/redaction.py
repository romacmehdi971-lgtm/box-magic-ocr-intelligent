"""
Redaction module for Phase 2 MCP
Systematic redaction of secrets, tokens, emails, sensitive IDs
"""

import re
from typing import Any, Dict, List, Union

# Redaction patterns
PATTERNS = {
    "api_key": (re.compile(r'sk-[A-Za-z0-9]{20,}'), "[REDACTED_API_KEY]"),
    "gcp_key": (re.compile(r'AIza[A-Za-z0-9_-]{35}'), "[REDACTED_GCP_KEY]"),
    "jwt": (re.compile(r'eyJ[A-Za-z0-9_-]+\.eyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+'), "[REDACTED_JWT]"),
    "github_token": (re.compile(r'ghp_[A-Za-z0-9]{36,}'), "[REDACTED_GITHUB_TOKEN]"),
    "email": (re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'), "[REDACTED_EMAIL]"),
    "secret_value": (re.compile(r'projects/[0-9]+/secrets/[^/]+/versions/[^/]+/value'), "[REDACTED_SECRET_VALUE]"),
    "bearer_token": (re.compile(r'Bearer\s+[A-Za-z0-9_-]+'), "Bearer [REDACTED_TOKEN]"),
}


def redact_string(text: str) -> str:
    """Redact sensitive patterns in a string"""
    if not isinstance(text, str):
        return text
    
    for pattern_name, (regex, replacement) in PATTERNS.items():
        text = regex.sub(replacement, text)
    
    return text


def redact_dict(data: Dict[str, Any]) -> Dict[str, Any]:
    """Recursively redact sensitive data in a dictionary"""
    if not isinstance(data, dict):
        return data
    
    redacted = {}
    for key, value in data.items():
        # Redact specific keys
        if key.lower() in ['password', 'token', 'api_key', 'secret', 'authorization']:
            redacted[key] = "[REDACTED]"
        elif key.lower() in ['emailaddress', 'email', 'owner', 'user']:
            if isinstance(value, str):
                redacted[key] = redact_string(value)
            elif isinstance(value, dict):
                redacted[key] = redact_dict(value)
            else:
                redacted[key] = "[REDACTED_EMAIL]"
        elif isinstance(value, str):
            redacted[key] = redact_string(value)
        elif isinstance(value, dict):
            redacted[key] = redact_dict(value)
        elif isinstance(value, list):
            redacted[key] = redact_list(value)
        else:
            redacted[key] = value
    
    return redacted


def redact_list(data: List[Any]) -> List[Any]:
    """Recursively redact sensitive data in a list"""
    if not isinstance(data, list):
        return data
    
    redacted = []
    for item in data:
        if isinstance(item, str):
            redacted.append(redact_string(item))
        elif isinstance(item, dict):
            redacted.append(redact_dict(item))
        elif isinstance(item, list):
            redacted.append(redact_list(item))
        else:
            redacted.append(item)
    
    return redacted


def redact_response(data: Union[Dict, List, str]) -> Union[Dict, List, str]:
    """Main redaction function for any response type"""
    if isinstance(data, dict):
        return redact_dict(data)
    elif isinstance(data, list):
        return redact_list(data)
    elif isinstance(data, str):
        return redact_string(data)
    else:
        return data


# Secret Manager specific redaction
def redact_secret_value_always(data: Dict[str, Any]) -> Dict[str, Any]:
    """Force redaction of 'value' field for Secret Manager responses"""
    if not isinstance(data, dict):
        return data
    
    if 'value' in data:
        data['value'] = "[REDACTED]"
    
    # Recursively check nested dicts
    for key, value in data.items():
        if isinstance(value, dict):
            data[key] = redact_secret_value_always(value)
        elif isinstance(value, list):
            data[key] = [redact_secret_value_always(item) if isinstance(item, dict) else item for item in value]
    
    return data
