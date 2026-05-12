'''import os
import json
import uuid
import asyncio
from typing import TypedDict, Annotated, List
from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages
from langgraph.checkpoint.redis import RedisSaver
from config.logger import logger
from config import chroma_client, neo4j_manager, redis_client
from dotenv import load_dotenv
import datetime

load_dotenv()

# Define Graph State
class AgentState(TypedDict):
    query: str
    response: str
    metadata: dict
    messages: Annotated[List[BaseMessage], add_messages]

from config.circuit_breaker import llm_breaker, chroma_breaker, neo4j_breaker, with_breaker, llm_fallback, chroma_fallback, neo4j_fallback

# Graph Nodes
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
        return {"response": "The AI service is currently having trouble. Please try again later.", "messages": []}

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
        except Exception as e: 
            logger.error(f"❌ ChromaDB error: {str(e)}")
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
        except Exception as e: 
            logger.error(f"❌ Neo4j error: {str(e)}")
    return state

# Build Graph
workflow = StateGraph(AgentState)
workflow.add_node("agent", call_llm)
workflow.add_node("chroma", store_chroma)
workflow.add_node("neo4j", store_neo4j)
workflow.set_entry_point("agent")
workflow.add_edge("agent", "chroma")
workflow.add_edge("chroma", "neo4j")
workflow.add_edge("neo4j", END)

# Use Redis Checkpointer for persistence across workers
# Redis connection info from environment
redis_url = f"redis://{os.getenv('REDIS_HOST', 'localhost')}:{os.getenv('REDIS_PORT', 6379)}"
checkpointer = RedisSaver.from_conn_string(redis_url)
graph = workflow.compile(checkpointer=checkpointer)

from config import chroma_client, neo4j_manager, redis_client, async_redis_client

# ... (graph nodes remain the same) ...

async def worker():
    logger.info("🚀 Worker started. Listening for LLM tasks via Async Redis Pub/Sub...")
    pubsub = async_redis_client.pubsub()
    await pubsub.subscribe("llm_tasks")

    while True:
        try:
            message = await pubsub.get_message(ignore_subscribe_messages=True)
            if message:
                data = json.loads(message['data'])
                request_id = data['request_id']
                query = data['query']
                thread_id = data.get('thread_id', 'default_thread')

                logger.info(f"📥 Processing request {request_id}")
                
                config = {"configurable": {"thread_id": thread_id}}
                inputs = {"query": query}
                
                async for event in graph.astream(inputs, config=config, stream_mode="updates"):
                    for node, output in event.items():
                        chunk = {"type": "node", "node": node, "content": output.get("response", "Done")}
                        await async_redis_client.publish(f"response:{request_id}", json.dumps(chunk))
                
                await async_redis_client.publish(f"response:{request_id}", "[DONE]")
                logger.info(f"📤 Completed request {request_id}")
            
            await asyncio.sleep(0.1)  # Prevent CPU hogging
        except Exception as e:
            logger.error(f"Worker Error: {str(e)}")
            await asyncio.sleep(1)

if __name__ == "__main__":
    asyncio.run(worker())
'''