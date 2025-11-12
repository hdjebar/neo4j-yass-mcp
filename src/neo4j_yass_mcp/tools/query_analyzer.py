"""
Query Plan Analyzer - Neo4j query performance analysis and optimization recommendations.

This module provides comprehensive query performance analysis by leveraging Neo4j's
EXPLAIN and PROFILE capabilities to identify bottlenecks and suggest optimizations.

Features:
- Query execution plan analysis (EXPLAIN/PROFILE)
- Performance bottleneck detection
- Optimization recommendation engine
- Cost estimation and severity scoring
- Multiple output formats (text, JSON)
"""

import json
import logging
from typing import Any

from neo4j_yass_mcp.tools.bottleneck_detector import BottleneckDetector
from neo4j_yass_mcp.tools.cost_estimator import QueryCostEstimator
from neo4j_yass_mcp.tools.recommendation_engine import RecommendationEngine

logger = logging.getLogger(__name__)


class QueryPlanAnalyzer:
    """
    Analyzes Neo4j query execution plans and provides optimization recommendations.

    This class integrates with SecureNeo4jGraph to provide safe query analysis
    while leveraging Neo4j's built-in query planning capabilities.
    """

    def __init__(self, graph: Any):
        """
        Initialize the query plan analyzer.

        Args:
            graph: SecureNeo4jGraph instance for safe query execution
        """
        self.graph = graph
        self.bottleneck_detector = BottleneckDetector()
        self.recommendation_engine = RecommendationEngine()
        self.cost_estimator = QueryCostEstimator()

        logger.info("QueryPlanAnalyzer initialized with comprehensive analysis capabilities")

    async def analyze_query(
        self,
        query: str,
        mode: str = "profile",
        include_recommendations: bool = True,
        include_cost_estimate: bool = True,
    ) -> dict[str, Any]:
        """
        Analyze a Cypher query and provide performance insights.

        Args:
            query: The Cypher query to analyze
            mode: Analysis mode - "explain" for plan only, "profile" for plan + stats
            include_recommendations: Whether to include optimization recommendations
            include_cost_estimate: Whether to include cost estimation

        Returns:
            Dictionary containing analysis results, bottlenecks, and recommendations

        Raises:
            ValueError: If query is invalid or analysis fails
        """
        logger.info(f"Starting query analysis in {mode} mode: {query[:100]}...")

        try:
            # Step 1: Get execution plan
            if mode.lower() == "explain":
                plan_result = await self._execute_explain(query)
            elif mode.lower() == "profile":
                plan_result = await self._execute_profile(query)
            else:
                raise ValueError(f"Invalid analysis mode: {mode}. Use 'explain' or 'profile'")

            # Step 2: Parse and normalize plan
            parsed_plan = self._parse_execution_plan(plan_result)

            # Step 3: Detect bottlenecks
            bottlenecks = []
            if include_recommendations:
                bottlenecks = await self.bottleneck_detector.detect_bottlenecks(parsed_plan, query)

            # Step 4: Generate recommendations
            recommendations = []
            if include_recommendations:
                recommendations = self.recommendation_engine.generate_recommendations(
                    query, parsed_plan, bottlenecks
                )

            # Step 5: Estimate costs
            cost_estimate = None
            if include_cost_estimate:
                cost_estimate = self.cost_estimator.estimate_cost(query, parsed_plan)

            # Step 6: Compile results
            analysis_result = {
                "query": query,
                "mode": mode,
                "execution_plan": parsed_plan,
                "bottlenecks": bottlenecks,
                "recommendations": recommendations,
                "cost_estimate": cost_estimate,
                "analysis_summary": self._generate_summary(
                    bottlenecks, recommendations, cost_estimate
                ),
                "success": True,
            }

            logger.info(
                f"Query analysis completed successfully. Found {len(bottlenecks)} bottlenecks, {len(recommendations)} recommendations"
            )
            return analysis_result

        except Exception as e:
            logger.error(f"Query analysis failed: {str(e)}", exc_info=True)
            raise ValueError(f"Query analysis failed: {str(e)}") from e

    async def _execute_explain(self, query: str) -> dict[str, Any]:
        """Execute EXPLAIN to get execution plan without running the query."""
        explain_query = f"EXPLAIN {query}"
        logger.debug("Executing EXPLAIN for query analysis")

        try:
            # Use the secure graph to execute the explain query
            result = await self._execute_cypher_safe(explain_query)
            return {
                "type": "explain",
                "plan": result,
                "statistics": None,  # EXPLAIN doesn't provide runtime stats
            }
        except Exception as e:
            logger.error(f"EXPLAIN execution failed: {str(e)}")
            raise ValueError(f"Failed to execute EXPLAIN: {str(e)}") from e

    async def _execute_profile(self, query: str) -> dict[str, Any]:
        """Execute PROFILE to get execution plan with runtime statistics."""
        profile_query = f"PROFILE {query}"
        logger.debug("Executing PROFILE for query analysis")

        try:
            # Use the secure graph to execute the profile query
            result = await self._execute_cypher_safe(profile_query)

            # Extract statistics from PROFILE output
            statistics = self._extract_profile_statistics(result)

            return {"type": "profile", "plan": result, "statistics": statistics}
        except Exception as e:
            logger.error(f"PROFILE execution failed: {str(e)}")
            raise ValueError(f"Failed to execute PROFILE: {str(e)}") from e

    async def _execute_cypher_safe(
        self, query: str, parameters: dict | None = None
    ) -> list[dict[str, Any]]:
        """
        Safely execute a Cypher query using the async secure graph.

        Args:
            query: Cypher query to execute
            parameters: Optional query parameters

        Returns:
            Query results
        """
        # Phase 4: Native async query execution (graph.query is now async)
        # ✅ NATIVE ASYNC - NO sync wrapper!
        result = await self.graph.query(query, params=parameters or {})
        # Cast to expected return type - graph.query should return list[dict[str, Any]]
        from typing import cast

        return cast(list[dict[str, Any]], result)

    def _parse_execution_plan(self, plan_result: dict[str, Any]) -> dict[str, Any]:
        """
        Parse and normalize the execution plan from Neo4j.

        Args:
            plan_result: Raw result from EXPLAIN/PROFILE

        Returns:
            Normalized execution plan structure
        """
        logger.debug("Parsing execution plan")

        try:
            # Extract plan information from the result
            plan_data = plan_result.get("plan", [])

            parsed_plan = {
                "type": plan_result.get("type", "unknown"),  # Preserve type from original result
                "operators": [],
                "estimated_rows": 0,
                "estimated_cost": 0,
                "planning_time_ms": 0,
                "root_operator": None,
            }

            if plan_data and isinstance(plan_data, list):
                # Parse each operator in the plan
                for operator_data in plan_data:
                    operator = self._parse_operator(operator_data)
                    if operator:
                        parsed_plan["operators"].append(operator)

                # Identify root operator (usually the first one)
                if parsed_plan["operators"]:
                    parsed_plan["root_operator"] = parsed_plan["operators"][0]

            # Extract statistics if available (PROFILE mode)
            if plan_result.get("statistics"):
                stats = plan_result["statistics"]
                # Preserve original statistics structure
                parsed_plan["statistics"] = stats
                # Also add individual fields for easy access
                parsed_plan.update(
                    {
                        "actual_rows": stats.get("rows", 0),
                        "actual_time_ms": stats.get("time", 0),
                        "db_hits": stats.get("db_hits", 0),
                        "memory_usage": stats.get("memory", 0),
                    }
                )

            return parsed_plan

        except Exception as e:
            logger.error(f"Failed to parse execution plan: {str(e)}")
            return {"error": f"Plan parsing failed: {str(e)}", "operators": []}

    def _parse_operator(self, operator_data: Any) -> dict[str, Any] | None:
        """
        Parse a single operator from the execution plan.

        Args:
            operator_data: Raw operator data

        Returns:
            Parsed operator information
        """
        if not operator_data:
            return None

        # Handle different formats that Neo4j might return
        if isinstance(operator_data, dict):
            return {
                "name": operator_data.get("name", "Unknown"),
                "arguments": operator_data.get("args", {}),
                "identifiers": operator_data.get("identifiers", []),
                "estimated_rows": operator_data.get("estimated_rows", 0),
                "estimated_cost": operator_data.get("estimated_cost", 0),
                "children": [],
            }
        elif isinstance(operator_data, str):
            return {
                "name": operator_data,
                "arguments": {},
                "identifiers": [],
                "estimated_rows": 0,
                "estimated_cost": 0,
                "children": [],
            }

        return None

    def _extract_profile_statistics(self, result: list[dict[str, Any]]) -> dict[str, Any]:
        """
        Extract runtime statistics from PROFILE results.

        Args:
            result: PROFILE query results

        Returns:
            Extracted statistics
        """
        statistics: dict[str, float] = {"rows": 0.0, "time_ms": 0.0, "db_hits": 0.0, "memory": 0.0}

        try:
            # Look for statistics in the result data
            if result and isinstance(result, list):
                for record in result:
                    if isinstance(record, dict):
                        # Extract common statistics fields
                        if "rows" in record:
                            statistics["rows"] += int(record["rows"])
                        if "time" in record:
                            statistics["time_ms"] += float(record["time"])
                        if "db_hits" in record:
                            statistics["db_hits"] += int(record["db_hits"])
                        if "memory" in record:
                            statistics["memory"] += int(record["memory"])

            return statistics

        except Exception as e:
            logger.warning(f"Failed to extract profile statistics: {str(e)}")
            return statistics

    def _generate_summary(
        self, bottlenecks: list[dict], recommendations: list[dict], cost_estimate: dict | None
    ) -> dict[str, Any]:
        """
        Generate a human-readable summary of the analysis.

        Args:
            bottlenecks: List of detected bottlenecks
            recommendations: List of recommendations
            cost_estimate: Cost estimation results

        Returns:
            Summary information
        """
        severity_score = 0
        if bottlenecks:
            # Calculate severity based on bottleneck impact
            severity_score = sum(b.get("severity", 0) for b in bottlenecks) / len(bottlenecks)

        summary = {
            "overall_severity": min(10, int(severity_score)),
            "bottleneck_count": len(bottlenecks),
            "recommendation_count": len(recommendations),
            "critical_issues": len([b for b in bottlenecks if b.get("severity", 0) >= 8]),
            "estimated_impact": "high"
            if severity_score >= 7
            else "medium"
            if severity_score >= 4
            else "low",
        }

        if cost_estimate:
            summary["estimated_cost"] = cost_estimate.get("total_cost", "unknown")

        return summary

    def format_analysis_report(
        self, analysis_result: dict[str, Any], format_type: str = "text"
    ) -> str:
        """
        Format the analysis results for display.

        Args:
            analysis_result: Complete analysis results
            format_type: Output format ("text", "json", "markdown")

        Returns:
            Formatted analysis report
        """
        if format_type == "json":
            return json.dumps(analysis_result, indent=2, default=str)

        # Default to text format
        summary = analysis_result.get("analysis_summary", {})
        bottlenecks = analysis_result.get("bottlenecks", [])
        recommendations = analysis_result.get("recommendations", [])

        report = f"""
Query Performance Analysis Report
================================

Query: {analysis_result.get("query", "N/A")}
Mode: {analysis_result.get("mode", "N/A")}
Overall Severity: {summary.get("overall_severity", 0)}/10
Estimated Impact: {summary.get("estimated_impact", "unknown")}

Bottlenecks Detected: {len(bottlenecks)}
Recommendations: {len(recommendations)}

"""

        if bottlenecks:
            report += "Performance Bottlenecks:\n"
            for i, bottleneck in enumerate(bottlenecks, 1):
                report += f"{i}. {bottleneck.get('type', 'Unknown')}: {bottleneck.get('description', 'No description')}\n"
                report += f"   Severity: {bottleneck.get('severity', 0)}/10\n"
                if bottleneck.get("impact"):
                    report += f"   Impact: {bottleneck['impact']}\n"
                report += "\n"

        if recommendations:
            report += "Optimization Recommendations:\n"
            for i, rec in enumerate(recommendations, 1):
                report += f"{i}. {rec.get('title', 'No title')}\n"
                report += f"   {rec.get('description', 'No description')}\n"
                report += f"   Priority: {rec.get('priority', 'unknown')}\n"
                report += "\n"

        return report.strip()
