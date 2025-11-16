"""
Security Configuration Module

This module centralizes security-related configurations, such as blocklists,
allowlists, and other security parameters.

DRY Approach:
- Uses zxcvbn library for comprehensive password strength estimation
- Fallback to manual list if library not available
"""

import logging

try:
    from zxcvbn import zxcvbn

    ZXCVBN_AVAILABLE = True
except ImportError:  # pragma: no cover
    ZXCVBN_AVAILABLE = False  # pragma: no cover

# Fallback list of known weak or default passwords (used if zxcvbn not available)
# This list should be updated periodically.
WEAK_PASSWORDS = [
    "password",
    "password123",
    "123456",
    "12345678",
    "qwerty",
    "neo4j",
    "admin",
    "test",
    "secret",
    "root",
    "CHANGE_ME",
    "CHANGE_ME_STRONG_PASSWORD",
    "changeme",
]


def is_password_weak(
    password: str, user_inputs: list[str] | None = None
) -> tuple[bool, str | None]:
    """
    Check if a password is weak using zxcvbn or fallback to manual list.

    Args:
        password: The password to check
        user_inputs: Optional list of user-specific strings (username, email, etc.)
                     that zxcvbn should consider as weak if password contains them

    Returns:
        Tuple of (is_weak, reason)
        - is_weak: True if password is weak, False if strong
        - reason: Description of why password is weak, None if strong

    Examples:
        >>> is_password_weak("password123")
        (True, "Password is too common and easily guessable (score: 0/4)")

        >>> is_password_weak("X9$mKp2#Qw!zR", ["john", "smith"])
        (False, None)
    """
    if not password:
        return True, "Password cannot be empty"

    # Use zxcvbn for comprehensive password strength estimation (DRY approach)
    if ZXCVBN_AVAILABLE:
        try:
            # Analyze password strength
            result = zxcvbn(password, user_inputs=user_inputs or [])

            # zxcvbn returns a score from 0 (worst) to 4 (best)
            # Consider score < 3 as weak
            if result["score"] < 3:
                feedback = result.get("feedback", {})
                warning = feedback.get("warning", "")
                suggestions = feedback.get("suggestions", [])

                reason_parts = [f"Password strength score: {result['score']}/4"]
                if warning:
                    reason_parts.append(warning)
                if suggestions:
                    reason_parts.append("Suggestions: " + "; ".join(suggestions))

                return True, " - ".join(reason_parts)

            # Password is strong
            return False, None

        except Exception as e:
            # If zxcvbn fails, fall back to manual check
            logging.warning(f"zxcvbn password check failed: {e}")

    # Fallback: Manual check against known weak passwords
    if password.lower() in [p.lower() for p in WEAK_PASSWORDS]:
        return True, "Password is in the list of commonly used weak passwords"

    # Basic manual checks if zxcvbn not available
    if len(password) < 8:
        return True, "Password must be at least 8 characters long"

    return False, None
