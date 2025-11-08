"""
Query Complexity Limiter

Analyzes and limits Cypher query complexity to prevent resource exhaustion attacks.

Complexity Metrics:
- Cartesian products (multiple MATCH without relationships)
- Unbounded variable-length patterns (e.g., -[*]->)
- Missing LIMIT clauses on unbounded queries
- Nested subqueries and WITH clauses
- Aggregation complexity

Environment Variables:
- COMPLEXITY_LIMIT_ENABLED: Enable/disable complexity analysis (default: true)
- MAX_QUERY_COMPLEXITY: Maximum allowed complexity score (default: 100)
- MAX_VARIABLE_PATH_LENGTH: Maximum variable path length (default: 10)
- REQUIRE_LIMIT_UNBOUNDED: Require LIMIT on unbounded queries (default: true)
"""

import logging
import re
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class ComplexityScore:
    """Query complexity analysis result."""

    total_score: int
    breakdown: dict[str, int]
    warnings: list[str]
    is_within_limit: bool
    max_allowed: int


class QueryComplexityAnalyzer:
    """Analyzes Cypher query complexity to prevent resource exhaustion."""

    def __init__(
        self,
        max_complexity: int = 100,
        max_variable_path_length: int = 10,
        require_limit_unbounded: bool = True,
    ):
        """
        Initialize complexity analyzer.

        Args:
            max_complexity: Maximum allowed complexity score
            max_variable_path_length: Maximum variable-length path length
            require_limit_unbounded: Require LIMIT on unbounded queries
        """
        self.max_complexity = max_complexity
        self.max_variable_path_length = max_variable_path_length
        self.require_limit_unbounded = require_limit_unbounded

        logger.info(f"Query complexity analyzer initialized (max: {max_complexity})")

    def analyze_query(self, query: str) -> ComplexityScore:
        """
        Analyze query complexity and return detailed score.

        Args:
            query: Cypher query to analyze

        Returns:
            ComplexityScore with total score, breakdown, and warnings
        """
        if not query or not isinstance(query, str):
            return ComplexityScore(
                total_score=0,
                breakdown={},
                warnings=["Invalid query"],
                is_within_limit=False,
                max_allowed=self.max_complexity,
            )

        # Normalize query for analysis
        query_upper = query.upper()
        query_normalized = re.sub(r'\s+', ' ', query).strip()

        breakdown = {}
        warnings = []

        # 1. Count MATCH clauses (base complexity)
        match_count = len(re.findall(r'\bMATCH\b', query_upper))
        breakdown['match_clauses'] = match_count * 5

        # 2. Detect Cartesian products (multiple MATCH without relationships)
        if match_count > 1:
            # Check if MATCH clauses are connected via WHERE or relationships
            cartesian_risk = self._detect_cartesian_product(query_normalized)
            if cartesian_risk:
                breakdown['cartesian_product_risk'] = 50
                warnings.append("Potential Cartesian product detected - multiple MATCH clauses without clear relationships")

        # 3. Variable-length patterns
        variable_patterns = re.findall(r'-\[\*(\d+)?\.\.(\d+)?\]->', query_normalized)
        variable_patterns += re.findall(r'-\[\*(\d+)?\]->', query_normalized)

        if variable_patterns:
            max_length = 0
            for pattern in variable_patterns:
                if isinstance(pattern, tuple):
                    # Pattern like [*1..5] or [*..10]
                    int(pattern[0]) if pattern[0] else 1
                    max_val = int(pattern[1]) if pattern[1] else self.max_variable_path_length
                    max_length = max(max_length, max_val)
                else:
                    # Pattern like [*] (unbounded)
                    max_length = self.max_variable_path_length

            if max_length > self.max_variable_path_length:
                breakdown['excessive_variable_path'] = 30
                warnings.append(f"Variable-length path exceeds limit: {max_length} > {self.max_variable_path_length}")
            else:
                breakdown['variable_length_patterns'] = len(variable_patterns) * 10

        # 4. Unbounded variable-length patterns (no upper limit)
        unbounded_patterns = re.findall(r'-\[\*\]->', query_normalized) + re.findall(r'-\[\*\.\.]->', query_normalized)
        if unbounded_patterns:
            breakdown['unbounded_patterns'] = len(unbounded_patterns) * 25
            warnings.append(f"Found {len(unbounded_patterns)} unbounded variable-length pattern(s) - may traverse entire graph")

        # 5. Check for LIMIT clause on unbounded queries
        has_limit = bool(re.search(r'\bLIMIT\s+\d+', query_upper))
        if self.require_limit_unbounded and not has_limit:
            if match_count > 0 or unbounded_patterns:
                breakdown['missing_limit'] = 20
                warnings.append("Unbounded query without LIMIT clause - may return excessive results")

        # 6. Nested subqueries and WITH clauses
        with_count = len(re.findall(r'\bWITH\b', query_upper))
        if with_count > 0:
            breakdown['with_clauses'] = with_count * 5

        call_subquery_count = len(re.findall(r'\bCALL\s*\{', query_upper))
        if call_subquery_count > 0:
            breakdown['call_subqueries'] = call_subquery_count * 15
            if call_subquery_count > 3:
                warnings.append(f"High subquery nesting: {call_subquery_count} CALL subqueries")

        # 7. Aggregation complexity
        aggregate_functions = re.findall(
            r'\b(COUNT|SUM|AVG|MIN|MAX|COLLECT|PERCENTILE)\s*\(',
            query_upper
        )
        if aggregate_functions:
            breakdown['aggregations'] = len(aggregate_functions) * 3

        # 8. UNION operations
        union_count = len(re.findall(r'\bUNION\b', query_upper))
        if union_count > 0:
            breakdown['union_operations'] = union_count * 10

        # 9. OPTIONAL MATCH (may increase result set)
        optional_match_count = len(re.findall(r'\bOPTIONAL\s+MATCH\b', query_upper))
        if optional_match_count > 0:
            breakdown['optional_matches'] = optional_match_count * 5

        # Calculate total score
        total_score = sum(breakdown.values())

        # Determine if within limit
        is_within_limit = total_score <= self.max_complexity

        if not is_within_limit:
            warnings.insert(0, f"Query complexity {total_score} exceeds limit of {self.max_complexity}")

        return ComplexityScore(
            total_score=total_score,
            breakdown=breakdown,
            warnings=warnings,
            is_within_limit=is_within_limit,
            max_allowed=self.max_complexity,
        )

    def _detect_cartesian_product(self, query: str) -> bool:
        """
        Detect potential Cartesian products in query.

        A Cartesian product occurs when multiple MATCH clauses
        are not properly connected via relationships or WHERE.

        Args:
            query: Normalized query string

        Returns:
            True if Cartesian product risk detected
        """
        # Split query into clauses
        query_upper = query.upper()

        # Count MATCH statements
        matches = re.findall(r'MATCH[^;]*?(?=MATCH|WHERE|WITH|RETURN|$)', query_upper, re.DOTALL)

        if len(matches) <= 1:
            return False

        # Check if MATCH clauses have relationships between them
        # Simple heuristic: Look for shared variables or WHERE clauses
        for i, match_clause in enumerate(matches[:-1]):
            next_clause = matches[i + 1]

            # Extract variable names from patterns
            vars_current = set(re.findall(r'\((\w+):', match_clause))
            vars_next = set(re.findall(r'\((\w+):', next_clause))

            # If no shared variables and no WHERE connecting them
            if not vars_current.intersection(vars_next):
                # Check if there's a WHERE clause between MATCH statements
                between_text = query_upper[query_upper.find(match_clause):query_upper.find(next_clause)]
                if 'WHERE' not in between_text and 'WITH' not in between_text:
                    return True

        return False

    def check_complexity(self, query: str) -> tuple[bool, str | None, ComplexityScore]:
        """
        Check if query complexity is within allowed limits.

        Args:
            query: Cypher query to check

        Returns:
            Tuple of (is_allowed, error_message, complexity_score)
        """
        score = self.analyze_query(query)

        if score.is_within_limit:
            return True, None, score
        else:
            error_msg = f"Query complexity {score.total_score} exceeds limit of {score.max_allowed}"
            if score.warnings:
                error_msg += f". Issues: {'; '.join(score.warnings)}"
            return False, error_msg, score


# Global complexity analyzer instance
_complexity_analyzer: QueryComplexityAnalyzer | None = None


def initialize_complexity_limiter(
    max_complexity: int = 100,
    max_variable_path_length: int = 10,
    require_limit_unbounded: bool = True,
) -> None:
    """
    Initialize global complexity analyzer.

    Args:
        max_complexity: Maximum allowed complexity score
        max_variable_path_length: Maximum variable-length path length
        require_limit_unbounded: Require LIMIT on unbounded queries
    """
    global _complexity_analyzer
    _complexity_analyzer = QueryComplexityAnalyzer(
        max_complexity=max_complexity,
        max_variable_path_length=max_variable_path_length,
        require_limit_unbounded=require_limit_unbounded,
    )
    logger.info("Query complexity limiter initialized")


def get_complexity_analyzer() -> QueryComplexityAnalyzer | None:
    """Get the global complexity analyzer instance."""
    return _complexity_analyzer


def check_query_complexity(query: str) -> tuple[bool, str | None, ComplexityScore | None]:
    """
    Check query complexity using global analyzer.

    Args:
        query: Cypher query to check

    Returns:
        Tuple of (is_allowed, error_message, complexity_score)
    """
    if _complexity_analyzer is None:
        # Analyzer not initialized - allow query
        return True, None, None

    return _complexity_analyzer.check_complexity(query)
