import os
from langchain_core.tools import tool
from config.neo4j_config import neo4j_manager
from config.logger import logger
from tavily import TavilyClient

@tool
def calculator(expression: str) -> str:
    """Calculates a mathematical expression. Input should be a valid python math expression string like '2 + 2'."""
    try:
        # Using eval safely for simple math
        result = eval(expression, {"__builtins__": None}, {})
        return str(result)
    except Exception as e:
        return f"Error: {str(e)}"

@tool
def neo4j_query_tool(query: str) -> str:
    """Executes a Cypher query on the Neo4j graph database to retrieve information about entities and relationships."""
    driver = neo4j_manager.connect()
    if not driver:
        return "Error: Could not connect to Neo4j"
    try:
        with driver.session() as session:
            result = session.run(query)
            data = [record.data() for record in result]
            return str(data)
    except Exception as e:
        return f"Neo4j Error: {str(e)}"

@tool
def web_search_tool(query: str) -> str:
    """Searches the internet for information when you need up-to-date facts or details outside your training data."""
    api_key = os.getenv("TAVILY_API_KEY")
    if not api_key:
        return "Error: TAVILY_API_KEY not found in environment"
    try:
        tavily = TavilyClient(api_key=api_key)
        response = tavily.search(query=query, search_depth="basic")
        return str(response)
    except Exception as e:
        return f"Search Error: {str(e)}"

# Export tools
tools = [calculator, neo4j_query_tool, web_search_tool]
