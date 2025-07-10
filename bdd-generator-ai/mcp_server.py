from fastapi import FastAPI, HTTPException
import os
import json
from tachyons import Client as TachyonsClient

# Initialize FastAPI application
app = FastAPI()

# Function to initialize Tachyons API client
def initialize_tachyons_client():
    tachyons_api_key = os.getenv("TACHYONS_API_KEY")
    if not tachyons_api_key:
        raise HTTPException(status_code=500, detail="Tachyons API key is missing.")
    return TachyonsClient(api_key=tachyons_api_key)

# Initialize Tachyons client
tachyons_client = initialize_tachyons_client()

# Endpoint to process Model Context Protocol (MCP)
@app.post("/process-context")
async def process_context(context: dict):
    try:
        dependency_graph = context.get("dependency_graph", {})
        vector_db_query = context.get("vector_db_query", "")
        jira_context = context.get("jira_context", [])  # Use Jira context directly from upstream

        # Process dependency graph
        relationships = dependency_graph.get("relationships", [])

        # Query Tachyons vector database
        vector_results = []
        if vector_db_query:
            vector_results = tachyons_client.query_vector_db(query=vector_db_query, top_k=5)

        # Combine context
        combined_context = {
            "dependency_graph": relationships,
            "vector_db_results": vector_results,
            "jira_context": jira_context
        }

        # Generate output using Tachyons
        prompt = """
        You are a QA engineer. Based on the following context, generate detailed BDD feature files in Gherkin syntax.

        Context:
        {context}

        Output:
        """
        response = tachyons_client.generate(
            model="tachyons-gpt-4",
            input=prompt.format(context=json.dumps(combined_context, indent=2))
        )
        return {"features": response["output"]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Root endpoint to check server status
@app.get("/")
async def root():
    return {"message": "Model Context Protocol (MCP) Server is running."}
