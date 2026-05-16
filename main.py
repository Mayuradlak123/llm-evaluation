import os
import json
import uuid
import datetime
import asyncio
from typing import TypedDict, Annotated, List, Optional
from fastapi import FastAPI, Request, Form
from fastapi.templating import Jinja2Templates
from fastapi.responses import StreamingResponse
from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, ToolMessage
from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages
from langgraph.checkpoint.memory import MemorySaver
from langgraph.prebuilt import ToolNode
from config.logger import logger
from config import chroma_client, neo4j_manager, redis_client
from config.circuit_breaker import llm_breaker, chroma_breaker, neo4j_breaker, with_breaker, llm_fallback, chroma_fallback, neo4j_fallback
from tools import tools
from dotenv import load_dotenv
from contextlib import asynccontextmanager

load_dotenv()

# --- Graph State ---
class AgentState(TypedDict):
    original_query: str
    rewritten_query: str
    context: List[str]
    raw_response: str
    final_response: str
    verification_score: float
    is_safe: bool
    confidence_score: float
    messages: Annotated[List[BaseMessage], add_messages]

# --- Production Nodes ---

def query_rewriter(state: AgentState):
    """Rewrite the user query for better retrieval performance using a high-speed model."""
    logger.info("🔍 Rewriting query (High-speed model)...")
    llm = ChatGroq(model="llama-3.3-70b-versatile")
    prompt = ChatPromptTemplate.from_messages([
        ("system", "Rewrite the user query for Vector/Graph search. Output ONLY the query."),
        ("human", "{query}")
    ])
    chain = prompt | llm
    result = chain.invoke({"query": state["original_query"]})
    return {"rewritten_query": result.content}

async def context_retriever(state: AgentState):
    """Retrieve context from ChromaDB and Neo4j in parallel."""
    logger.info("📚 Retrieving context in parallel...")
    query = state["rewritten_query"]
    
    async def get_chroma():
        if not chroma_client: return []
        try:
            collection = chroma_client.get_or_create_collection(name="conversations")
            results = collection.query(query_texts=[query], n_results=3)
            return results['documents'][0] if results['documents'] else []
        except: return []

    async def get_neo4j():
        driver = neo4j_manager.connect()
        if not driver: return []
        try:
            with driver.session() as session:
                cypher = "MATCH (q:Query)-[:GEN]->(r:Res) WHERE q.text CONTAINS $q OR r.text CONTAINS $q RETURN r.text LIMIT 2"
                res = session.run(cypher, q=query)
                return [record["r.text"] for record in res]
        except: return []

    # Parallelize I/O
    results = await asyncio.gather(get_chroma(), get_neo4j())
    flat_results = [item for sublist in results for item in sublist]
    return {"context": flat_results}

def context_reranker(state: AgentState):
    """Rerank chunks using a high-speed model."""
    if not state["context"]: return {"context": []}
    llm = ChatGroq(model="llama-3.3-70b-versatile")
    prompt = ChatPromptTemplate.from_messages([
        ("system", "Rank context by relevance. Output top 3 chunks separated by '---'."),
        ("human", "Query: {query}\nChunks:\n{chunks}")
    ])
    chain = prompt | llm
    result = chain.invoke({"query": state["rewritten_query"], "chunks": "\n".join(state["context"])})
    reranked = [c.strip() for c in result.content.split('---') if c.strip()]
    return {"context": reranked}

def llm_generator(state: AgentState):
    """Generate final response using the high-quality model."""
    logger.info("🤖 Generating response (High-quality model)...")
    llm = ChatGroq(model="llama-3.3-70b-versatile")
    context_text = "\n".join(state["context"])
    prompt = ChatPromptTemplate.from_messages([
        ("system", "Use the following context to answer. Plain text only. Context:\n{context}"),
        ("human", "{query}")
    ])
    chain = prompt | llm
    result = chain.invoke({"query": state["original_query"], "context": context_text})
    return {"raw_response": result.content}

def verifier_agent(state: AgentState):
    """Verify grounding using a high-speed model."""
    llm = ChatGroq(model="llama-3.3-70b-versatile")
    prompt = ChatPromptTemplate.from_messages([
        ("system", "Score response grounding against context (0.0 to 1.0). Output ONLY the number."),
        ("human", "Context: {context}\nResponse: {response}")
    ])
    chain = prompt | llm
    try: score = float(chain.invoke({"context": "\n".join(state["context"]), "response": state["raw_response"]}).content.strip())
    except: score = 0.5
    return {"verification_score": score}

def guardrails_node(state: AgentState):
    """Apply safety and scope guardrails."""
    logger.info("🛡️ Applying guardrails...")
    # Simple logic: if score is too low or response is dangerous
    is_safe = state["verification_score"] > 0.6
    final_resp = state["raw_response"] if is_safe else "I cannot answer this as it may contain hallucinated information."
    return {"is_safe": is_safe, "final_response": final_resp, "confidence_score": state["verification_score"]}

# --- Build the Production Graph ---

workflow = StateGraph(AgentState)

workflow.add_node("rewriter", query_rewriter)
workflow.add_node("retriever", context_retriever)
workflow.add_node("reranker", context_reranker)
workflow.add_node("generator", llm_generator)
workflow.add_node("verifier", verifier_agent)
workflow.add_node("guardrails", guardrails_node)

workflow.set_entry_point("rewriter")
workflow.add_edge("rewriter", "retriever")
workflow.add_edge("retriever", "reranker")
workflow.add_edge("reranker", "generator")
workflow.add_edge("generator", "verifier")
workflow.add_edge("verifier", "guardrails")
workflow.add_edge("guardrails", END)

checkpointer = MemorySaver()
graph = workflow.compile(checkpointer=checkpointer)

# --- FastAPI App ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("FastAPI Gateway starting (Production Pipeline Mode)...")
    yield
    if redis_client: redis_client.close()
    neo4j_manager.close()
    logger.info("✅ Connections closed")

app = FastAPI(lifespan=lifespan)
templates = Jinja2Templates(directory="templates")

@app.get("/")
async def read_item(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.post("/query")
async def handle_query(request: Request, query: str = Form(...)):
    logger.info(f"Received query: {query}")

    async def event_generator():
        config = {"configurable": {"thread_id": "shared_thread"}}
        inputs = {"original_query": query}
        
        try:
            async for event in graph.astream(inputs, config=config, stream_mode="updates"):
                for node, output in event.items():
                    # Handle node specific output for UI streaming
                    content = ""
                    if node == "rewriter": content = f"🔍 Optimized Query: {output['rewritten_query']}"
                    elif node == "retriever": content = "📚 Context retrieved from DBs..."
                    elif node == "reranker": content = "⚖️ Context ranked for accuracy..."
                    elif node == "generator": content = output['raw_response']
                    elif node == "verifier": content = f"✅ Grounding Score: {output['verification_score']}"
                    elif node == "guardrails": content = output['final_response']
                    
                    if content:
                        chunk = {"type": "node", "node": node, "content": content}
                        yield f"data: {json.dumps(chunk)}\n\n"
            
            yield "data: [DONE]\n\n"
        except Exception as e:
            logger.error(f"Error: {str(e)}")
            yield f"data: {json.dumps({'type': 'error', 'content': str(e)})}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
