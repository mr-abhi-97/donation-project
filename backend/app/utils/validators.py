import re
from typing import Tuple


def normalize_indian_phone(phone_input: str) -> str:
    """
    Normalizes an Indian phone number to E.164 international standard (+91XXXXXXXXXX):
    1. Strips all non-digit characters (+, -, spaces, parentheses).
    2. Strips leading country code '91' if 12 digits.
    3. Strips leading trunk prefix '0' if 11 digits.
    4. Validates that the remaining 10 digits begin with valid Indian mobile telecom prefix [6-9].
    5. Returns formatted '+91XXXXXXXXXX' string.
    Raises ValueError if invalid.
    """
    if not phone_input or not isinstance(phone_input, str):
        raise ValueError("Phone number is required.")

    # Strip all non-digit characters
    cleaned = re.sub(r"\D", "", phone_input.strip())

    # Handle leading country code '91'
    if len(cleaned) == 12 and cleaned.startswith("91"):
        cleaned = cleaned[2:]
    # Handle leading trunk code '0'
    elif len(cleaned) == 11 and cleaned.startswith("0"):
        cleaned = cleaned[1:]

    # Must now be exactly 10 digits
    if len(cleaned) != 10:
        raise ValueError(f"Invalid phone number length ({len(cleaned)} digits). Expected 10-digit mobile number.")

    # Must start with 6, 7, 8, or 9
    if not re.match(r"^[6-9]\d{9}$", cleaned):
        raise ValueError("Invalid Indian mobile number. Mobile numbers must start with 6, 7, 8, or 9.")

    return f"+91{cleaned}"


def is_valid_indian_phone(phone_input: str) -> bool:
    """Returns True if the phone number can be normalized to valid Indian format."""
    try:
        normalize_indian_phone(phone_input)
        return True
    except (ValueError, TypeError):
        return False


def validate_pan_format(pan_input: str) -> str:
    """
    Validates Indian Income Tax Permanent Account Number (PAN):
    Format: 5 uppercase letters, 4 digits, 1 uppercase letter (e.g. ABCDE1234F).
    Fourth character represents status:
    P - Individual, C - Company, H - HUF, A - AOP, B - BOI, T - Trust, etc.
    """
    if not pan_input:
        raise ValueError("PAN number is required.")
    cleaned = pan_input.strip().upper()
    if not re.match(r"^[A-Z]{5}[0-9]{4}[A-Z]{1}$", cleaned):
        raise ValueError("Invalid PAN format. Must be 5 uppercase letters, 4 digits, 1 letter (e.g. ABCDE1234F).")
    return cleaned
