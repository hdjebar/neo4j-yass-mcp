"""
Security Configuration Module

This module centralizes security-related configurations, such as blocklists,
allowlists, and other security parameters.
"""

# List of known weak or default passwords to check against.
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
