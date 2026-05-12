import os
import json
import uuid
import datetime
import asyncio
from typing import TypedDict, Annotated, List
from fastapi import FastAPI, Request, Form
from fastapi.templating import Jinja2Templates
from fastapi.responses import StreamingResponse
from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages
from langgraph.checkpoint.redis import RedisSaver
from config.logger import logger
from config import chroma_client, neo4j_manager, redis_client
from config.circuit_breaker import llm_breaker, chroma_breaker, neo4j_breaker, with_breaker, llm_fallback, chroma_fallback, neo4j_fallback
from dotenv import load_dotenv
from contextlib import asynccontextmanager

load_dotenv()

# --- Graph State and Nodes ---
class AgentState(TypedDict):
    query: str
    response: str
    metadata: dict
    messages: Annotated[List[BaseMessage], add_messages]

def call_llm(state: AgentState):
    try:
        @with_breaker(llm_breaker, llm_fallback)
        def get_llm_response():
            llm = ChatGroq(model="llama-3.3-70b-versatile")
            prompt = ChatPromptTemplate.from_messages([
                ("system", "You are a helpful assistant. Keep your answers very short, direct, and concise. Avoid all rich text formatting. Plain text only."),
                ("placeholder", "{messages}"),
                ("human", "{query}")
            ])
            chain = prompt | llm
            return chain.invoke({"query": state["query"], "messages": state.get("messages", [])})

        result = get_llm_response()
        logger.info("✅ Agent: LLM call completed successfully")
        logger.info("➡️ Passing to Edge: Agent -> ChromaDB | Successfully execution")
        
        return {
            "response": result.content,
            "messages": [HumanMessage(content=state["query"]), AIMessage(content=result.content)],
            "metadata": {"model": "llama-3.3-70b-versatile", "timestamp": str(datetime.datetime.now()), "user": "default_user"}
        }
    except Exception as e:
        logger.error(f"❌ Agent error: {str(e)}")
        return {"response": "The AI service is currently having trouble.", "messages": []}

def store_chroma(state: AgentState):
    if chroma_client:
        try:
            @with_breaker(chroma_breaker, chroma_fallback)
            def save_to_chroma():
                collection = chroma_client.get_or_create_collection(name="conversations")
                collection.add(
                    ids=[str(uuid.uuid4())],
                    documents=[f"User: {state['query']}\nAssistant: {state['response']}"],
                    metadatas=[{"query": state["query"], "response": state["response"], **state["metadata"]}]
                )
            save_to_chroma()
            logger.info("✅ ChromaDB: Stored successfully")
            logger.info("➡️ Passing to Edge: ChromaDB -> Neo4j | Successfully execution")
        except Exception as e: logger.error(f"❌ ChromaDB error: {str(e)}")
    return state

def store_neo4j(state: AgentState):
    driver = neo4j_manager.connect()
    if driver:
        try:
            @with_breaker(neo4j_breaker, neo4j_fallback)
            def save_to_neo4j():
                with driver.session() as session:
                    session.run("MERGE (u:User {id: $uid}) CREATE (q:Query {text: $q, ts: $ts})-[:GEN]->(r:Res {text: $r})", 
                        uid=state["metadata"]["user"], q=state["query"], r=state["response"], ts=state["metadata"]["timestamp"])
            save_to_neo4j()
            logger.info("✅ Neo4j: Stored successfully")
            logger.info("➡️ Passing to Edge: Neo4j -> END | Successfully execution")
        except Exception as e: logger.error(f"❌ Neo4j error: {str(e)}")
    return state

# --- Build and Compile Graph ---
workflow = StateGraph(AgentState)
workflow.add_node("agent", call_llm)
workflow.add_node("chroma", store_chroma)
workflow.add_node("neo4j", store_neo4j)
workflow.set_entry_point("agent")
workflow.add_edge("agent", "chroma")
workflow.add_edge("chroma", "neo4j")
workflow.add_edge("neo4j", END)

from langgraph.checkpoint.memory import MemorySaver

checkpointer = MemorySaver()
graph = workflow.compile(checkpointer=checkpointer)

# --- FastAPI App ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("FastAPI Gateway starting (Monolithic Mode)...")
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
    thread_id = str(uuid.uuid4()) # In a real app, this might come from the session
    logger.info(f"Received query: {query}")

    async def event_generator():
        config = {"configurable": {"thread_id": "shared_thread"}} # Using a shared thread for now
        inputs = {"query": query}
        
        try:
            async for event in graph.astream(inputs, config=config, stream_mode="updates"):
                for node, output in event.items():
                    chunk = {"type": "node", "node": node, "content": output.get("response", "Done")}
                    yield f"data: {json.dumps(chunk)}\n\n"
            
            yield "data: [DONE]\n\n"
        except Exception as e:
            logger.error(f"Error: {str(e)}")
            yield f"data: {json.dumps({'type': 'error', 'content': str(e)})}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app", 
        host="0.0.0.0", 
        port=8000, 
        reload=True,
        reload_includes=["main.py", "config/*.py", "templates/*.html"],
        reload_dirs=["config", "templates", "."],
        reload_excludes=["logs/*", "**/__pycache__/*", "*.log"]
    )
