#!/usr/bin/env python3
"""
Query Analysis Examples - Demonstrates various use cases for the query analysis tool.

This script provides practical examples of using the query analysis tool for:
- Basic query analysis
- Performance optimization
- Schema optimization
- Production validation
- Batch analysis
"""

import asyncio
import json
import sys
from typing import Any, Dict, List

# Add the src directory to Python path
sys.path.insert(0, "/Users/hdjebar/Projects/kimi/neo4j-yass-mcp/src")

from neo4j_yass_mcp.server import analyze_query_performance
from fastmcp import Context


async def example_basic_analysis():
    """Example 1: Basic query analysis."""
    print("=" * 60)
    print("EXAMPLE 1: Basic Query Analysis")
    print("=" * 60)

    # Simple query analysis
    query = "MATCH (n:Person) WHERE n.age > 25 RETURN n.name, n.age"

    print(f"Analyzing query: {query}")
    print()

    # Use EXPLAIN mode for quick analysis
    result = await analyze_query_performance(
        query=query, mode="explain", include_recommendations=True
    )

    if result["success"]:
        print(f"✅ Analysis completed successfully!")
        print(f"   Overall Severity: {result['analysis_summary']['overall_severity']}/10")
        print(f"   Bottlenecks Found: {result['bottlenecks_found']}")
        print(f"   Recommendations: {result['recommendations_count']}")
        print(f"   Risk Level: {result['risk_level']}")
        print(f"   Analysis Time: {result['execution_time_ms']}ms")
        print()

        # Show formatted report
        if "analysis_report" in result:
            print("📊 ANALYSIS REPORT:")
            print(result["analysis_report"])
    else:
        print(f"❌ Analysis failed: {result.get('error', 'Unknown error')}")

    print()


async def example_performance_optimization():
    """Example 2: Performance optimization workflow."""
    print("=" * 60)
    print("EXAMPLE 2: Performance Optimization Workflow")
    print("=" * 60)

    # Problematic query (likely to have performance issues)
    problematic_query = """
    MATCH (user:Person)-[:FRIENDS_WITH*]-(friend:Person)
    WHERE user.name = 'Alice'
    RETURN friend.name, friend.age
    """

    print(f"Analyzing potentially problematic query...")
    print(f"Query: {problematic_query.strip()}")
    print()

    # Use PROFILE mode for detailed analysis
    result = await analyze_query_performance(
        query=problematic_query, mode="profile", include_recommendations=True
    )

    if result["success"]:
        print(f"📈 PERFORMANCE ANALYSIS:")
        print(f"   Cost Score: {result['cost_score']}/10")
        print(
            f"   Estimated Execution Time: {result.get('detailed_analysis', {}).get('cost_estimate', {}).get('execution_time_estimate_ms', 'Unknown')}ms"
        )
        print(
            f"   Estimated Memory: {result.get('detailed_analysis', {}).get('cost_estimate', {}).get('memory_estimate_mb', 'Unknown')}MB"
        )
        print()

        # Show high-priority recommendations
        high_priority_recs = [
            rec
            for rec in result.get("detailed_analysis", {}).get("recommendations", [])
            if rec.get("priority") == "high"
        ]

        if high_priority_recs:
            print("🔧 HIGH-PRIORITY RECOMMENDATIONS:")
            for i, rec in enumerate(high_priority_recs[:3], 1):
                print(f"   {i}. {rec['title']}")
                print(f"      {rec['description']}")
                print(f"      Example: {rec['example']}")
                print()
        else:
            print("✅ No high-priority issues detected!")
    else:
        print(f"❌ Analysis failed: {result.get('error', 'Unknown error')}")

    print()


async def example_schema_optimization():
    """Example 3: Schema optimization recommendations."""
    print("=" * 60)
    print("EXAMPLE 3: Schema Optimization")
    print("=" * 60)

    # Query that would benefit from indexing
    index_candidate_query = """
    MATCH (product:Product)
    WHERE product.category = 'Electronics' 
      AND product.price > 500
      AND product.brand = 'Apple'
    RETURN product.name, product.price
    ORDER BY product.price DESC
    LIMIT 20
    """

    print(f"Analyzing query for index optimization opportunities...")
    print(f"Query: {index_candidate_query.strip()}")
    print()

    result = await analyze_query_performance(
        query=index_candidate_query, mode="explain", include_recommendations=True
    )

    if result["success"]:
        # Look for index-related recommendations
        index_recommendations = [
            rec
            for rec in result.get("detailed_analysis", {}).get("recommendations", [])
            if "index" in rec.get("title", "").lower()
        ]

        if index_recommendations:
            print("🗂️  INDEX OPTIMIZATION OPPORTUNITIES:")
            for i, rec in enumerate(index_recommendations, 1):
                print(f"   {i}. {rec['title']}")
                print(f"      {rec['description']}")
                print(f"      SQL: {rec['example']}")
                print(f"      Effort: {rec['effort']} | Impact: {rec['impact']}")
                print()
        else:
            print("✅ No index optimization opportunities detected!")

        # Show any missing index bottlenecks
        missing_index_bottlenecks = [
            b
            for b in result.get("detailed_analysis", {}).get("bottlenecks", [])
            if b.get("type") == "missing_index"
        ]

        if missing_index_bottlenecks:
            print("⚠️  MISSING INDEX DETECTED:")
            for bottleneck in missing_index_bottlenecks:
                print(f"   - {bottleneck['description']}")
                print(f"     Impact: {bottleneck['impact']}")
                print()
    else:
        print(f"❌ Analysis failed: {result.get('error', 'Unknown error')}")

    print()


async def example_production_validation():
    """Example 4: Production query validation."""
    print("=" * 60)
    print("EXAMPLE 4: Production Query Validation")
    print("=" * 60)

    # Simulate user-submitted queries for production
    user_queries = [
        "MATCH (n) RETURN n",  # Potentially dangerous
        "MATCH (n:Person) RETURN n.name LIMIT 100",  # Safer
        "MATCH (n:Person)-[:KNOWS*]-(m:Person) RETURN n, m",  # Could be expensive
    ]

    print("Validating user queries for production deployment...")
    print()

    validation_results = []

    for i, query in enumerate(user_queries, 1):
        print(f"Query {i}: {query}")

        # Use EXPLAIN mode for quick validation
        result = await analyze_query_performance(
            query=query,
            mode="explain",
            include_recommendations=False,  # Faster without recommendations
        )

        if result["success"]:
            validation = {
                "query": query,
                "risk_level": result["risk_level"],
                "cost_score": result["cost_score"],
                "bottlenecks": result["bottlenecks_found"],
                "approved": result["risk_level"] in ["low", "medium"] and result["cost_score"] <= 7,
            }
            validation_results.append(validation)

            status = "✅ APPROVED" if validation["approved"] else "❌ REJECTED"
            print(f"   {status}")
            print(
                f"   Risk: {result['risk_level']} | Cost: {result['cost_score']}/10 | Issues: {result['bottlenecks_found']}"
            )

            if not validation["approved"]:
                print(f"   Reason: High risk or cost detected")
        else:
            print(f"   ❌ VALIDATION FAILED: {result.get('error', 'Unknown error')}")

        print()

    # Summary
    approved = sum(1 for v in validation_results if v["approved"])
    total = len(validation_results)

    print(f"📊 VALIDATION SUMMARY:")
    print(f"   Total Queries: {total}")
    print(f"   Approved: {approved}")
    print(f"   Rejected: {total - approved}")
    print(f"   Success Rate: {approved / total * 100:.1f}%")
    print()


async def example_batch_analysis():
    """Example 5: Batch analysis of multiple queries."""
    print("=" * 60)
    print("EXAMPLE 5: Batch Analysis")
    print("=" * 60)

    # Collection of queries to analyze
    queries = [
        "MATCH (n:Person) RETURN n.name",
        "MATCH (n:Movie) RETURN n.title",
        "MATCH (n:Person)-[:ACTED_IN]->(m:Movie) RETURN n.name, m.title",
        "MATCH (n:Person)-[:DIRECTED]->(m:Movie) WHERE m.year > 2000 RETURN n.name, m.title",
        "MATCH (n:Person)-[:FOLLOWS]-(m:Person) RETURN n.name, m.name",
    ]

    print(f"Analyzing {len(queries)} queries in batch...")
    print()

    # Run batch analysis
    results = []
    for i, query in enumerate(queries, 1):
        print(f"Analyzing query {i}/{len(queries)}...", end=" ")

        result = await analyze_query_performance(
            query=query,
            mode="explain",  # Use EXPLAIN for faster batch processing
            include_recommendations=False,  # Skip recommendations for speed
        )

        if result["success"]:
            results.append(
                {
                    "query": query,
                    "cost_score": result["cost_score"],
                    "risk_level": result["risk_level"],
                    "execution_time": result["execution_time_ms"],
                }
            )
            print(f"✅ (Score: {result['cost_score']})")
        else:
            print(f"❌ Failed")

    print()

    # Analyze results
    if results:
        # Sort by cost score (highest first)
        results.sort(key=lambda x: x["cost_score"], reverse=True)

        print("📈 BATCH ANALYSIS RESULTS:")
        print(f"   Average Cost Score: {sum(r['cost_score'] for r in results) / len(results):.1f}")
        print(f"   Highest Cost Query: {results[0]['cost_score']}/10")
        print(
            f"   Average Analysis Time: {sum(r['execution_time'] for r in results) / len(results):.1f}ms"
        )
        print()

        # Show top 3 most expensive queries
        print("🔍 TOP 3 MOST EXPENSIVE QUERIES:")
        for i, result in enumerate(results[:3], 1):
            print(f"   {i}. Cost: {result['cost_score']}/10 | Risk: {result['risk_level']}")
            print(f"      Query: {result['query'][:60]}...")
            print()

        # Show queries that need attention
        attention_needed = [r for r in results if r["cost_score"] > 5 or r["risk_level"] == "high"]
        if attention_needed:
            print(f"⚠️  QUERIES NEEDING ATTENTION: {len(attention_needed)}")
            for result in attention_needed:
                print(f"   - Cost: {result['cost_score']}/10, Risk: {result['risk_level']}")
                print(f"     Query: {result['query'][:50]}...")
            print()
    else:
        print("❌ No successful analyses completed")

    print()


async def example_monitoring_and_alerts():
    """Example 6: Monitoring and alerting setup."""
    print("=" * 60)
    print("EXAMPLE 6: Monitoring and Alerting")
    print("=" * 60)

    # Simulate monitoring important queries
    important_queries = [
        {
            "name": "User Authentication",
            "query": "MATCH (u:User {email: $email}) RETURN u",
            "max_acceptable_cost": 3,
            "max_acceptable_risk": "medium",
        },
        {
            "name": "Dashboard Data",
            "query": "MATCH (u:User)-[:HAS_ORDER]->(o:Order) RETURN u, count(o) as order_count",
            "max_acceptable_cost": 5,
            "max_acceptable_risk": "medium",
        },
        {
            "name": "Report Generation",
            "query": "MATCH (u:User)-[:HAS_ORDER]->(o:Order)-[:CONTAINS]->(p:Product) RETURN u, o, collect(p)",
            "max_acceptable_cost": 7,
            "max_acceptable_risk": "high",
        },
    ]

    print("Monitoring critical queries for performance issues...")
    print()

    alerts_triggered = []

    for query_config in important_queries:
        print(f"Monitoring: {query_config['name']}")
        print(f"   Query: {query_config['query'][:60]}...")

        # Analyze the query
        result = await analyze_query_performance(
            query=query_config["query"], mode="explain", include_recommendations=False
        )

        if result["success"]:
            cost_score = result["cost_score"]
            risk_level = result["risk_level"]

            print(f"   Cost Score: {cost_score}/10 (Limit: {query_config['max_acceptable_cost']})")
            print(f"   Risk Level: {risk_level} (Limit: {query_config['max_acceptable_risk']})")

            # Check if thresholds are exceeded
            cost_exceeded = cost_score > query_config["max_acceptable_cost"]
            risk_exceeded = risk_level not in ["low", query_config["max_acceptable_risk"]]

            if cost_exceeded or risk_exceeded:
                alert = {
                    "query_name": query_config["name"],
                    "cost_score": cost_score,
                    "risk_level": risk_level,
                    "reason": "Cost exceeded" if cost_exceeded else "Risk exceeded",
                }
                alerts_triggered.append(alert)
                print(f"   🚨 ALERT: {alert['reason']}")
            else:
                print(f"   ✅ Performance within acceptable limits")
        else:
            print(f"   ❌ Analysis failed: {result.get('error', 'Unknown error')}")

        print()

    # Alert summary
    if alerts_triggered:
        print("🚨 PERFORMANCE ALERTS TRIGGERED:")
        for alert in alerts_triggered:
            print(
                f"   - {alert['query_name']}: Cost {alert['cost_score']}, Risk {alert['risk_level']}"
            )
            print(f"     Reason: {alert['reason']}")
        print()
        print("💡 RECOMMENDED ACTIONS:")
        print("   1. Review and optimize the flagged queries")
        print("   2. Consider adding indexes or query restructuring")
        print("   3. Implement query result caching if appropriate")
        print("   4. Monitor query execution times in production")
    else:
        print("✅ All queries are performing within acceptable limits!")

    print()


async def main():
    """Main function to run all examples."""
    print("🚀 Neo4j Query Analysis Tool - Examples")
    print("=" * 60)
    print()

    # Check if Neo4j is configured (skip if not)
    if not os.getenv("NEO4J_URI"):
        print("⚠️  Neo4j not configured. These examples use mock data.")
        print("   Set NEO4J_URI environment variable to analyze real queries.")
        print()

    try:
        # Run all examples
        await example_basic_analysis()
        await example_performance_optimization()
        await example_schema_optimization()
        await example_production_validation()
        await example_batch_analysis()
        await example_monitoring_and_alerts()

        print("=" * 60)
        print("✅ All examples completed successfully!")
        print("=" * 60)
        print()
        print("📚 NEXT STEPS:")
        print("   1. Try analyzing your own queries")
        print("   2. Integrate analysis into your development workflow")
        print("   3. Set up monitoring for critical queries")
        print("   4. Read the full user guide for advanced features")
        print()

    except Exception as e:
        print(f"❌ Examples failed: {str(e)}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    # Run the examples
    asyncio.run(main())
