#!/usr/bin/env python3
"""
Test script to verify the Query Analysis Tool integration with the HTML test page.

This script simulates the HTTP requests that the HTML page would make to test
the new analyze_query_performance functionality.
"""

import asyncio
import sys

# Add the src directory to Python path
sys.path.insert(0, "/Users/hdjebar/Projects/kimi/neo4j-yass-mcp/src")

from neo4j_yass_mcp.server import analyze_query_performance


async def test_query_analysis_integration():
    """Test the query analysis tool with various scenarios."""

    print("🧪 Testing Query Analysis Tool Integration")
    print("=" * 60)

    # Test 1: Basic EXPLAIN mode analysis
    print("\n1️⃣ Testing EXPLAIN mode with simple query...")
    try:
        result = await analyze_query_performance(
            query="MATCH (n:Person) WHERE n.age > 25 RETURN n.name",
            mode="explain",
            include_recommendations=True,
        )

        print("✅ EXPLAIN analysis successful!")
        print(f"   Success: {result['success']}")
        print(f"   Mode: {result['mode']}")
        print(f"   Cost Score: {result['cost_score']}/10")
        print(f"   Risk Level: {result['risk_level']}")
        print(f"   Bottlenecks: {result['bottlenecks_found']}")
        print(f"   Recommendations: {result['recommendations_count']}")
        print(f"   Execution Time: {result['execution_time_ms']}ms")

        # Verify response structure matches HTML expectations
        required_fields = [
            "success",
            "mode",
            "cost_score",
            "risk_level",
            "bottlenecks_found",
            "recommendations_count",
            "execution_time_ms",
            "analysis_summary",
        ]
        missing_fields = [field for field in required_fields if field not in result]
        if missing_fields:
            print(f"⚠️  Missing fields: {missing_fields}")
        else:
            print("✅ All required fields present for HTML integration")

    except Exception as e:
        print(f"❌ EXPLAIN test failed: {str(e)}")
        return False

    # Test 2: PROFILE mode analysis
    print("\n2️⃣ Testing PROFILE mode...")
    try:
        result = await analyze_query_performance(
            query="MATCH (n:Person) RETURN n.name LIMIT 10",
            mode="profile",
            include_recommendations=True,
        )

        print("✅ PROFILE analysis successful!")
        print(f"   Mode: {result['mode']}")
        print(f"   Detailed analysis available: {'detailed_analysis' in result}")

        if "detailed_analysis" in result:
            detailed = result["detailed_analysis"]
            print(f"   Execution plan available: {'execution_plan' in detailed}")
            print(
                f"   Bottlenecks available: {'bottlenecks' in detailed and len(detailed['bottlenecks']) > 0}"
            )
            print(
                f"   Recommendations available: {'recommendations' in detailed and len(detailed['recommendations']) > 0}"
            )

    except Exception as e:
        print(f"❌ PROFILE test failed: {str(e)}")
        return False

    # Test 3: Problematic query (should detect bottlenecks)
    print("\n3️⃣ Testing problematic query (should detect issues)...")
    try:
        problematic_query = """
        MATCH (a), (b), (c)
        WHERE a.name = 'test' AND b.age > 25
        OPTIONAL MATCH (a)-[*]->(d)
        WITH *
        RETURN a.name, b.name, c.name, d.name
        """

        result = await analyze_query_performance(
            query=problematic_query, mode="explain", include_recommendations=True
        )

        print("✅ Problematic query analysis successful!")
        print(f"   Bottlenecks found: {result['bottlenecks_found']}")
        print(f"   Recommendations: {result['recommendations_count']}")

        # Should find some issues with this query
        if result["bottlenecks_found"] > 0:
            print("✅ Successfully detected performance issues!")

            # Show first bottleneck if available
            if "detailed_analysis" in result and result["detailed_analysis"].get("bottlenecks"):
                first_bottleneck = result["detailed_analysis"]["bottlenecks"][0]
                print(
                    f"   First issue: {first_bottleneck.get('type', 'Unknown')} - {first_bottleneck.get('description', 'No description')}"
                )
        else:
            print("ℹ️  No significant issues detected (query might be well-structured)")

    except Exception as e:
        print(f"❌ Problematic query test failed: {str(e)}")
        return False

    # Test 4: HTML-formatted report
    print("\n4️⃣ Testing HTML-formatted analysis report...")
    try:
        result = await analyze_query_performance(
            query="MATCH (n:Person) RETURN n.name LIMIT 5",
            mode="explain",
            include_recommendations=True,
        )

        if "analysis_report" in result:
            print("✅ HTML-formatted report available!")
            print("📄 Sample report content:")
            report_lines = result["analysis_report"].split("\n")[:5]
            for line in report_lines:
                print(f"   {line}")
            print("   ... (report truncated)")
        else:
            print("⚠️  No formatted report available")

    except Exception as e:
        print(f"❌ HTML report test failed: {str(e)}")
        return False

    # Test 5: Error handling
    print("\n5️⃣ Testing error handling...")
    try:
        # Test invalid mode
        result = await analyze_query_performance(
            query="MATCH (n) RETURN n", mode="invalid_mode", include_recommendations=True
        )

        if not result["success"]:
            print("✅ Error handling works correctly!")
            print(f"   Error: {result.get('error', 'Unknown error')}")
            print(f"   Error type: {result.get('type', 'Unknown')}")
        else:
            print("❌ Expected error but got success")
            return False

    except Exception as e:
        print(f"✅ Exception properly raised: {str(e)}")

    return True


async def test_html_page_compatibility():
    """Test that the results are compatible with the HTML test page format."""

    print("\n🌐 Testing HTML Page Compatibility")
    print("=" * 60)

    # Test the exact format that the HTML page expects
    test_query = "MATCH (n:Person) WHERE n.age > 30 RETURN n.name, n.age LIMIT 10"

    try:
        result = await analyze_query_performance(
            query=test_query, mode="explain", include_recommendations=True
        )

        print("✅ Query analysis successful!")

        # Verify HTML-specific requirements
        html_requirements = {
            "success": bool,
            "analysis_summary": dict,
            "bottlenecks_found": int,
            "recommendations_count": int,
            "cost_score": int,
            "risk_level": str,
            "execution_time_ms": int,
            "analysis_report": str,
        }

        print("\n📋 HTML Compatibility Check:")
        all_good = True

        for field, expected_type in html_requirements.items():
            if field in result:
                if isinstance(result[field], expected_type):
                    print(f"   ✅ {field}: {type(result[field]).__name__} ✓")
                else:
                    print(
                        f"   ❌ {field}: Expected {expected_type.__name__}, got {type(result[field]).__name__}"
                    )
                    all_good = False
            else:
                print(f"   ⚠️  {field}: Missing")
                all_good = False

        # Test the analysis report format (what HTML page displays)
        if "analysis_report" in result:
            print("\n📄 Analysis Report Preview:")
            report_preview = (
                result["analysis_report"][:200] + "..."
                if len(result["analysis_report"]) > 200
                else result["analysis_report"]
            )
            print(f"   {report_preview}")

            # Check if report contains expected sections
            expected_sections = ["Query Performance Analysis", "Bottlenecks", "Recommendations"]
            missing_sections = [
                section for section in expected_sections if section not in result["analysis_report"]
            ]
            if missing_sections:
                print(f"   ⚠️  Missing sections: {missing_sections}")
            else:
                print("   ✅ All expected sections present")

        return all_good

    except Exception as e:
        print(f"❌ HTML compatibility test failed: {str(e)}")
        return False


async def main():
    """Main test function."""
    print("🚀 Neo4j Query Analysis Tool - HTML Page Integration Test")
    print("=" * 60)
    print("Testing compatibility with test-mcp.html page...")
    print()

    # Check if Neo4j is configured (use mock mode if not)
    import os

    if not os.getenv("NEO4J_URI"):
        print("⚠️  Neo4j not configured. Testing with mock responses.")
        print("   Set NEO4J_URI environment variable to test with real Neo4j.")
        print()

    # Run all tests
    tests_passed = 0
    total_tests = 3

    if await test_query_analysis_integration():
        tests_passed += 1
        print("\n✅ Query Analysis Integration: PASSED")
    else:
        print("\n❌ Query Analysis Integration: FAILED")

    if await test_html_page_compatibility():
        tests_passed += 1
        print("\n✅ HTML Page Compatibility: PASSED")
    else:
        print("\n❌ HTML Page Compatibility: FAILED")

    # Summary
    print("\n" + "=" * 60)
    print("📊 TEST SUMMARY:")
    print(f"   Tests Passed: {tests_passed}/{total_tests}")
    print(f"   Success Rate: {tests_passed / total_tests * 100:.1f}%")

    if tests_passed == total_tests:
        print("\n🎉 All tests passed! The Query Analysis Tool is ready for HTML page integration.")
        print("\n💡 Next Steps:")
        print("   1. Open tests/test-mcp.html in your browser")
        print("   2. Configure your MCP server endpoint")
        print("   3. Test the new 'Query Analysis Tool' section")
        print("   4. Try the problematic vs optimized query examples")
    else:
        print(f"\n⚠️  {total_tests - tests_passed} test(s) failed. Please review the errors above.")

    return tests_passed == total_tests


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
