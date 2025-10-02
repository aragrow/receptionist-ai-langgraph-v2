# ==================== src/utilities/pii_masking.py ====================
"""
PII Masking Utility for Logging and Data Protection

This module provides functions to detect and mask Personally Identifiable Information (PII)
in logs, database entries, and other text to ensure GDPR/CCPA compliance.
"""

import re
from typing import Any, Dict, List, Optional, Union
from enum import Enum


class PIIType(Enum):
    """Types of PII that can be detected and masked."""
    EMAIL = "email"
    PHONE = "phone"
    SSN = "ssn"
    CREDIT_CARD = "credit_card"
    ADDRESS = "address"
    NAME = "name"
    IP_ADDRESS = "ip_address"
    DATE_OF_BIRTH = "date_of_birth"


# Regex patterns for PII detection
PII_PATTERNS = {
    PIIType.EMAIL: [
        r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
    ],
    PIIType.PHONE: [
        r'\b(?:\+?1[-.]?)?\(?([0-9]{3})\)?[-.]?([0-9]{3})[-.]?([0-9]{4})\b',
        r'\b\d{3}[-.\s]?\d{3}[-.\s]?\d{4}\b',
        r'\(\d{3}\)\s*\d{3}[-.\s]?\d{4}'
    ],
    PIIType.SSN: [
        r'\b\d{3}-\d{2}-\d{4}\b',
        r'\b\d{9}\b'
    ],
    PIIType.CREDIT_CARD: [
        r'\b(?:4[0-9]{12}(?:[0-9]{3})?|5[1-5][0-9]{14}|3[47][0-9]{13}|3(?:0[0-5]|[68][0-9])[0-9]{11}|6(?:011|5[0-9]{2})[0-9]{12}|(?:2131|1800|35\d{3})\d{11})\b'
    ],
    PIIType.ADDRESS: [
        r'\b\d{1,5}\s+[\w\s]+(?:street|st|avenue|ave|road|rd|highway|hwy|square|sq|trail|trl|drive|dr|court|ct|parkway|pkwy|circle|cir|boulevard|blvd)\b',
        r'\b\d{5}(?:-\d{4})?\b'  # ZIP codes
    ],
    PIIType.IP_ADDRESS: [
        r'\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b',
        r'\b(?:[A-F0-9]{1,4}:){7}[A-F0-9]{1,4}\b'  # IPv6
    ],
    PIIType.DATE_OF_BIRTH: [
        r'\b(?:0[1-9]|1[0-2])[/-](?:0[1-9]|[12][0-9]|3[01])[/-](?:19|20)\d{2}\b',
        r'\b(?:19|20)\d{2}[/-](?:0[1-9]|1[0-2])[/-](?:0[1-9]|[12][0-9]|3[01])\b'
    ]
}


def mask_pii(
    text: str,
    pii_types: Optional[List[PIIType]] = None,
    mask_char: str = "*",
    preserve_length: bool = True,
    preserve_format: bool = False
) -> str:
    """
    Mask PII in the given text.
    
    Args:
        text: The text to mask
        pii_types: List of PII types to mask. If None, masks all types.
        mask_char: Character to use for masking
        preserve_length: If True, masks with same length as original
        preserve_format: If True, preserves format (e.g., xxx-xx-xxxx for SSN)
    
    Returns:
        Text with PII masked
    
    Examples:
        >>> mask_pii("Contact me at john@example.com")
        'Contact me at ********************'
        
        >>> mask_pii("Call (555) 123-4567", preserve_format=True)
        'Call (***) ***-****'
    """
    if not text:
        return text
    
    masked_text = text
    types_to_mask = pii_types or list(PIIType)
    
    for pii_type in types_to_mask:
        if pii_type not in PII_PATTERNS:
            continue
            
        for pattern in PII_PATTERNS[pii_type]:
            matches = list(re.finditer(pattern, masked_text, re.IGNORECASE))
            
            # Process matches in reverse order to maintain string indices
            for match in reversed(matches):
                original = match.group(0)
                
                if preserve_format and pii_type in [PIIType.PHONE, PIIType.SSN]:
                    # Preserve format structure (keep dashes, parentheses, etc.)
                    masked = ''.join(
                        char if not char.isdigit() else mask_char 
                        for char in original
                    )
                elif preserve_length:
                    masked = mask_char * len(original)
                else:
                    masked = f"[{pii_type.value.upper()}_REDACTED]"
                
                masked_text = masked_text[:match.start()] + masked + masked_text[match.end():]
    
    return masked_text


def mask_dict(
    data: Dict[str, Any],
    sensitive_keys: Optional[List[str]] = None,
    pii_types: Optional[List[PIIType]] = None,
    recursive: bool = True
) -> Dict[str, Any]:
    """
    Mask PII in dictionary values.
    
    Args:
        data: Dictionary to mask
        sensitive_keys: List of key names that should be masked entirely
        pii_types: List of PII types to detect and mask in string values
        recursive: If True, recursively mask nested dictionaries
    
    Returns:
        Dictionary with PII masked
    
    Examples:
        >>> mask_dict({"email": "test@example.com", "age": 30})
        {'email': '****************', 'age': 30}
    """
    default_sensitive_keys = [
        'password', 'ssn', 'social_security', 'credit_card', 
        'card_number', 'cvv', 'pin', 'secret', 'token',
        'api_key', 'private_key'
    ]
    
    keys_to_mask = set(sensitive_keys or []) | set(default_sensitive_keys)
    masked_data = {}
    
    for key, value in data.items():
        # Check if key itself is sensitive
        if any(sensitive in key.lower() for sensitive in keys_to_mask):
            masked_data[key] = "[REDACTED]"
        elif isinstance(value, str):
            # Mask PII in string values
            masked_data[key] = mask_pii(value, pii_types=pii_types)
        elif isinstance(value, dict) and recursive:
            # Recursively mask nested dictionaries
            masked_data[key] = mask_dict(
                value, 
                sensitive_keys=sensitive_keys,
                pii_types=pii_types,
                recursive=recursive
            )
        elif isinstance(value, list) and recursive:
            # Mask list items
            masked_data[key] = [
                mask_dict(item, sensitive_keys, pii_types, recursive) 
                if isinstance(item, dict)
                else mask_pii(item, pii_types) if isinstance(item, str)
                else item
                for item in value
            ]
        else:
            masked_data[key] = value
    
    return masked_data


def detect_pii(text: str, pii_types: Optional[List[PIIType]] = None) -> Dict[PIIType, List[str]]:
    """
    Detect PII in text without masking.
    
    Args:
        text: Text to analyze
        pii_types: List of PII types to detect. If None, detects all types.
    
    Returns:
        Dictionary mapping PII types to list of detected instances
    
    Examples:
        >>> detect_pii("Email: test@example.com, Phone: 555-1234")
        {<PIIType.EMAIL>: ['test@example.com'], <PIIType.PHONE>: ['555-1234']}
    """
    if not text:
        return {}
    
    detected = {}
    types_to_detect = pii_types or list(PIIType)
    
    for pii_type in types_to_detect:
        if pii_type not in PII_PATTERNS:
            continue
            
        matches = []
        for pattern in PII_PATTERNS[pii_type]:
            found = re.findall(pattern, text, re.IGNORECASE)
            matches.extend(found)
        
        if matches:
            detected[pii_type] = list(set(matches))  # Remove duplicates
    
    return detected


def has_pii(text: str, pii_types: Optional[List[PIIType]] = None) -> bool:
    """
    Check if text contains any PII.
    
    Args:
        text: Text to check
        pii_types: List of PII types to check for. If None, checks all types.
    
    Returns:
        True if PII detected, False otherwise
    """
    detected = detect_pii(text, pii_types)
    return len(detected) > 0


def sanitize_for_logging(
    message: Union[str, Dict[str, Any]],
    mask_all_pii: bool = True
) -> Union[str, Dict[str, Any]]:
    """
    Sanitize a log message by masking all PII.
    
    This is the primary function to use before logging any user data.
    
    Args:
        message: Log message (string or dict)
        mask_all_pii: If True, masks all PII types
    
    Returns:
        Sanitized message safe for logging
    
    Examples:
        >>> sanitize_for_logging("User john@example.com requested service")
        'User ******************** requested service'
    """
    if isinstance(message, dict):
        return mask_dict(message, pii_types=list(PIIType) if mask_all_pii else None)
    elif isinstance(message, str):
        return mask_pii(message, pii_types=list(PIIType) if mask_all_pii else None)
    else:
        return message


# Convenience functions for specific PII types
def mask_email(text: str) -> str:
    """Mask only email addresses."""
    return mask_pii(text, pii_types=[PIIType.EMAIL])


def mask_phone(text: str, preserve_format: bool = True) -> str:
    """Mask only phone numbers."""
    return mask_pii(text, pii_types=[PIIType.PHONE], preserve_format=preserve_format)


def mask_credit_card(text: str) -> str:
    """Mask only credit card numbers."""
    return mask_pii(text, pii_types=[PIIType.CREDIT_CARD])


def mask_ssn(text: str, preserve_format: bool = True) -> str:
    """Mask only Social Security Numbers."""
    return mask_pii(text, pii_types=[PIIType.SSN], preserve_format=preserve_format)


if __name__ == "__main__":
    # Example usage
    test_text = """
    Contact Information:
    Email: john.doe@example.com
    Phone: (555) 123-4567
    SSN: 123-45-6789
    Address: 123 Main Street, Minneapolis, MN 55401
    Credit Card: 4532-1234-5678-9010
    """
    
    print("Original Text:")
    print(test_text)
    print("\n" + "="*50 + "\n")
    print("Masked Text:")
    print(mask_pii(test_text))
    print("\n" + "="*50 + "\n")
    print("Detected PII:")
    print(detect_pii(test_text))