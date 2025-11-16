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
        parameters: dict[str, Any] | None = None,
        mode: str = "explain",
        include_recommendations: bool = True,
        include_cost_estimate: bool = True,
        allow_write_queries: bool = False,
    ) -> dict[str, Any]:
        """
        Analyze a Cypher query and provide performance insights.

        Args:
            query: The Cypher query to analyze
            parameters: Query parameters for parameterized Cypher queries (e.g., {"userId": 123})
            mode: Analysis mode - "explain" (safe, default) or "profile" (executes query)
            include_recommendations: Whether to include optimization recommendations
            include_cost_estimate: Whether to include cost estimation
            allow_write_queries: Whether to allow PROFILE on write queries (default: False)

        Returns:
            Dictionary containing analysis results, bottlenecks, and recommendations

        Raises:
            ValueError: If query is invalid, contains writes in PROFILE mode, or analysis fails
        """
        logger.info(f"Starting query analysis in {mode} mode: {query[:100]}...")

        try:
            # Step 1: Get execution plan
            if mode.lower() == "explain":
                plan_result = await self._execute_explain(query, parameters)
            elif mode.lower() == "profile":
                plan_result = await self._execute_profile(query, parameters, allow_write_queries)
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

    async def _execute_explain(
        self, query: str, parameters: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """
        Execute EXPLAIN to get execution plan without running the query.

        Args:
            query: The Cypher query to explain
            parameters: Query parameters for parameterized queries (default: None)

        Returns:
            Dictionary containing:
            - type: "explain"
            - plan: Neo4j execution plan object
            - records: Always empty list (EXPLAIN queries don't materialize records)
            - statistics: None (EXPLAIN doesn't provide runtime stats)
        """
        explain_query = f"EXPLAIN {query}"
        logger.debug("Executing EXPLAIN for query analysis")

        try:
            # Use query_with_summary to get the actual execution plan from Neo4j
            # fetch_records=False avoids materializing result rows (we only need the plan)
            records, summary = await self.graph.query_with_summary(
                explain_query, params=parameters or {}, fetch_records=False
            )

            # Extract the plan from the summary
            plan = summary.plan if hasattr(summary, "plan") else None

            return {
                "type": "explain",
                "plan": plan,
                "records": records,  # Always [] when fetch_records=False
                "statistics": None,  # EXPLAIN doesn't provide runtime stats
            }
        except Exception as e:
            logger.error(f"EXPLAIN execution failed: {str(e)}")
            raise ValueError(f"Failed to execute EXPLAIN: {str(e)}") from e

    def _is_write_query(self, query: str) -> bool:
        """
        Detect if a query contains write operations.

        Uses regex with word boundaries to catch all whitespace variations
        (spaces, tabs, newlines) and prevent bypass attacks.

        Args:
            query: The Cypher query to check

        Returns:
            True if query contains write operations, False otherwise
        """
        import re

        # Write operation keywords with word boundaries
        # \b ensures we match whole words regardless of surrounding whitespace
        write_patterns = [
            r'\bCREATE\b',
            r'\bMERGE\b',
            r'\bDELETE\b',
            r'\bDETACH\s+DELETE\b',
            r'\bSET\b',
            r'\bREMOVE\b',
            r'\bDROP\b',
        ]

        # Check each pattern with case-insensitive regex
        for pattern in write_patterns:
            if re.search(pattern, query, re.IGNORECASE):
                return True

        return False

    async def _execute_profile(
        self,
        query: str,
        parameters: dict[str, Any] | None = None,
        allow_write_queries: bool = False,
    ) -> dict[str, Any]:
        """
        Execute PROFILE to get execution plan with runtime statistics.

        IMPORTANT: PROFILE executes the query to gather runtime statistics.
        By default, write queries (CREATE/MERGE/DELETE/SET) are blocked unless
        explicitly allowed via allow_write_queries=True.

        Args:
            query: The Cypher query to profile
            parameters: Query parameters for parameterized queries (default: None)
            allow_write_queries: Whether to allow profiling of write queries (default: False)

        Returns:
            Dictionary containing:
            - type: "profile"
            - plan: Neo4j execution plan object with runtime info
            - records: Always empty list (we don't materialize query results, only plan stats)
            - statistics: Runtime statistics (db_hits, time, memory, etc.)

        Raises:
            ValueError: If query is a write query and allow_write_queries=False
        """
        # Safety check: Block write queries unless explicitly allowed
        if not allow_write_queries and self._is_write_query(query):
            logger.warning(
                f"PROFILE blocked: Query contains write operations. "
                f"Use EXPLAIN for safe analysis or set allow_write_queries=True to override."
            )
            raise ValueError(
                "PROFILE mode blocked: Query contains write operations (CREATE/MERGE/DELETE/SET/REMOVE/DROP). "
                "Use EXPLAIN mode for safe analysis, or explicitly allow write queries if intentional."
            )

        profile_query = f"PROFILE {query}"
        logger.debug("Executing PROFILE for query analysis")

        try:
            # Use query_with_summary to get the actual execution plan and statistics from Neo4j
            # fetch_records=False avoids materializing result rows (we only need plan + stats)
            records, summary = await self.graph.query_with_summary(
                profile_query, params=parameters or {}, fetch_records=False
            )

            # Extract the plan from the summary
            plan = summary.plan if hasattr(summary, "plan") else None

            # Extract statistics from the summary
            statistics = self._extract_profile_statistics_from_summary(summary)

            return {
                "type": "profile",
                "plan": plan,
                "records": records,  # Always [] when fetch_records=False
                "statistics": statistics,
            }
        except Exception as e:
            logger.error(f"PROFILE execution failed: {str(e)}")
            raise ValueError(f"Failed to execute PROFILE: {str(e)}") from e

    def _parse_execution_plan(self, plan_result: dict[str, Any]) -> dict[str, Any]:
        """
        Parse and normalize the execution plan from Neo4j.

        Args:
            plan_result: Raw result from EXPLAIN/PROFILE containing the Neo4j plan object

        Returns:
            Normalized execution plan structure
        """
        logger.debug("Parsing execution plan")

        try:
            # Extract the actual Neo4j plan object
            plan_obj = plan_result.get("plan")

            parsed_plan = {
                "type": plan_result.get("type", "unknown"),
                "operators": [],
                "estimated_rows": 0,
                "estimated_cost": 0,
                "planning_time_ms": 0,
                "root_operator": None,
            }

            if plan_obj:
                # Parse the Neo4j plan object recursively
                root_operator = self._parse_neo4j_plan_node(plan_obj)
                if root_operator:
                    parsed_plan["root_operator"] = root_operator
                    # Flatten the plan tree into a list of operators
                    parsed_plan["operators"] = self._flatten_plan_tree(root_operator)

                # Extract plan-level metadata
                if hasattr(plan_obj, "arguments"):
                    args = plan_obj.arguments
                    parsed_plan["estimated_rows"] = args.get("EstimatedRows", 0)
                    parsed_plan["estimated_cost"] = args.get("EstimatedCost", 0)

            # Extract statistics if available (PROFILE mode)
            if plan_result.get("statistics"):
                stats = plan_result["statistics"]
                parsed_plan["statistics"] = stats
                parsed_plan.update(
                    {
                        "actual_rows": stats.get("rows", 0),
                        "actual_time_ms": stats.get("time_ms", 0),
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

    def _parse_neo4j_plan_node(self, plan_node: Any) -> dict[str, Any] | None:
        """
        Parse a Neo4j plan node object into a normalized dictionary.

        Args:
            plan_node: Neo4j plan node object from summary.plan

        Returns:
            Normalized operator information
        """
        if not plan_node:
            return None

        try:
            operator = {
                "name": getattr(plan_node, "operator_type", "Unknown"),
                "arguments": dict(getattr(plan_node, "arguments", {})),
                "identifiers": list(getattr(plan_node, "identifiers", [])),
                "estimated_rows": getattr(plan_node, "arguments", {}).get("EstimatedRows", 0),
                "db_hits": getattr(plan_node, "arguments", {}).get("DbHits", 0),
                "rows": getattr(plan_node, "arguments", {}).get("Rows", 0),
                "children": [],
            }

            # Recursively parse child nodes
            children = getattr(plan_node, "children", [])
            if children:
                for child in children:
                    child_op = self._parse_neo4j_plan_node(child)
                    if child_op:
                        operator["children"].append(child_op)

            return operator

        except Exception as e:
            logger.warning(f"Failed to parse plan node: {str(e)}")
            return None

    def _flatten_plan_tree(self, root: dict[str, Any]) -> list[dict[str, Any]]:
        """
        Flatten a plan tree into a list of operators.

        Args:
            root: Root operator of the plan tree

        Returns:
            List of all operators in the plan
        """
        operators = [root]
        for child in root.get("children", []):
            operators.extend(self._flatten_plan_tree(child))
        return operators

    def _extract_profile_statistics_from_summary(self, summary: Any) -> dict[str, Any]:
        """
        Extract runtime statistics from Neo4j result summary.

        Args:
            summary: Neo4j ResultSummary object from PROFILE query

        Returns:
            Extracted statistics
        """
        statistics: dict[str, float] = {"rows": 0.0, "time_ms": 0.0, "db_hits": 0.0, "memory": 0.0}

        try:
            # Extract counters from the summary
            if hasattr(summary, "counters"):
                counters = summary.counters
                # Note: counters contains update statistics, not query performance stats

            # Extract profile information from the plan
            if hasattr(summary, "plan"):
                plan = summary.plan
                # Recursively collect statistics from the plan tree
                statistics = self._collect_plan_statistics(plan)

            # Extract result metadata
            if hasattr(summary, "result_available_after"):
                statistics["result_available_after_ms"] = summary.result_available_after

            if hasattr(summary, "result_consumed_after"):
                statistics["result_consumed_after_ms"] = summary.result_consumed_after

            return statistics

        except Exception as e:
            logger.warning(f"Failed to extract profile statistics from summary: {str(e)}")
            return statistics

    def _collect_plan_statistics(self, plan_node: Any) -> dict[str, float]:
        """
        Recursively collect statistics from a plan tree.

        Args:
            plan_node: Neo4j plan node object

        Returns:
            Aggregated statistics
        """
        stats: dict[str, float] = {"rows": 0.0, "time_ms": 0.0, "db_hits": 0.0, "memory": 0.0}

        if not plan_node:
            return stats

        try:
            # Extract statistics from this node's arguments
            args = getattr(plan_node, "arguments", {})

            if "Rows" in args:
                stats["rows"] = float(args["Rows"])
            if "DbHits" in args:
                stats["db_hits"] = float(args["DbHits"])
            if "Time" in args:
                stats["time_ms"] = float(args["Time"])
            if "Memory" in args:
                stats["memory"] = float(args["Memory"])

            # Recursively collect from children (accumulate db_hits, max rows)
            children = getattr(plan_node, "children", [])
            for child in children:
                child_stats = self._collect_plan_statistics(child)
                stats["db_hits"] += child_stats["db_hits"]
                stats["time_ms"] = max(stats["time_ms"], child_stats["time_ms"])
                # For memory, we want the peak across the tree
                stats["memory"] = max(stats["memory"], child_stats["memory"])

            return stats

        except Exception as e:
            logger.warning(f"Failed to collect statistics from plan node: {str(e)}")
            return stats

    def _extract_profile_statistics(self, result: list[dict[str, Any]]) -> dict[str, Any]:
        """
        Extract runtime statistics from PROFILE results (legacy method, kept for compatibility).

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
