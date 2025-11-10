# Neo4j YASS MCP Test Page Design Document

## Overview

This document describes the design of a simple HTML page that allows users to test the Neo4j YASS MCP server functionality directly from a web browser. This test page will serve as a basic interface for sending queries to the MCP server and viewing results.

## Objectives

- Provide a simple, self-contained HTML page for testing MCP server functionality
- Allow users to easily send both natural language and raw Cypher queries
- Display query results in a readable format
- Show debugging information (generated Cypher, execution time, etc.)
- Support basic configuration options (endpoint URL, authentication, etc.)

## Design Requirements

### Functional Requirements

1. **Query Input**
   - Text area for natural language queries
   - Text area for raw Cypher queries
   - Toggle between query types
   - Submit button for each query type

2. **Configuration**
   - Endpoint URL input field
   - Authentication token field
   - Query timeout configuration

3. **Results Display**
   - Raw JSON response display
   - Formatted response view
   - Generated Cypher query (for NL queries)
   - Execution time information
   - Error message display

4. **Testing Features**
   - Multiple pre-defined test queries
   - Simple query history
   - Clear results button

### Non-Functional Requirements

1. **Simplicity**
   - Single HTML file with embedded JavaScript
   - No external dependencies
   - Lightweight and fast loading

2. **Compatibility**
   - Works in all modern browsers
   - Responsive design for different screen sizes

3. **Security**
   - No automatic credential storage
   - Clear token field after use option

## UI Design

### Layout Structure

```
+-------------------------------------+
|          MCP Test Page Header       |
+-------------------------------------+
|  Configuration Panel                |
|  [Endpoint: _________________]      |
|  [Token:    _________________]      |
|  [Timeout:  _________________]      |
+-------------------------------------+
|  Query Type Toggle                  |
|  ( ) Natural Language  (*) Cypher   |
+-------------------------------------+
|  Query Input Area (Natural Language)|
|  [Enter your natural language      |
|   query here...                ]    |
|                                     |
|  OR                                 |
|                                     |
|  Query Input Area (Cypher)          |
|  [Enter your Cypher query here...   |
|                                     |
+-------------------------------------+
|  [Submit Query] [Clear Results]     |
+-------------------------------------+
|  Test Queries (Quick Buttons)       |
|  [Sample NL Query] [Sample Cypher]  |
+-------------------------------------+
|  Results Panel                      |
|  +---------------------------------+|
|  | Generated Cypher:               ||
|  | MATCH (n) RETURN n LIMIT 10     ||
|  |                                 ||
|  | Execution Time: 123ms           ||
|  |                                 ||
|  | Response:                       ||
|  | {                               ||
|  |   "results": [...],             ||
|  |   "success": true               ||
|  | }                               ||
|  +---------------------------------+|
+-------------------------------------+
```

### HTML Structure

```html
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Neo4j YASS MCP Test Page</title>
    <style>
        /* CSS will be embedded for self-containment */
    </style>
</head>
<body>
    <header>
        <h1>Neo4j YASS MCP Test Page</h1>
        <p>Test your Neo4j MCP server endpoints</p>
    </header>

    <section id="configuration">
        <h2>Configuration</h2>
        <div class="config-row">
            <label for="endpoint">MCP Endpoint:</label>
            <input type="text" id="endpoint" placeholder="http://localhost:8000" value="http://localhost:8000">
        </div>
        <div class="config-row">
            <label for="token">Authentication Token:</label>
            <input type="password" id="token" placeholder="Enter your token">
        </div>
        <div class="config-row">
            <label for="timeout">Timeout (ms):</label>
            <input type="number" id="timeout" value="30000" min="1000" max="60000">
        </div>
    </section>

    <section id="query-type">
        <h2>Query Type</h2>
        <div class="toggle-group">
            <button id="nl-toggle" class="toggle-btn active">Natural Language</button>
            <button id="cypher-toggle" class="toggle-btn">Raw Cypher</button>
        </div>
    </section>

    <section id="query-input">
        <h2>Query Input</h2>
        <div id="nl-query" class="query-section">
            <label for="nl-text">Natural Language Query:</label>
            <textarea id="nl-text" placeholder="Ask a question about your graph (e.g., 'Who starred in Top Gun?')"></textarea>
        </div>
        <div id="cypher-query" class="query-section hidden">
            <label for="cypher-text">Raw Cypher Query:</label>
            <textarea id="cypher-text" placeholder="Enter a Cypher query (e.g., 'MATCH (n:Person) RETURN n LIMIT 10')"></textarea>
        </div>
    </section>

    <section id="test-buttons">
        <h2>Quick Test Queries</h2>
        <div class="button-row">
            <button class="sample-btn" data-type="nl" data-query="Who are the top 5 actors by number of movies?">Top 5 Actors</button>
            <button class="sample-btn" data-type="nl" data-query="Show all movies released in 1986">Movies from 1986</button>
        </div>
        <div class="button-row">
            <button class="sample-btn" data-type="cypher" data-query="MATCH (n) RETURN count(n) AS nodeCount">Count All Nodes</button>
            <button class="sample-btn" data-type="cypher" data-query="MATCH (n) RETURN labels(n) LIMIT 10">Get Node Labels</button>
        </div>
    </section>

    <section id="actions">
        <button id="submit-btn">Submit Query</button>
        <button id="clear-btn">Clear Results</button>
    </section>

    <section id="results">
        <h2>Results</h2>
        <div id="results-display">
            <div id="results-info" class="results-info">No results yet. Submit a query to see results.</div>
            <div id="cypher-output" class="result-section hidden">
                <h3>Generated Cypher Query:</h3>
                <pre id="generated-cypher"></pre>
            </div>
            <div id="execution-info" class="result-section hidden">
                <h3>Execution Info:</h3>
                <div id="exec-time"></div>
            </div>
            <div id="response-output" class="result-section hidden">
                <h3>Response:</h3>
                <pre id="response-data"></pre>
            </div>
            <div id="error-output" class="result-section hidden error">
                <h3>Error:</h3>
                <pre id="error-message"></pre>
            </div>
        </div>
    </section>

    <script>
        // JavaScript code for functionality will be embedded
    </script>
</body>
</html>
```

## Functionality

### JavaScript Implementation

The page will include JavaScript to handle:

1. **Query Submission**
   - Making HTTP requests to the MCP server
   - Handling both NL and Cypher query types
   - Proper request formatting

2. **Response Processing**
   - Parsing JSON responses
   - Displaying generated Cypher for NL queries
   - Calculating and showing execution time

3. **UI Interactions**
   - Toggle between NL and Cypher query modes
   - Sample query buttons
   - Real-time validation
   - Loading indicators

4. **Error Handling**
   - Network errors
   - MCP server errors
   - Validation errors

### API Endpoints Used

The test page will interact with the following MCP tools:

1. **query_graph** - For natural language queries
2. **execute_cypher** - For raw Cypher queries
3. **get_schema** - To retrieve database schema (as a test)

## Security Considerations

1. **Token Management**
   - Option to clear token after each request
   - Password field for token entry
   - No token storage in local storage by default

2. **Input Validation**
   - Basic validation of endpoint URL
   - Sanitization of display outputs

3. **CORS Handling**
   - Designed to work with properly configured MCP servers
   - Clear instructions for CORS setup if needed

## Testing Scenarios

The page will support testing of:

1. **Basic Functionality**
   - Simple NL queries
   - Raw Cypher execution
   - Schema retrieval

2. **Error Handling**
   - Invalid queries
   - Network timeouts
   - Authentication failures

3. **Performance**
   - Execution time measurement
   - Large result set handling

## Deployment

### Single File Distribution

The HTML page will be completely self-contained in a single file with:
- Embedded CSS for styling
- Embedded JavaScript for functionality
- No external dependencies

### Usage Instructions

Users will simply:
1. Download the HTML file
2. Open it in a web browser
3. Configure the endpoint URL
4. Enter queries and submit

## Conclusion

This test page will provide a simple but effective way to test the Neo4j YASS MCP server functionality without requiring additional tools or complex setup. It will be useful for development, debugging, and demonstration purposes.