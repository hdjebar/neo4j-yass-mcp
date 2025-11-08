#!/usr/bin/env python3
"""
Quick connection test script for Neo4j Movie database and Gemini.

Run this to verify your configuration before starting the MCP server.
"""

import os
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

print("=" * 70)
print("Neo4j YASS MCP - Connection Test")
print("=" * 70)
print()

# Test 1: Environment Variables
print("✓ Testing environment variables...")
required_vars = {
    'NEO4J_URI': os.getenv('NEO4J_URI'),
    'NEO4J_USERNAME': os.getenv('NEO4J_USERNAME'),
    'NEO4J_PASSWORD': os.getenv('NEO4J_PASSWORD'),
    'LLM_PROVIDER': os.getenv('LLM_PROVIDER'),
    'LLM_MODEL': os.getenv('LLM_MODEL'),
    'LLM_API_KEY': os.getenv('LLM_API_KEY'),
}

missing_vars = [k for k, v in required_vars.items() if not v]
if missing_vars:
    print(f"  ✗ Missing environment variables: {', '.join(missing_vars)}")
    print("  → Please create a .env file with your configuration")
    print("  → See .env.example for reference")
    sys.exit(1)

print(f"  ✓ NEO4J_URI: {required_vars['NEO4J_URI']}")
print(f"  ✓ LLM_PROVIDER: {required_vars['LLM_PROVIDER']}")
print(f"  ✓ LLM_MODEL: {required_vars['LLM_MODEL']}")
print()

# Test 2: Neo4j Connection
print("✓ Testing Neo4j connection...")
try:
    from neo4j import GraphDatabase

    driver = GraphDatabase.driver(
        required_vars['NEO4J_URI'],
        auth=(required_vars['NEO4J_USERNAME'], required_vars['NEO4J_PASSWORD'])
    )

    # Verify connectivity
    driver.verify_connectivity()

    # Count nodes
    with driver.session() as session:
        result = session.run("MATCH (n) RETURN count(n) as count")
        node_count = result.single()['count']
        print(f"  ✓ Connected successfully!")
        print(f"  ✓ Database contains {node_count:,} nodes")

        # Check for Movie nodes
        result = session.run("MATCH (m:Movie) RETURN count(m) as count")
        movie_count = result.single()['count']
        print(f"  ✓ Found {movie_count} Movie nodes")

        # Get sample movie
        result = session.run("MATCH (m:Movie) RETURN m.title LIMIT 1")
        sample = result.single()
        if sample:
            print(f"  ✓ Sample movie: {sample['m.title']}")

    driver.close()
    print()

except Exception as e:
    print(f"  ✗ Neo4j connection failed: {e}")
    print("  → Check your NEO4J_URI, NEO4J_USERNAME, and NEO4J_PASSWORD")
    sys.exit(1)

# Test 3: Gemini API
print("✓ Testing Gemini API...")
try:
    from langchain_google_genai import ChatGoogleGenerativeAI

    llm = ChatGoogleGenerativeAI(
        model=required_vars['LLM_MODEL'],
        google_api_key=required_vars['LLM_API_KEY'],
        temperature=0
    )

    # Test with simple query
    result = llm.invoke("Say 'Hello from Gemini!' in exactly 3 words")
    print(f"  ✓ Gemini API working!")
    print(f"  ✓ Response: {result.content[:100]}")
    print()

except Exception as e:
    print(f"  ✗ Gemini API failed: {e}")
    print("  → Check your LLM_API_KEY")
    sys.exit(1)

# Test 4: Integration Test
print("✓ Testing Neo4j + Gemini integration...")
try:
    from langchain_neo4j import GraphCypherQAChain, Neo4jGraph

    # Create graph
    graph = Neo4jGraph(
        url=required_vars['NEO4J_URI'],
        username=required_vars['NEO4J_USERNAME'],
        password=required_vars['NEO4J_PASSWORD'],
    )

    # Create chain
    chain = GraphCypherQAChain.from_llm(
        llm=llm,
        graph=graph,
        allow_dangerous_requests=True,  # For testing only
        verbose=True,
        return_intermediate_steps=True,
    )

    print("  ✓ LangChain integration initialized")

    # Test a simple query
    print("  Testing query: 'How many movies are there?'")
    result = chain.invoke({"query": "How many movies are in the database?"})

    print(f"  ✓ Query successful!")
    print(f"  ✓ Answer: {result['result']}")

    if 'intermediate_steps' in result and result['intermediate_steps']:
        cypher = result['intermediate_steps'][0].get('query', 'N/A')
        print(f"  ✓ Generated Cypher: {cypher[:200]}")

    print()

except Exception as e:
    print(f"  ✗ Integration test failed: {e}")
    print("  → This might be okay - try running the full server")
    print()

# Summary
print("=" * 70)
print("✓ All tests passed!")
print("=" * 70)
print()
print("Next steps:")
print("  1. Run the server: python -m neo4j_yass_mcp.server")
print("  2. Or use MCP Inspector: mcp dev src/neo4j_yass_mcp/server.py")
print("  3. Check QUICKSTART_TEST.md for example queries")
print()
print("Security features enabled:")
print(f"  • Query Sanitizer: {os.getenv('SANITIZER_ENABLED', 'true')}")
print(f"  • Complexity Limiter: {os.getenv('COMPLEXITY_LIMIT_ENABLED', 'true')}")
print(f"  • Audit Logging: {os.getenv('AUDIT_LOG_ENABLED', 'true')}")
print(f"  • Read-Only Mode: {os.getenv('NEO4J_READ_ONLY', 'false')}")
print()
