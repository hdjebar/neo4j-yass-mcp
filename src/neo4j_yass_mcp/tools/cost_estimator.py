"""
Query Cost Estimator - Estimates resource usage and execution costs for Neo4j queries.

This module provides cost estimation for query execution based on execution plans,
query complexity, and historical performance data. It helps users understand the
potential resource requirements before executing expensive queries.
"""

import logging
import re
from typing import Any

logger = logging.getLogger(__name__)


class QueryCostEstimator:
    """
    Estimates query execution costs based on execution plans and query patterns.

    This estimator uses heuristics and plan analysis to predict:
    - CPU usage
    - Memory requirements
    - I/O operations
    - Execution time
    - Overall cost score
    """

    def __init__(self):
        """Initialize the cost estimator with baseline metrics."""
        self._init_cost_factors()
        logger.info("QueryCostEstimator initialized with performance heuristics")

    def _init_cost_factors(self):
        """Initialize cost factors for different operations."""
        # Base cost units (relative scale)
        self.operation_costs = {
            # Node operations
            "NodeByLabelScan": 100,
            "NodeIndexSeek": 10,
            "NodeIndexScan": 50,
            "NodeUniqueIndexSeek": 5,
            # Relationship operations
            "ExpandAll": 80,
            "ExpandInto": 40,
            "VarLengthExpand": 200,
            # Join operations
            "NodeHashJoin": 150,
            "NodeNestedLoopJoin": 300,
            "CartesianProduct": 1000,  # Very expensive
            # Filtering and projection
            "Filter": 20,
            "Projection": 15,
            "Sort": 60,
            "Limit": 5,
            "Skip": 10,
            # Aggregation
            "Aggregation": 70,
            "Distinct": 50,
            "EagerAggregation": 90,
            # Other operations
            "Apply": 120,
            "SemiApply": 100,
            "AntiSemiApply": 100,
            "LetSemiApply": 110,
            "LetAntiSemiApply": 110,
        }

        # Pattern complexity multipliers
        self.pattern_multipliers = {
            "unbounded_varlength": 10.0,  # [*] patterns
            "large_varlength": 5.0,  # [*1..100] patterns
            "multiple_optional": 3.0,  # Multiple OPTIONAL MATCH
            "complex_aggregation": 2.5,  # Complex aggregation functions
            "subquery": 2.0,  # Nested subqueries
            "procedure_call": 4.0,  # Procedure calls
        }

        # Resource scaling factors
        self.resource_factors = {"cpu_factor": 1.0, "memory_factor": 1.0, "io_factor": 1.0}

    def estimate_cost(
        self,
        query: str,
        execution_plan: dict[str, Any] | None = None,
        estimated_rows: int | None = None,
    ) -> dict[str, Any]:
        """
        Estimate the cost of executing a query.

        Args:
            query: The Cypher query
            execution_plan: Optional execution plan for detailed analysis
            estimated_rows: Optional estimated row count

        Returns:
            Cost estimation with breakdown by resource type
        """
        logger.debug(f"Estimating cost for query: {query[:100]}...")

        try:
            # Base cost from query complexity
            base_cost = self._calculate_base_cost(query)

            # Pattern-based cost adjustments
            pattern_multiplier = self._calculate_pattern_multiplier(query)

            # Plan-based cost adjustments (if available)
            plan_cost = 0
            plan_multipliers = {}
            if execution_plan:
                plan_cost = self._calculate_plan_cost(execution_plan)
                plan_multipliers = self._extract_plan_multipliers(execution_plan)

            # Row count estimation
            row_estimate = estimated_rows or self._estimate_row_count(query, execution_plan)

            # Calculate final costs
            total_cost = (base_cost + plan_cost) * pattern_multiplier * row_estimate / 100

            # Resource breakdown
            resource_costs = self._calculate_resource_costs(total_cost, plan_multipliers)

            # Risk assessment
            risk_assessment = self._assess_risk(query, total_cost, resource_costs)

            cost_estimate = {
                "total_cost": int(total_cost),
                "cost_score": self._calculate_cost_score(total_cost),
                "confidence": self._calculate_confidence(execution_plan),
                "resource_breakdown": resource_costs,
                "estimated_rows": row_estimate,
                "risk_level": risk_assessment["risk_level"],
                "risk_factors": risk_assessment["risk_factors"],
                "execution_time_estimate_ms": self._estimate_execution_time(
                    total_cost, row_estimate
                ),
                "memory_estimate_mb": self._estimate_memory_usage(total_cost, row_estimate),
                "factors": {
                    "base_cost": base_cost,
                    "pattern_multiplier": pattern_multiplier,
                    "plan_cost": plan_cost,
                    "row_multiplier": row_estimate / 100,
                },
            }

            logger.info(
                f"Cost estimation completed: total_cost={total_cost}, risk={risk_assessment['risk_level']}"
            )
            return cost_estimate

        except Exception as e:
            logger.error(f"Cost estimation failed: {str(e)}", exc_info=True)
            return {
                "total_cost": 1000,  # Default high cost
                "cost_score": 8,
                "confidence": "low",
                "error": f"Cost estimation failed: {str(e)}",
            }

    def _calculate_base_cost(self, query: str) -> float:
        """Calculate base cost from query complexity."""
        query_upper = query.upper()

        # Count different query components
        match_count = len(re.findall(r"\bMATCH\b", query_upper))
        optional_match_count = len(re.findall(r"\bOPTIONAL\s+MATCH\b", query_upper))
        where_count = len(re.findall(r"\bWHERE\b", query_upper))
        return_count = len(re.findall(r"\bRETURN\b", query_upper))
        with_count = len(re.findall(r"\bWITH\b", query_upper))
        create_count = len(re.findall(r"\bCREATE\b", query_upper))
        merge_count = len(re.findall(r"\bMERGE\b", query_upper))
        delete_count = len(re.findall(r"\bDELETE\b", query_upper))

        # Calculate base cost
        base_cost = (
            match_count * 50
            + optional_match_count * 80
            + where_count * 20
            + return_count * 10
            + with_count * 30
            + create_count * 100
            + merge_count * 150
            + delete_count * 80
        )

        # Add complexity for long queries
        query_length_factor = len(query) / 1000  # Cost increases with query length
        base_cost *= 1 + query_length_factor * 0.1

        return base_cost

    def _calculate_pattern_multiplier(self, query: str) -> float:
        """Calculate cost multiplier based on query patterns."""
        multiplier = 1.0

        # Check for unbounded patterns
        if re.search(r"\[\s*\*\s*\]", query):
            multiplier *= self.pattern_multipliers["unbounded_varlength"]

        # Check for large bounded patterns
        if re.search(r"\[\s*\*\s*\d+\s*\.\.\s*\d{2,}\s*\]", query):
            multiplier *= self.pattern_multipliers["large_varlength"]

        # Check for multiple OPTIONAL MATCH
        optional_count = len(re.findall(r"\bOPTIONAL\s+MATCH\b", query, re.IGNORECASE))
        if optional_count > 2:
            multiplier *= self.pattern_multipliers["multiple_optional"]

        # Check for complex aggregation
        if re.search(r"\bCOLLECT\s*\(|\bCOUNT\s*\(|\bSUM\s*\(|\bAVG\s*\(", query, re.IGNORECASE):
            multiplier *= self.pattern_multipliers["complex_aggregation"]

        # Check for subqueries
        if re.search(r"\bCALL\s*\{", query, re.IGNORECASE):
            multiplier *= self.pattern_multipliers["subquery"]

        # Check for procedure calls
        if re.search(r"\bCALL\s+\w+\.\w+", query, re.IGNORECASE):
            multiplier *= self.pattern_multipliers["procedure_call"]

        return multiplier

    def _calculate_plan_cost(self, execution_plan: dict[str, Any]) -> float:
        """Calculate cost from execution plan operators."""
        plan_cost = 0
        operators = execution_plan.get("operators", [])

        for operator in operators:
            operator_name = operator.get("name", "")
            base_operator_cost = self.operation_costs.get(operator_name, 50)  # Default cost

            # Adjust cost based on estimated rows
            estimated_rows = operator.get("estimated_rows", 1)
            row_factor = max(1, estimated_rows / 100)  # Scale with estimated rows

            operator_cost = base_operator_cost * row_factor
            plan_cost += operator_cost

        return plan_cost

    def _extract_plan_multipliers(self, execution_plan: dict[str, Any]) -> dict[str, float]:
        """Extract additional multipliers from execution plan."""
        multipliers = {}
        operators = execution_plan.get("operators", [])

        # Check for expensive operators
        expensive_ops = [
            op
            for op in operators
            if op.get("name", "") in ["CartesianProduct", "NodeNestedLoopJoin"]
        ]
        if expensive_ops:
            multipliers["expensive_operations"] = 2.0

        # Check for many operators (complex plan)
        if len(operators) > 10:
            multipliers["complex_plan"] = 1.5

        return multipliers

    def _estimate_row_count(self, query: str, execution_plan: dict[str, Any] | None) -> int:
        """Estimate the number of rows the query will process."""
        # Default estimate
        estimated_rows = 100

        # Use execution plan estimates if available
        if execution_plan:
            operators = execution_plan.get("operators", [])
            if operators:
                # Use the largest estimated row count from operators
                max_rows = max(op.get("estimated_rows", 100) for op in operators)
                estimated_rows = max(estimated_rows, max_rows)

        # Adjust based on query patterns
        if re.search(r"\bCOUNT\s*\(", query, re.IGNORECASE):
            estimated_rows = 1  # COUNT returns single row
        elif re.search(r"\bEXISTS\s*\(", query, re.IGNORECASE):
            estimated_rows = 1  # EXISTS returns boolean
        elif re.search(r"\bLIMIT\s+(\d+)", query, re.IGNORECASE):
            # Use the LIMIT value if specified
            limit_match = re.search(r"\bLIMIT\s+(\d+)", query, re.IGNORECASE)
            if limit_match:
                limit_value = int(limit_match.group(1))
                estimated_rows = min(estimated_rows, limit_value)

        return estimated_rows

    def _calculate_resource_costs(
        self, total_cost: float, multipliers: dict[str, float]
    ) -> dict[str, float]:
        """Calculate cost breakdown by resource type."""
        # Apply multipliers
        cpu_multiplier = multipliers.get("expensive_operations", 1.0) * multipliers.get(
            "complex_plan", 1.0
        )
        memory_multiplier = multipliers.get("expensive_operations", 1.0)
        io_multiplier = multipliers.get("complex_plan", 1.0)

        return {
            "cpu_cost": int(total_cost * 0.4 * cpu_multiplier),
            "memory_cost": int(total_cost * 0.3 * memory_multiplier),
            "io_cost": int(total_cost * 0.3 * io_multiplier),
        }

    def _assess_risk(
        self, query: str, total_cost: float, resource_costs: dict[str, float]
    ) -> dict[str, Any]:
        """Assess the risk level of the query."""
        risk_factors = []
        risk_level = "low"

        # Check for high-cost operations
        if total_cost > 10000:
            risk_factors.append("Very high estimated cost")
            risk_level = "high"
        elif total_cost > 5000:
            risk_factors.append("High estimated cost")
            risk_level = "medium"

        # Check for memory-intensive patterns
        if resource_costs["memory_cost"] > total_cost * 0.4:
            risk_factors.append("Memory-intensive operations detected")
            if risk_level == "low":
                risk_level = "medium"

        # Check for dangerous patterns
        dangerous_patterns = [
            r"\[\s*\*\s*\]",  # Unbounded patterns
            r"\bDELETE\b.*\bDETACH\b",  # Detach delete
            r"\bFOREACH\b.*\bCREATE\b",  # Foreach creates
        ]

        for pattern in dangerous_patterns:
            if re.search(pattern, query, re.IGNORECASE):
                risk_factors.append("Potentially dangerous operation pattern")
                risk_level = "high"
                break

        return {"risk_level": risk_level, "risk_factors": risk_factors}

    def _calculate_cost_score(self, total_cost: float) -> int:
        """Convert total cost to a 1-10 score."""
        if total_cost < 100:
            return 1
        elif total_cost < 500:
            return 2
        elif total_cost < 1000:
            return 3
        elif total_cost < 2000:
            return 4
        elif total_cost < 5000:
            return 5
        elif total_cost < 8000:
            return 6
        elif total_cost < 12000:
            return 7
        elif total_cost < 20000:
            return 8
        elif total_cost < 30000:
            return 9
        else:
            return 10

    def _calculate_confidence(self, execution_plan: dict[str, Any] | None) -> str:
        """Calculate confidence level of the cost estimate."""
        if not execution_plan:
            return "low"

        operators = execution_plan.get("operators", [])
        if len(operators) > 5:
            return "high"
        elif len(operators) > 2:
            return "medium"
        else:
            return "low"

    def _estimate_execution_time(self, total_cost: float, estimated_rows: int) -> int:
        """Estimate execution time in milliseconds."""
        # Base time calculation
        base_time = total_cost * 0.1  # Rough correlation

        # Row count impact
        row_time = estimated_rows * 0.01  # Time per row

        # Combine and add realistic bounds
        estimated_time = base_time + row_time

        # Apply reasonable bounds (1ms to 60 seconds)
        return max(1, min(60000, int(estimated_time)))

    def _estimate_memory_usage(self, total_cost: float, estimated_rows: int) -> int:
        """Estimate memory usage in MB."""
        # Base memory calculation
        base_memory = total_cost * 0.01  # Base memory cost

        # Row count impact (roughly 1KB per row)
        row_memory = estimated_rows * 0.001

        # Combine and add realistic bounds
        estimated_memory = base_memory + row_memory

        # Apply reasonable bounds (1MB to 1GB)
        return max(1, min(1000, int(estimated_memory)))
