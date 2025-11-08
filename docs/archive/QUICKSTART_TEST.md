# Quick Start: Testing with Movie Database & Gemini

This guide will help you test the Neo4j YASS MCP server with your Movie Neo4j instance and Gemini API.

## Prerequisites

- ✅ Free Movie Neo4j instance
- ✅ Gemini API key
- ✅ Python 3.13 installed
- ✅ Project dependencies installed

## Step 1: Create Your `.env` File

Create a `.env` file in the project root with your credentials:

```bash
# Copy the example file
cp .env.example .env

# Edit the file with your credentials
nano .env  # or use your preferred editor
```

Update these key settings:

```bash
# Neo4j Movie Database Connection
NEO4J_URI=bolt://your-movie-instance.databases.neo4j.io:7687
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=your_neo4j_password
NEO4J_DATABASE=neo4j

# Gemini Configuration
LLM_PROVIDER=google-genai
LLM_MODEL=gemini-pro
LLM_API_KEY=your_gemini_api_key_here
LLM_TEMPERATURE=0

# Security Settings (for testing)
ALLOW_WEAK_PASSWORDS=true  # Only if using weak password for testing
DEBUG_MODE=true
ENVIRONMENT=development

# Keep security features enabled
SANITIZER_ENABLED=true
COMPLEXITY_LIMIT_ENABLED=true
NEO4J_READ_ONLY=false
```

## Step 2: Install Dependencies

```bash
# Activate virtual environment
source .venv/bin/activate

# Install dependencies (if not already done)
pip install -e .
```

## Step 3: Test the Server

### Option A: Run as Python Module (Recommended for Testing)

```bash
python -m neo4j_yass_mcp.server
```

### Option B: Run with MCP Inspector (Interactive Testing)

```bash
# Install MCP Inspector globally (if not already installed)
npm install -g @modelcontextprotocol/inspector

# Run with inspector
mcp dev src/neo4j_yass_mcp/server.py
```

This will open an interactive web interface where you can test queries.

## Step 4: Test Queries

Try these queries with your Movie database:

### 1. Simple Movie Query
```
Natural Language: "What movies are in the database?"
Expected Cypher: MATCH (m:Movie) RETURN m.title LIMIT 10
```

### 2. Actor Query
```
Natural Language: "Who acted in The Matrix?"
Expected Cypher: MATCH (p:Person)-[:ACTED_IN]->(m:Movie {title: 'The Matrix'}) RETURN p.name
```

### 3. Director Query
```
Natural Language: "What movies did Tom Hanks act in?"
Expected Cypher: MATCH (p:Person {name: 'Tom Hanks'})-[:ACTED_IN]->(m:Movie) RETURN m.title
```

### 4. Complex Query
```
Natural Language: "Find all actors who worked with Tom Hanks"
Expected Cypher: MATCH (tom:Person {name: 'Tom Hanks'})-[:ACTED_IN]->(m:Movie)<-[:ACTED_IN]-(coactor:Person)
WHERE tom <> coactor
RETURN DISTINCT coactor.name LIMIT 20
```

## Step 5: Verify Security Features

### Test Query Sanitizer (Should Block)
```cypher
LOAD CSV FROM 'file:///etc/passwd' AS line RETURN line
```
Expected: ❌ Blocked by sanitizer

### Test Complexity Limiter (Should Warn/Block)
```cypher
MATCH (a)-[*]->(b)-[*]->(c) RETURN a, b, c
```
Expected: ❌ Blocked by complexity limiter (unbounded patterns)

### Test Read-Only Mode
```bash
# Set in .env: NEO4J_READ_ONLY=true
# Then try:
CREATE (n:Test) RETURN n
```
Expected: ❌ Blocked by read-only mode

## Step 6: Monitor Logs

Watch the logs for security events:

```bash
# In another terminal
tail -f logs/audit/audit_*.log

# Or view in JSON format
cat logs/audit/audit_*.log | jq .
```

## Troubleshooting

### Connection Issues

```bash
# Test Neo4j connection directly
python -c "
from neo4j import GraphDatabase
driver = GraphDatabase.driver('bolt://your-uri:7687', auth=('neo4j', 'password'))
driver.verify_connectivity()
print('✅ Connection successful!')
driver.close()
"
```

### Gemini API Issues

```bash
# Test Gemini API
python -c "
from langchain_google_genai import ChatGoogleGenerativeAI
llm = ChatGoogleGenerativeAI(model='gemini-pro', google_api_key='your-key')
result = llm.invoke('Hello')
print(f'✅ Gemini working: {result.content}')
"
```

### Schema Refresh

If queries aren't working well, refresh the schema:

```python
# In Python REPL
from neo4j_yass_mcp.server import initialize_neo4j, refresh_schema
initialize_neo4j()
result = await refresh_schema()
print(result)
```

## Example Session Output

```
2025-11-08 15:30:00 - neo4j_yass_mcp.server - INFO - Query sanitizer enabled (injection + UTF-8 attack protection active)
2025-11-08 15:30:00 - neo4j_yass_mcp.server - INFO - Query complexity limiter enabled (prevents resource exhaustion attacks)
2025-11-08 15:30:01 - neo4j_yass_mcp.server - INFO - Connecting to Neo4j at bolt://your-instance:7687
2025-11-08 15:30:02 - neo4j_yass_mcp.server - INFO - Initializing LLM: google-genai/gemini-pro
2025-11-08 15:30:02 - neo4j_yass_mcp.server - INFO - Neo4j MCP Server initialized successfully
2025-11-08 15:30:02 - neo4j_yass_mcp.server - INFO - Starting MCP server with stdio transport
```

## Next Steps

1. **Test with MCP Inspector**: Most interactive and visual
2. **Integrate with Claude Desktop**: Add to your Claude Desktop config
3. **Run Integration Tests**: `pytest tests/integration/ -v`
4. **Monitor Security**: Check audit logs in `logs/audit/`

## Security Notes

- ⚠️ **Never use `ALLOW_WEAK_PASSWORDS=true` in production**
- ⚠️ **Never use `DEBUG_MODE=true` in production**
- ⚠️ **Keep `SANITIZER_ENABLED=true` always**
- ⚠️ **Keep `COMPLEXITY_LIMIT_ENABLED=true` always**
- ✅ **Review audit logs regularly**

## Getting Help

If you encounter issues:

1. Check the logs: `tail -f logs/audit/audit_*.log`
2. Enable debug mode: `DEBUG_MODE=true`
3. Run tests: `pytest tests/ -v`
4. Check configuration: `cat .env`

Enjoy testing! 🎬🎥
