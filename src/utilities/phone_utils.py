# ==================== src/utilities/phone_utils.py ====================
"""Phone number utilities."""

import re


class PhoneUtils:
    """Utility class for phone number operations."""
    
    @staticmethod
    def normalize_phone(phone: str) -> str:
        """Normalize phone number to standard format."""
        if not phone:
            return ""
        
        # Remove all non-digit characters
        digits = re.sub(r'\D', '', phone)
        
        # Handle US numbers
        if len(digits) == 10:
            return f"+1{digits}"
        elif len(digits) == 11 and digits.startswith('1'):
            return f"+{digits}"
        
        return f"+{digits}" if digits else ""
    
    @staticmethod
    def format_phone_display(phone: str) -> str:
        """Format phone number for display."""
        normalized = PhoneUtils.normalize_phone(phone)
        
        if normalized.startswith('+1') and len(normalized) == 12:
            # US number format: +1 (XXX) XXX-XXXX
            digits = normalized[2:]
            return f"+1 ({digits[:3]}) {digits[3:6]}-{digits[6:]}"
        
        return normalized
    
    @staticmethod
    def is_valid_phone(phone: str) -> bool:
        """Check if phone number is valid."""
        normalized = PhoneUtils.normalize_phone(phone)
        return len(normalized) >= 10