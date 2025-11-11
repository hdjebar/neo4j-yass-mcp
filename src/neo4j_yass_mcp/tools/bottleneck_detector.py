"""
Bottleneck Detector - Identifies performance bottlenecks in Neo4j query execution plans.

This module analyzes query execution plans to identify common performance issues such as:
- Cartesian products
- Missing indexes
- Expensive operations
- Unbounded patterns
- Inefficient joins
"""

import logging
import re
from typing import Any

logger = logging.getLogger(__name__)


class BottleneckDetector:
    """
    Detects performance bottlenecks in Neo4j query execution plans.

    This class implements various algorithms to identify common performance issues
    by analyzing query patterns, execution plans, and schema information.
    """

    def __init__(self):
        """Initialize the bottleneck detector with detection patterns."""
        self._init_detection_patterns()
        logger.info("BottleneckDetector initialized with comprehensive detection patterns")

    def _init_detection_patterns(self):
        """Initialize detection patterns and rules."""
        # Patterns for expensive operations
        self.expensive_patterns = {
            "unbounded_varlength": [
                r"\[\*\]",  # [*] - completely unbounded
                r"\[\*\d+\.\.\d+\]",  # [*1..1000] - large bounds
                r"\[\*\.\.\d+\]",  # [*..5] - upper bound only
            ],
            "cartesian_product": [
                r"MATCH\s+\([^)]*\)\s*,\s*\([^)]*\)",  # Multiple MATCH patterns without relationships
                r"WITH\s+\*",  # WITH * can cause cartesian products
            ],
            "expensive_procedures": [
                r"apoc\.path\.",  # APOC path procedures
                r"apoc\.algo\.",  # APOC algorithms
                r"algo\.",  # Graph algorithms
            ],
        }

        # Severity scores for different bottleneck types (1-10)
        self.severity_scores = {
            "cartesian_product": 9,
            "missing_index": 8,
            "unbounded_varlength": 7,
            "expensive_procedure": 6,
            "inefficient_pattern": 5,
            "missing_limit": 4,
            "redundant_operation": 3,
        }

    async def detect_bottlenecks(
        self,
        execution_plan: dict[str, Any],
        query: str,
        schema_info: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        """
        Detect performance bottlenecks in query execution plan and query text.

        Args:
            execution_plan: Parsed execution plan from Neo4j
            query: Original Cypher query
            schema_info: Optional schema information for context

        Returns:
            List of detected bottlenecks with details and severity scores
        """
        logger.debug(f"Detecting bottlenecks for query: {query[:100]}...")

        bottlenecks = []

        # 1. Detect query pattern bottlenecks
        pattern_bottlenecks = self._detect_pattern_bottlenecks(query)
        bottlenecks.extend(pattern_bottlenecks)

        # 2. Detect execution plan bottlenecks
        if execution_plan and execution_plan.get("operators"):
            plan_bottlenecks = self._detect_plan_bottlenecks(execution_plan, schema_info)
            bottlenecks.extend(plan_bottlenecks)

        # 3. Detect schema-related bottlenecks
        if schema_info:
            schema_bottlenecks = self._detect_schema_bottlenecks(query, schema_info)
            bottlenecks.extend(schema_bottlenecks)

        # 4. Remove duplicates and sort by severity
        unique_bottlenecks = self._deduplicate_bottlenecks(bottlenecks)
        unique_bottlenecks.sort(key=lambda x: x.get("severity", 0), reverse=True)

        logger.info(f"Detected {len(unique_bottlenecks)} bottlenecks")
        return unique_bottlenecks

    def _detect_pattern_bottlenecks(self, query: str) -> list[dict[str, Any]]:
        """Detect bottlenecks by analyzing query patterns."""
        bottlenecks = []
        query_upper = query.upper()

        # Check for Cartesian products
        cartesian_bottlenecks = self._detect_cartesian_products(query_upper)
        bottlenecks.extend(cartesian_bottlenecks)

        # Check for unbounded variable-length patterns
        varlength_bottlenecks = self._detect_unbounded_varlength_patterns(query)
        bottlenecks.extend(varlength_bottlenecks)

        # Check for missing LIMIT clauses on potentially expensive queries
        limit_bottlenecks = self._detect_missing_limit_clauses(query_upper)
        bottlenecks.extend(limit_bottlenecks)

        # Check for expensive procedures
        procedure_bottlenecks = self._detect_expensive_procedures(query)
        bottlenecks.extend(procedure_bottlenecks)

        # Check for inefficient patterns
        inefficient_bottlenecks = self._detect_inefficient_patterns(query_upper)
        bottlenecks.extend(inefficient_bottlenecks)

        return bottlenecks

    def _detect_cartesian_products(self, query: str) -> list[dict[str, Any]]:
        """Detect potential Cartesian products in the query."""
        bottlenecks = []

        # Pattern 1: Multiple MATCH clauses without relationships
        match_pattern = r"\bMATCH\s+\([^)]*\)(?:\s*,\s*\([^)]*\))*"
        matches = re.findall(match_pattern, query, re.IGNORECASE)

        for match in matches:
            # Count the number of patterns in this MATCH
            pattern_count = len(re.findall(r"\([^)]*\)", match))
            if pattern_count > 2:  # More than 2 patterns is suspicious
                bottlenecks.append(
                    {
                        "type": "cartesian_product",
                        "description": f"Potential Cartesian product: {pattern_count} patterns in single MATCH",
                        "severity": self.severity_scores.get("cartesian_product", 9),
                        "impact": "High - can cause exponential row growth",
                        "location": match.strip(),
                        "suggestion": "Consider adding relationship constraints or breaking into separate queries",
                    }
                )

        # Pattern 2: WITH * usage
        with_star_pattern = r"\bWITH\s+\*\b"
        if re.search(with_star_pattern, query):
            bottlenecks.append(
                {
                    "type": "cartesian_product",
                    "description": "WITH * can cause Cartesian products if previous operations generated many rows",
                    "severity": self.severity_scores.get("cartesian_product", 9),
                    "impact": "Medium to High - depends on data volume",
                    "location": "WITH * clause",
                    "suggestion": "Use explicit column selection instead of WITH *",
                }
            )

        return bottlenecks

    def _detect_unbounded_varlength_patterns(self, query: str) -> list[dict[str, Any]]:
        """Detect unbounded or large variable-length patterns."""
        bottlenecks = []

        # Pattern 1: Completely unbounded [*]
        unbounded_pattern = r"\[\s*\*\s*\]"
        if re.search(unbounded_pattern, query):
            bottlenecks.append(
                {
                    "type": "unbounded_varlength",
                    "description": "Completely unbounded variable-length pattern [*] can explore entire graph",
                    "severity": self.severity_scores.get("unbounded_varlength", 7),
                    "impact": "Very High - can cause out-of-memory errors",
                    "location": "[*] pattern",
                    "suggestion": "Add reasonable bounds like [*1..4] or use shortestPath()",
                }
            )

        # Pattern 2: Large bounds like [*1..1000]
        large_bounds_pattern = r"\[\s*\*\s*(\d+)\s*\.\.\s*(\d+)\s*\]"
        matches = re.findall(large_bounds_pattern, query)

        for min_bound, max_bound in matches:
            max_val = int(max_bound)
            if max_val > 10:  # Large bounds are suspicious
                severity = min(10, 5 + (max_val // 10))  # Scale severity with bound size
                bottlenecks.append(
                    {
                        "type": "unbounded_varlength",
                        "description": f"Large variable-length bounds [*{min_bound}..{max_bound}]",
                        "severity": severity,
                        "impact": f"High - can explore up to {max_val} hops",
                        "location": f"[*{min_bound}..{max_bound}]",
                        "suggestion": "Consider smaller bounds or use shortestPath() for long paths",
                    }
                )

        return bottlenecks

    def _detect_missing_limit_clauses(self, query: str) -> list[dict[str, Any]]:
        """Detect queries that might benefit from LIMIT clauses."""
        bottlenecks = []

        # Check for RETURN statements without LIMIT
        return_pattern = r"\bRETURN\b(?!.*\bLIMIT\b)"

        # Only flag if it's a potentially expensive query
        expensive_indicators = ["MATCH", "OPTIONAL MATCH", "COLLECT", "COUNT", "DISTINCT"]

        if re.search(return_pattern, query, re.IGNORECASE):
            has_expensive_indicator = any(
                re.search(rf"\b{indicator}\b", query, re.IGNORECASE)
                for indicator in expensive_indicators
            )

            if has_expensive_indicator:
                bottlenecks.append(
                    {
                        "type": "missing_limit",
                        "description": "Query with RETURN but no LIMIT clause on potentially expensive operation",
                        "severity": self.severity_scores.get("missing_limit", 4),
                        "impact": "Medium - can return large result sets",
                        "location": "RETURN clause",
                        "suggestion": "Add LIMIT clause to control result set size",
                    }
                )

        return bottlenecks

    def _detect_expensive_procedures(self, query: str) -> list[dict[str, Any]]:
        """Detect usage of expensive procedures."""
        bottlenecks = []

        expensive_procedures = [
            (r"apoc\.path\.", "APOC path procedures can be expensive on large graphs"),
            (r"apoc\.algo\.", "APOC algorithms can be computationally intensive"),
            (r"algo\.", "Graph algorithms can be expensive"),
            (r"apoc\.periodic\.", "Periodic procedures for batch operations"),
        ]

        for pattern, description in expensive_procedures:
            if re.search(pattern, query, re.IGNORECASE):
                bottlenecks.append(
                    {
                        "type": "expensive_procedure",
                        "description": description,
                        "severity": self.severity_scores.get("expensive_procedure", 6),
                        "impact": "Variable - depends on data size and procedure",
                        "location": re.findall(pattern, query, re.IGNORECASE)[0],
                        "suggestion": "Consider data size and add limits if appropriate",
                    }
                )

        return bottlenecks

    def _detect_inefficient_patterns(self, query: str) -> list[dict[str, Any]]:
        """Detect inefficient query patterns."""
        bottlenecks = []

        # Pattern 1: Multiple OPTIONAL MATCH when one would suffice
        optional_count = len(re.findall(r"\bOPTIONAL\s+MATCH\b", query, re.IGNORECASE))
        if optional_count > 3:
            bottlenecks.append(
                {
                    "type": "inefficient_pattern",
                    "description": f"Many OPTIONAL MATCH clauses ({optional_count}) - consider pattern comprehension",
                    "severity": self.severity_scores.get("inefficient_pattern", 5),
                    "impact": "Medium - can be slower than alternatives",
                    "location": f"{optional_count} OPTIONAL MATCH clauses",
                    "suggestion": "Consider using pattern comprehension or COLLECT for multiple optional matches",
                }
            )

        # Pattern 2: Redundant property access
        property_pattern = r"\(\w+\)\.(\w+).*\(\w+\)\.\1"
        if re.search(property_pattern, query):
            bottlenecks.append(
                {
                    "type": "redundant_operation",
                    "description": "Redundant property access detected",
                    "severity": self.severity_scores.get("redundant_operation", 3),
                    "impact": "Low - minor performance impact",
                    "location": "Property access pattern",
                    "suggestion": "Consider using WITH to store property values",
                }
            )

        return bottlenecks

    def _detect_plan_bottlenecks(
        self, execution_plan: dict[str, Any], schema_info: dict[str, Any] | None
    ) -> list[dict[str, Any]]:
        """Detect bottlenecks by analyzing execution plan operators."""
        bottlenecks = []
        operators = execution_plan.get("operators", [])

        for operator in operators:
            operator_name = operator.get("name", "").lower()

            # Check for Cartesian product operators
            if "cartesianproduct" in operator_name:
                estimated_rows = operator.get("estimated_rows", 0)
                bottlenecks.append(
                    {
                        "type": "cartesian_product",
                        "description": f"Cartesian product detected in execution plan",
                        "severity": self.severity_scores.get("cartesian_product", 9),
                        "impact": f"Very High - estimated {estimated_rows} row combinations",
                        "location": operator.get("name", "Unknown operator"),
                        "suggestion": "Add relationship constraints or filter conditions to reduce cross-product",
                    }
                )

            # Check for expensive operators
            if "scan" in operator_name and "index" not in operator_name:
                # NodeByLabelScan or similar without index
                estimated_rows = operator.get("estimated_rows", 0)
                if estimated_rows > 1000:  # Large estimated row count
                    bottlenecks.append(
                        {
                            "type": "missing_index",
                            "description": f"{operator.get('name')} on large estimated dataset ({estimated_rows} rows)",
                            "severity": self.severity_scores.get("missing_index", 8),
                            "impact": f"High - full scan of ~{estimated_rows} nodes",
                            "location": operator.get("name", "Unknown operator"),
                            "suggestion": "Consider creating an index on the scanned property",
                        }
                    )

            # Check for join operations that might be expensive
            if "join" in operator_name:
                estimated_cost = operator.get("estimated_cost", 0)
                if estimated_cost > 10000:  # High estimated cost
                    bottlenecks.append(
                        {
                            "type": "expensive_operation",
                            "description": f"Expensive join operation: {operator.get('name')}",
                            "severity": 6,
                            "impact": f"High estimated cost: {estimated_cost}",
                            "location": operator.get("name", "Unknown operator"),
                            "suggestion": "Review join conditions and consider query restructuring",
                        }
                    )

        return bottlenecks

    def _detect_schema_bottlenecks(
        self, query: str, schema_info: dict[str, Any]
    ) -> list[dict[str, Any]]:
        """Detect bottlenecks based on schema information."""
        bottlenecks = []

        # Extract node labels and relationship types from query
        node_labels = re.findall(r":(\w+)", query)
        # rel_types = re.findall(r"\[:?(\w+)\]", query)  # Not currently used

        # Check if queried labels exist in schema
        schema_labels = set(schema_info.get("node_labels", []))
        for label in node_labels:
            if label not in schema_labels:
                bottlenecks.append(
                    {
                        "type": "schema_mismatch",
                        "description": f"Node label '{label}' not found in schema",
                        "severity": 5,
                        "impact": "Medium - may indicate typo or missing data",
                        "location": f"Label '{label}'",
                        "suggestion": "Verify label name or check if schema is up to date",
                    }
                )

        return bottlenecks

    def _deduplicate_bottlenecks(self, bottlenecks: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Remove duplicate bottlenecks based on type and location."""
        seen = set()
        unique_bottlenecks = []

        for bottleneck in bottlenecks:
            key = (bottleneck.get("type"), bottleneck.get("location", ""))
            if key not in seen:
                seen.add(key)
                unique_bottlenecks.append(bottleneck)

        return unique_bottlenecks
