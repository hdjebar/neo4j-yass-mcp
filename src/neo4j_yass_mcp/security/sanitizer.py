"""
Query Sanitization Module - SISO Prevention

SISO: "Shit In, Shit Out" - The fundamental security principle.
If you accept malicious/unsanitized input, you'll get:
- Injection attacks (SQL/Cypher/Command injection)
- Data breaches
- System compromise
- Unauthorized access

This module prevents SISO by sanitizing ALL queries BEFORE execution.

Security Features:
- Cypher injection prevention
- Malicious pattern detection
- Parameter validation
- Query complexity limits
- Dangerous operation blocking
- LLM output sanitization
- UTF-8 attack prevention (homographs, zero-width chars, directional overrides)

DRY Approach:
- Uses confusable-homoglyphs for homograph detection
- Uses ftfy for Unicode normalization and UTF-8 cleaning
- Custom logic for Cypher-specific and advanced UTF-8 attacks
"""

import logging
import re
from typing import Any

try:
    from confusable_homoglyphs import confusables

    CONFUSABLES_AVAILABLE = True
except ImportError:
    CONFUSABLES_AVAILABLE = False

try:
    import ftfy

    FTFY_AVAILABLE = True
except ImportError:
    FTFY_AVAILABLE = False


class QuerySanitizer:
    """
    Sanitizes and validates Cypher queries for security.

    Prevents:
    - Cypher injection attacks
    - Command injection
    - Path traversal
    - Excessive resource consumption
    - Malicious operations
    """

    # Dangerous patterns that should be blocked
    DANGEROUS_PATTERNS = [
        # System commands and file operations
        r"(?i)LOAD\s+CSV",  # File loading
        r"(?i)apoc\.load",  # APOC file loading
        r"(?i)apoc\.export",  # APOC export
        r"(?i)apoc\.cypher\.run",  # Dynamic Cypher execution
        r"(?i)apoc\.refactor",  # Schema refactoring
        r"(?i)dbms\.security",  # Security procedures
        r"(?i)dbms\.cluster",  # Cluster operations
        # Potential injection patterns (improved to catch whitespace variations)
        r";\s+(?i:MATCH)",  # Query chaining with any whitespace
        r";\s+(?i:CREATE)",  # Query chaining with any whitespace
        r";\s+(?i:MERGE)",  # Query chaining with any whitespace
        r";\s+(?i:DELETE)",  # Query chaining with any whitespace
        r";\s+(?i:DROP)",  # Query chaining with any whitespace
        r";\s+(?i:CALL)",  # Query chaining with CALL
        # Comment-based injection (fixed for multi-line)
        r"/\*[\s\S]*?\*/",  # Block comments (multi-line aware)
        r"//[^\n]*",  # Line comments (safer pattern)
        # Excessive operations
        r"(?i)FOREACH\s*\([^)]*\s+IN\s+range\s*\(\s*\d+\s*,\s*\d{6,}",  # Large range iterations
        # Additional dangerous patterns
        r"(?i)apoc\.periodic\.iterate",  # Batch operations that can cause DoS
        r"(?i)apoc\.cypher\.parallel",  # Parallel execution abuse
    ]

    # Suspicious but not always dangerous (warnings)
    SUSPICIOUS_PATTERNS = [
        r"(?i)CALL\s+apoc",  # APOC procedures (review needed)
        r"(?i)CALL\s+dbms",  # DBMS procedures (review needed)
        r"(?i)CREATE\s+INDEX",  # Schema changes
        r"(?i)DROP\s+INDEX",  # Schema changes
        r"(?i)CREATE\s+CONSTRAINT",  # Schema changes
        r"(?i)DROP\s+CONSTRAINT",  # Schema changes
    ]

    # Maximum query length
    MAX_QUERY_LENGTH = 10000  # 10KB

    # Maximum parameter value length
    MAX_PARAM_LENGTH = 5000

    # Maximum number of parameters
    MAX_PARAMS = 100

    def __init__(
        self,
        strict_mode: bool = False,
        allow_apoc: bool = False,
        allow_schema_changes: bool = False,
        max_query_length: int | None = None,
        block_non_ascii: bool = False,
    ):
        """
        Initialize query sanitizer.

        Args:
            strict_mode: Enable strict validation (block suspicious patterns)
            allow_apoc: Allow APOC procedures
            allow_schema_changes: Allow schema modification (indexes, constraints)
            max_query_length: Maximum allowed query length
            block_non_ascii: Block non-ASCII characters (UTF-8 attack prevention)
        """
        self.strict_mode = strict_mode
        self.allow_apoc = allow_apoc
        self.allow_schema_changes = allow_schema_changes
        self.max_query_length = max_query_length or self.MAX_QUERY_LENGTH
        self.block_non_ascii = block_non_ascii

    def sanitize_query(self, query: str) -> tuple[bool, str | None, list]:
        """
        Sanitize and validate a Cypher query.

        Args:
            query: The Cypher query to sanitize

        Returns:
            Tuple of (is_safe, error_message, warnings)
            - is_safe: True if query is safe, False if blocked
            - error_message: Error description if blocked, None if safe
            - warnings: List of warning messages
        """
        warnings = []

        # Check 1: Query length
        if len(query) > self.max_query_length:
            return (
                False,
                f"Query exceeds maximum length ({self.max_query_length} characters)",
                warnings,
            )

        # Check 2: Null or empty
        if not query or not query.strip():
            return False, "Empty query not allowed", warnings

        # Check 3: Check for dangerous patterns
        for pattern in self.DANGEROUS_PATTERNS:
            if re.search(pattern, query, re.IGNORECASE | re.MULTILINE):
                return False, f"Blocked: Query contains dangerous pattern: {pattern}", warnings

        # Check 4: Check for suspicious patterns
        for pattern in self.SUSPICIOUS_PATTERNS:
            if re.search(pattern, query, re.IGNORECASE):
                # APOC exceptions
                if "apoc" in pattern.lower() and self.allow_apoc:
                    continue

                # Schema change exceptions
                if ("INDEX" in pattern or "CONSTRAINT" in pattern) and self.allow_schema_changes:
                    continue

                if self.strict_mode:
                    return (
                        False,
                        f"Blocked in strict mode: Query contains suspicious pattern: {pattern}",
                        warnings,
                    )
                else:
                    warnings.append(
                        f"Warning: Query contains pattern that may need review: {pattern}"
                    )

        # Check 5: Balance of parentheses, braces, brackets
        if not self._check_balanced_delimiters(query):
            return False, "Unbalanced parentheses, braces, or brackets detected", warnings

        # Check 6: Detect potential string escape injection
        if self._detect_string_injection(query):
            return False, "Potential string injection detected", warnings

        # Check 7: Detect UTF-8/Unicode attacks
        utf8_safe, utf8_error = self._detect_utf8_attacks(query)
        if not utf8_safe:
            return False, utf8_error, warnings

        # All checks passed
        return True, None, warnings

    def sanitize_parameters(self, parameters: dict[str, Any | None]) -> tuple[bool, str | None]:
        """
        Sanitize and validate query parameters.

        Args:
            parameters: Dictionary of query parameters

        Returns:
            Tuple of (is_safe, error_message)
        """
        if parameters is None:
            return True, None

        # Check parameter count
        if len(parameters) > self.MAX_PARAMS:
            return False, f"Too many parameters ({len(parameters)}), maximum is {self.MAX_PARAMS}"

        # Validate each parameter
        for key, value in parameters.items():
            # Check parameter key
            if not re.match(r"^[a-zA-Z_][a-zA-Z0-9_]*$", key):
                return False, f"Invalid parameter name: {key}"

            # Check parameter value
            if isinstance(value, str):
                if len(value) > self.MAX_PARAM_LENGTH:
                    return False, f"Parameter '{key}' value too long ({len(value)} chars)"

                # Check for injection patterns in string values
                if self._detect_injection_in_param(value):
                    return False, f"Potential injection in parameter '{key}'"

            elif isinstance(value, (list, dict)):
                # Recursively check nested structures
                import json

                try:
                    json_str = json.dumps(value)
                    if len(json_str) > self.MAX_PARAM_LENGTH:
                        return False, f"Parameter '{key}' structure too large"
                except (TypeError, ValueError) as e:
                    return False, f"Parameter '{key}' contains invalid data: {str(e)}"

        return True, None

    def _check_balanced_delimiters(self, query: str) -> bool:
        """Check if parentheses, braces, and brackets are balanced"""
        stack = []
        pairs = {"(": ")", "{": "}", "[": "]"}
        closing = set(pairs.values())

        # Remove string literals to avoid false positives
        query_no_strings = re.sub(r"'[^']*'", "", query)
        query_no_strings = re.sub(r'"[^"]*"', "", query_no_strings)

        for char in query_no_strings:
            if char in pairs:
                stack.append(char)
            elif char in closing:
                if not stack or pairs[stack.pop()] != char:
                    return False

        return len(stack) == 0

    def _detect_string_injection(self, query: str) -> bool:
        """Detect potential string escape injection"""
        # Look for suspicious string escape patterns
        suspicious_escapes = [
            r"\\x[0-9a-fA-F]{2}",  # Hex escapes
            r"\\u[0-9a-fA-F]{4}",  # Unicode escapes
            r"\\[0-7]{3}",  # Octal escapes
            r"'+\s*\+\s*'",  # String concatenation with +
            r'"+\s*\+\s*"',  # String concatenation with +
        ]

        for pattern in suspicious_escapes:
            if re.search(pattern, query):
                return True

        return False

    def _detect_injection_in_param(self, value: str) -> bool:
        """Detect injection attempts in parameter values"""
        # Patterns that should not appear in parameter values
        injection_patterns = [
            r";\s*\w+",  # Statement separator
            r"\bMATCH\b",  # Cypher keywords
            r"\bCREATE\b",
            r"\bMERGE\b",
            r"\bDELETE\b",
            r"\bDROP\b",
            r"\bCALL\b",
            r"\bLOAD\b",
            r"--",  # SQL comment
            r"/\*",  # Block comment start
        ]

        for pattern in injection_patterns:
            if re.search(pattern, value, re.IGNORECASE):
                return True

        return False

    def _detect_utf8_attacks(self, query: str) -> tuple[bool, str | None]:
        """
        Detect UTF-8/Unicode encoding attacks.

        Protects against:
        - Zero-width characters (data hiding/exfiltration)
        - Right-to-left override (visual spoofing)
        - Homograph attacks (lookalike characters)
        - Combining diacritics
        - Mathematical alphanumeric symbols
        - Null bytes
        - Invalid UTF-8 sequences
        - Non-ASCII in suspicious contexts

        DRY Approach:
        - Uses ftfy to normalize and detect problematic Unicode sequences
        - Uses confusable-homoglyphs for comprehensive homograph detection
        - Custom checks for attack patterns not covered by libraries

        Returns:
            Tuple of (is_safe, error_message)
        """
        # Step 1: Use ftfy to normalize and detect UTF-8 issues (DRY approach)
        if FTFY_AVAILABLE:
            try:
                # Normalize the query and check if it changed significantly
                normalized = ftfy.fix_text(query)

                # If ftfy had to fix things, it might indicate an attack
                if normalized != query:
                    # Check what ftfy fixed
                    if (
                        len(normalized) < len(query) * 0.9
                    ):  # >10% shrinkage suggests removed characters
                        return (
                            False,
                            "Blocked: Query contained problematic Unicode sequences removed by normalization",
                        )
            except Exception as e:
                # ftfy failed, continue with manual checks
                logging.warning(f"ftfy normalization failed: {e}")

        # Null bytes (can truncate strings or bypass filters)
        if "\x00" in query:
            return False, "Blocked: Query contains null byte (U+0000)"

        # Zero-width characters (invisible characters for data hiding)
        zero_width_chars = [
            "\u200b",  # Zero-width space
            "\u200c",  # Zero-width non-joiner
            "\u200d",  # Zero-width joiner
            "\ufeff",  # Zero-width no-break space (BOM)
        ]

        for char in zero_width_chars:
            if char in query:
                return False, f"Blocked: Query contains zero-width character (U+{ord(char):04X})"

        # Directional override characters (text direction manipulation)
        directional_chars = [
            "\u202e",  # Right-to-left override
            "\u202d",  # Left-to-right override
            "\u202a",  # Left-to-right embedding
            "\u202b",  # Right-to-left embedding
            "\u202c",  # Pop directional formatting
        ]

        for char in directional_chars:
            if char in query:
                return (
                    False,
                    f"Blocked: Query contains directional override character (U+{ord(char):04X})",
                )

        # Check for combining diacritical marks (U+0300 to U+036F)
        for char in query:
            if "\u0300" <= char <= "\u036f":
                return (
                    False,
                    f"Blocked: Query contains combining diacritical mark (U+{ord(char):04X})",
                )

        # Check for mathematical alphanumeric symbols (U+1D400 to U+1D7FF)
        # These look like normal letters but are different characters
        for char in query:
            if "\U0001d400" <= char <= "\U0001d7ff":
                return (
                    False,
                    f"Blocked: Query contains mathematical alphanumeric symbol (U+{ord(char):04X})",
                )

        # Homograph detection using confusable-homoglyphs library (DRY approach)
        if CONFUSABLES_AVAILABLE:
            try:
                # Check if the query contains dangerous confusable characters
                if confusables.is_dangerous(query):
                    return (
                        False,
                        "Blocked: Query contains dangerous confusable characters (homograph attack)",
                    )

                # Check for mixed scripts (e.g., Latin + Cyrillic)
                if confusables.is_mixed_script(query):
                    # Get more details about the confusables
                    for char in query:
                        if ord(char) > 127:  # Non-ASCII characters
                            try:
                                # Check if this character is confusable with Latin
                                if confusables.is_confusable(char, preferred_aliases=["LATIN"]):
                                    return (
                                        False,
                                        f"Blocked: Character '{char}' (U+{ord(char):04X}) is confusable with Latin characters (homograph attack)",
                                    )
                            except Exception as e:
                                # Character not in confusables database, continue
                                logging.debug(
                                    f"Character U+{ord(char):04X} not in confusables database: {e}"
                                )
            except Exception:
                # If library fails, fall back to manual detection
                homograph_result = self._manual_homograph_detection(query)
                if not homograph_result[0]:
                    return homograph_result
        else:
            # Fallback to manual homograph detection if library not available
            homograph_result = self._manual_homograph_detection(query)
            if not homograph_result[0]:
                return homograph_result

        # Check for non-ASCII if strict mode enabled
        if self.block_non_ascii:
            # Allow common exceptions (quotes, etc.) but block everything else
            allowed_non_ascii = set("\u2018\u2019\u201c\u201d")  # Smart quotes

            for char in query:
                if ord(char) > 127 and char not in allowed_non_ascii:
                    return (
                        False,
                        f"Blocked: Non-ASCII character '{char}' (U+{ord(char):04X}) not allowed in strict mode",
                    )

        # Validate UTF-8 encoding (detect invalid sequences)
        try:
            query.encode("utf-8", errors="strict")
        except UnicodeEncodeError as e:
            return False, f"Blocked: Invalid UTF-8 encoding at position {e.start}"

        return True, None

    def _manual_homograph_detection(self, query: str) -> tuple[bool, str | None]:
        """
        Manual fallback homograph detection when confusable-homoglyphs is not available.

        Checks a limited set of common Cyrillic/Greek homoglyphs.
        """
        # Common homographs used in attacks (fallback when library not available)
        homograph_chars = {
            "\u0430": "a",  # Cyrillic 'a'
            "\u0435": "e",  # Cyrillic 'e'
            "\u043e": "o",  # Cyrillic 'o'
            "\u0440": "p",  # Cyrillic 'p'
            "\u0441": "c",  # Cyrillic 'c'
            "\u0445": "x",  # Cyrillic 'x'
            "\u0455": "s",  # Cyrillic 's'
            "\u0456": "i",  # Cyrillic 'i'
            "\u03bf": "o",  # Greek omicron
            "\u03c1": "p",  # Greek rho
        }

        for char, lookalike in homograph_chars.items():
            if char in query:
                return (
                    False,
                    f"Blocked: Query contains homograph character '{char}' (looks like '{lookalike}', U+{ord(char):04X})",
                )

        return True, None


# Global sanitizer instance
_sanitizer: QuerySanitizer | None = None


def initialize_sanitizer(
    strict_mode: bool = False,
    allow_apoc: bool = False,
    allow_schema_changes: bool = False,
    block_non_ascii: bool = False,
    max_query_length: int = 10000,
) -> QuerySanitizer:
    """
    Initialize global query sanitizer.

    Args:
        strict_mode: Enable strict validation
        allow_apoc: Allow APOC procedures
        allow_schema_changes: Allow schema modifications
        block_non_ascii: Block non-ASCII characters (UTF-8 attack prevention)
        max_query_length: Maximum allowed query length (default: 10000)

    Returns:
        Configured QuerySanitizer instance
    """
    global _sanitizer
    _sanitizer = QuerySanitizer(
        strict_mode=strict_mode,
        allow_apoc=allow_apoc,
        allow_schema_changes=allow_schema_changes,
        block_non_ascii=block_non_ascii,
        max_query_length=max_query_length,
    )
    return _sanitizer


def get_sanitizer() -> QuerySanitizer | None:
    """Get the global sanitizer instance"""
    return _sanitizer


def sanitize_query(
    query: str, parameters: dict[str, Any | None] = None
) -> tuple[bool, str | None, list]:
    """
    Sanitize query and parameters using global sanitizer.

    Args:
        query: Cypher query to sanitize
        parameters: Optional query parameters

    Returns:
        Tuple of (is_safe, error_message, warnings)
    """
    if _sanitizer is None:
        # Auto-initialize with default settings
        initialize_sanitizer()

    # Sanitize query
    is_safe, error, warnings = _sanitizer.sanitize_query(query)
    if not is_safe:
        return False, error, warnings

    # Sanitize parameters
    if parameters:
        params_safe, params_error = _sanitizer.sanitize_parameters(parameters)
        if not params_safe:
            return False, params_error, warnings

    return True, None, warnings
