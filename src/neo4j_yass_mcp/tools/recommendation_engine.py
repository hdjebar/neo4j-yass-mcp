"""
Recommendation Engine - Generates optimization recommendations for Neo4j queries.

This module analyzes detected bottlenecks and generates actionable recommendations
for improving query performance. Recommendations are prioritized by severity and
potential impact.
"""

import logging
from typing import Any

logger = logging.getLogger(__name__)


class RecommendationEngine:
    """
    Generates optimization recommendations based on query analysis and detected bottlenecks.

    This engine uses rule-based logic to generate actionable recommendations
    for improving query performance, with severity scoring and implementation guidance.
    """

    def __init__(self):
        """Initialize the recommendation engine with optimization rules."""
        self._init_optimization_rules()
        logger.info("RecommendationEngine initialized with comprehensive optimization rules")

    def _init_optimization_rules(self):
        """Initialize optimization rules and recommendation templates."""
        self.optimization_rules: dict[str, dict[str, Any]] = {
            # Cartesian Product Rules
            "cartesian_product": {
                "priority": "high",
                "category": "query_structure",
                "templates": [
                    {
                        "condition": lambda b: "patterns in single MATCH"
                        in b.get("description", "")
                        or "many patterns" in b.get("description", ""),
                        "recommendation": {
                            "title": "Break complex MATCH into smaller parts",
                            "description": "Split the MATCH clause into multiple queries or use pattern comprehension",
                            "example": "Instead of: MATCH (a), (b), (c) RETURN a, b, c\\nUse: MATCH (a) WITH a MATCH (b) WITH a, b MATCH (c) RETURN a, b, c",
                            "effort": "medium",
                            "impact": "high",
                        },
                    },
                    {
                        "condition": lambda b: "WITH *" in b.get("location", ""),
                        "recommendation": {
                            "title": "Replace WITH * with explicit columns",
                            "description": "Explicit column selection reduces memory usage and improves performance",
                            "example": "Instead of: WITH * MATCH (n) RETURN n\\nUse: WITH collect(n) as nodes UNWIND nodes as n RETURN n",
                            "effort": "low",
                            "impact": "medium",
                        },
                    },
                ],
            },
            # Index Rules
            "missing_index": {
                "priority": "high",
                "category": "indexing",
                "templates": [
                    {
                        "condition": lambda b: "NodeByLabelScan" in b.get("description", ""),
                        "recommendation": {
                            "title": "Create index on frequently queried property",
                            "description": "Add an index to speed up node lookups by property",
                            "example": "CREATE INDEX index_name FOR (n:Label) ON (n.property)",
                            "effort": "low",
                            "impact": "high",
                            "considerations": [
                                "Index creation takes time and disk space",
                                "Consider composite indexes for multiple properties",
                            ],
                        },
                    },
                    {
                        "condition": lambda b: "estimated_rows" in b.get("description", ""),
                        "recommendation": {
                            "title": "Analyze data distribution before creating index",
                            "description": "Check property selectivity to ensure index will be effective",
                            "example": "MATCH (n:Label) RETURN n.property, count(*) ORDER BY count(*) DESC LIMIT 10",
                            "effort": "low",
                            "impact": "medium",
                            "considerations": [
                                "Indexes work best on selective properties",
                                "Low-selectivity indexes may hurt performance",
                            ],
                        },
                    },
                ],
            },
            # Variable Length Pattern Rules
            "unbounded_varlength": {
                "priority": "high",
                "category": "pattern_optimization",
                "templates": [
                    {
                        "condition": lambda b: "completely unbounded"
                        in b.get("description", "").lower(),
                        "recommendation": {
                            "title": "Add reasonable bounds to variable-length pattern",
                            "description": "Unbounded patterns can explore the entire graph and cause memory issues",
                            "example": "Instead of: (a)-[*]->(b)\\nUse: (a)-[*1..4]->(b) or shortestPath((a)-[*]->(b))",
                            "effort": "low",
                            "impact": "high",
                            "considerations": [
                                "Choose bounds based on your data model",
                                "Consider shortestPath() for finding shortest paths",
                            ],
                        },
                    },
                    {
                        "condition": lambda b: "large bounds" in b.get("description", ""),
                        "recommendation": {
                            "title": "Reduce variable-length pattern bounds",
                            "description": "Large bounds can still be expensive, use smaller ranges",
                            "example": "Instead of: [*1..100]\\nUse: [*1..5] if that meets your requirements",
                            "effort": "low",
                            "impact": "high",
                        },
                    },
                ],
            },
            # Limit Clause Rules
            "missing_limit": {
                "priority": "medium",
                "category": "result_optimization",
                "templates": [
                    {
                        "condition": lambda b: "no LIMIT clause" in b.get("description", ""),
                        "recommendation": {
                            "title": "Add LIMIT clause to control result set size",
                            "description": "LIMIT prevents excessive memory usage and improves response time",
                            "example": "RETURN n LIMIT 100",
                            "effort": "low",
                            "impact": "medium",
                            "considerations": [
                                "Consider pagination for large result sets",
                                "Use SKIP for offset-based pagination",
                            ],
                        },
                    }
                ],
            },
            # Procedure Rules
            "expensive_procedure": {
                "priority": "medium",
                "category": "procedure_optimization",
                "templates": [
                    {
                        "condition": lambda b: "APOC path" in b.get("description", ""),
                        "recommendation": {
                            "title": "Consider alternatives to APOC path procedures",
                            "description": "Native Cypher patterns are often faster than APOC procedures",
                            "example": "Instead of: apoc.path.expand()\\nUse: (a)-[*1..3]->(b) pattern",
                            "effort": "medium",
                            "impact": "medium",
                        },
                    },
                    {
                        "condition": lambda b: "APOC algorithm" in b.get("description", ""),
                        "recommendation": {
                            "title": "Use graph algorithms on appropriately sized subgraphs",
                            "description": "Graph algorithms can be expensive - limit data scope",
                            "example": "MATCH (n:Label {category: 'specific'}) WITH n CALL algo.pagestream() YIELD result RETURN result",
                            "effort": "medium",
                            "impact": "high",
                            "considerations": [
                                "Consider sampling for large graphs",
                                "Use community detection on relevant subgraphs",
                            ],
                        },
                    },
                ],
            },
            # Join Operation Rules
            "expensive_operation": {
                "priority": "medium",
                "category": "operation_optimization",
                "templates": [
                    {
                        "condition": lambda b: "expensive join" in b.get("description", ""),
                        "recommendation": {
                            "title": "Optimize join conditions and consider query restructuring",
                            "description": "Expensive joins can often be optimized with better patterns",
                            "example": "Review join conditions and ensure proper indexing on join properties",
                            "effort": "high",
                            "impact": "medium",
                            "considerations": [
                                "Ensure indexes exist on join properties",
                                "Consider denormalization for frequently joined data",
                            ],
                        },
                    }
                ],
            },
            # Schema Rules
            "schema_mismatch": {
                "priority": "low",
                "category": "schema_validation",
                "templates": [
                    {
                        "condition": lambda b: "not found in schema" in b.get("description", ""),
                        "recommendation": {
                            "title": "Verify schema and update queries accordingly",
                            "description": "Ensure queries match actual schema structure",
                            "example": "Check schema with CALL db.schema.visualization()",
                            "effort": "low",
                            "impact": "low",
                        },
                    }
                ],
            },
        }

    def generate_recommendations(
        self, query: str, execution_plan: dict[str, Any], bottlenecks: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        """
        Generate optimization recommendations based on detected bottlenecks.

        Args:
            query: Original Cypher query
            execution_plan: Parsed execution plan
            bottlenecks: List of detected bottlenecks

        Returns:
            List of recommendations with implementation details
        """
        logger.debug(f"Generating recommendations for {len(bottlenecks)} bottlenecks")

        recommendations = []

        for bottleneck in bottlenecks:
            bottleneck_type = bottleneck.get("type")

            if bottleneck_type in self.optimization_rules:
                rule = self.optimization_rules[bottleneck_type]

                # Find matching template for this bottleneck
                templates = rule["templates"]  # type: list[dict[str, Any]]
                matching_template = self._find_matching_template(bottleneck, templates)

                if matching_template:
                    recommendation = self._build_recommendation(
                        bottleneck, matching_template, rule["priority"], rule["category"]
                    )
                    recommendations.append(recommendation)
                else:
                    # Generate generic recommendation if no template matches
                    generic_rec = self._generate_generic_recommendation(bottleneck, rule)
                    recommendations.append(generic_rec)
            else:
                # Unknown bottleneck type - generate basic recommendation
                basic_rec = self._generate_basic_recommendation(bottleneck)
                recommendations.append(basic_rec)

        # Remove duplicates and sort by priority and impact
        unique_recommendations = self._deduplicate_recommendations(recommendations)
        unique_recommendations.sort(
            key=lambda x: (
                self._priority_to_score(x.get("priority", "medium")),
                self._impact_to_score(x.get("impact", "medium")),
                -len(x.get("considerations", [])),  # More considerations = more detailed
            ),
            reverse=True,
        )

        logger.info(f"Generated {len(unique_recommendations)} unique recommendations")
        return unique_recommendations

    def _find_matching_template(
        self, bottleneck: dict[str, Any], templates: list[dict[str, Any]]
    ) -> dict[str, Any] | None:
        """Find the first template that matches the bottleneck."""
        for template in templates:
            condition_func = template.get("condition")
            if condition_func and condition_func(bottleneck):
                return template.get("recommendation")
        return None

    def _build_recommendation(
        self, bottleneck: dict[str, Any], template: dict[str, Any], priority: str, category: str
    ) -> dict[str, Any]:
        """Build a complete recommendation from template and bottleneck context."""

        # Calculate severity-based priority adjustment
        base_severity = bottleneck.get("severity", 5)
        adjusted_priority = self._adjust_priority_by_severity(priority, base_severity)

        recommendation = {
            "id": f"{category}_{bottleneck.get('type', 'unknown')}_{hash(str(bottleneck))}",
            "title": template.get("title", "Optimization needed"),
            "description": template.get(
                "description", "Consider optimizing this part of the query"
            ),
            "priority": adjusted_priority,
            "category": category,
            "severity": base_severity,
            "effort": template.get("effort", "medium"),
            "impact": template.get("impact", "medium"),
            "example": template.get("example", ""),
            "bottleneck_type": bottleneck.get("type"),
            "bottleneck_location": bottleneck.get("location", ""),
            "reasoning": f"Detected {bottleneck.get('type')} with severity {base_severity}/10",
            "considerations": template.get("considerations", []),
        }

        # Add implementation guidance
        recommendation["implementation"] = self._generate_implementation_guidance(recommendation)

        return recommendation

    def _generate_generic_recommendation(
        self, bottleneck: dict[str, Any], rule: dict[str, Any]
    ) -> dict[str, Any]:
        """Generate a generic recommendation when no specific template matches."""
        return {
            "id": f"generic_{bottleneck.get('type', 'unknown')}_{hash(str(bottleneck))}",
            "title": f"Address {bottleneck.get('type', 'performance issue')}",
            "description": f"Consider optimizing the identified {bottleneck.get('type')} issue",
            "priority": rule.get("priority", "medium"),
            "category": rule.get("category", "general"),
            "severity": bottleneck.get("severity", 5),
            "effort": "medium",
            "impact": "medium",
            "example": "Review the query structure and consider alternatives",
            "bottleneck_type": bottleneck.get("type"),
            "bottleneck_location": bottleneck.get("location", ""),
            "reasoning": f"Generic recommendation for {bottleneck.get('type')}",
            "implementation": "Review query patterns and consider optimization techniques",
        }

    def _generate_basic_recommendation(self, bottleneck: dict[str, Any]) -> dict[str, Any]:
        """Generate a basic recommendation for unknown bottleneck types."""
        return {
            "id": f"basic_{bottleneck.get('type', 'unknown')}_{hash(str(bottleneck))}",
            "title": f"Review {bottleneck.get('type', 'performance issue')}",
            "description": bottleneck.get("description", "Performance issue detected"),
            "priority": "medium",
            "category": "general",
            "severity": bottleneck.get("severity", 5),
            "effort": "medium",
            "impact": "unknown",
            "example": "Review query execution plan for optimization opportunities",
            "bottleneck_type": bottleneck.get("type"),
            "bottleneck_location": bottleneck.get("location", ""),
            "reasoning": "Basic recommendation for detected issue",
            "implementation": "Analyze query patterns and consider optimization strategies",
        }

    def _generate_implementation_guidance(self, recommendation: dict[str, Any]) -> str:
        """Generate step-by-step implementation guidance."""
        category = recommendation.get("category", "")
        effort = recommendation.get("effort", "medium")

        guidance_parts = []

        # Effort-based guidance
        if effort == "low":
            guidance_parts.append("This is a quick fix that can be implemented immediately.")
        elif effort == "medium":
            guidance_parts.append("This requires moderate changes to the query structure.")
        elif effort == "high":
            guidance_parts.append(
                "This requires significant query restructuring or schema changes."
            )

        # Category-specific guidance
        if category == "indexing":
            guidance_parts.extend(
                [
                    "1. Analyze the property selectivity",
                    "2. Create the suggested index",
                    "3. Test query performance after index creation",
                    "4. Monitor index usage and maintenance",
                ]
            )
        elif category == "query_structure":
            guidance_parts.extend(
                [
                    "1. Review the current query structure",
                    "2. Implement the suggested pattern changes",
                    "3. Test the modified query for correctness",
                    "4. Compare performance before and after",
                ]
            )
        elif category == "pattern_optimization":
            guidance_parts.extend(
                [
                    "1. Understand the current pattern limitations",
                    "2. Apply the suggested pattern bounds",
                    "3. Verify results are still correct",
                    "4. Monitor query execution time",
                ]
            )
        else:
            guidance_parts.extend(
                [
                    "1. Review the identified issue",
                    "2. Consider the suggested optimization",
                    "3. Implement changes incrementally",
                    "4. Test and validate improvements",
                ]
            )

        return " ".join(guidance_parts)

    def _adjust_priority_by_severity(self, base_priority: str, severity: int) -> str:
        """Adjust recommendation priority based on bottleneck severity."""
        # priority_scores = {"low": 1, "medium": 2, "high": 3}  # Not currently used

        # Increase priority for high-severity issues (but never decrease)
        if severity >= 8:
            return "high"
        elif severity >= 6 and base_priority == "low":
            return "medium"

        # Keep original priority for all other cases
        return base_priority

    def _priority_to_score(self, priority: str) -> int:
        """Convert priority string to numeric score for sorting."""
        scores = {"low": 1, "medium": 2, "high": 3}
        return scores.get(priority.lower(), 2)

    def _impact_to_score(self, impact: str) -> int:
        """Convert impact string to numeric score for sorting."""
        scores = {"low": 1, "medium": 2, "high": 3, "unknown": 1}
        return scores.get(impact.lower(), 2)

    def _deduplicate_recommendations(
        self, recommendations: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        """Remove duplicate recommendations based on type and location."""
        seen = set()
        unique_recommendations = []

        for rec in recommendations:
            key = (rec.get("bottleneck_type"), rec.get("bottleneck_location", ""))
            if key not in seen:
                seen.add(key)
                unique_recommendations.append(rec)

        return unique_recommendations

    def score_recommendation_severity(
        self, recommendation: dict[str, Any], query_complexity: int
    ) -> int:
        """
        Score recommendation severity (1-10 scale) considering query complexity.

        Args:
            recommendation: The recommendation to score
            query_complexity: Overall query complexity score (0-100)

        Returns:
            Severity score (1-10)
        """
        base_severity = recommendation.get("severity", 5)
        priority_score = self._priority_to_score(recommendation.get("priority", "medium"))
        impact_score = self._impact_to_score(recommendation.get("impact", "medium"))

        # Adjust for query complexity
        complexity_factor = min(2, query_complexity / 50)  # Scale 0-2

        # Calculate final score
        final_score = (base_severity + priority_score + impact_score) / 3
        final_score *= 1 + complexity_factor * 0.2  # Boost for complex queries

        return min(10, int(final_score))
