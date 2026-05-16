# 🚀 Stateful AI Evaluation Pipeline

A production-grade, stateful AI agent pipeline built with **LangGraph**, **FastAPI**, and a multi-database architecture (**Neo4j**, **ChromaDB**, **Redis**). This project implements a high-fidelity anti-hallucination workflow designed for enterprise-level reliability and observability.

---

## 🏗️ System Architecture

The application follows a specialized **Production Anti-Hallucination Pipeline**:

1.  **🔍 Query Rewriter**: Optimizes user input for precise Vector and Graph retrieval.
2.  **📚 Hybrid Retriever**: Parallelized data fetching from **ChromaDB** (Semantic) and **Neo4j** (Relational).
3.  **⚖️ Context Reranker**: Filters out noise to provide the LLM with only high-relevance information.
4.  **🤖 LLM Generator**: Produces answers strictly grounded in the verified context.
5.  **✅ Verifier Agent**: Automatically scores the "grounding" of the response to ensure accuracy.
6.  **🛡️ Guardrails**: Applies confidence checks and safety policies before final delivery.

---

## ✨ Key Features

- **Stateful Conversational Memory**: Powered by LangGraph's `MemorySaver` for persistent context across sessions.
- **Tool-Augmented Intelligence**: 
    - **Calculator**: For verified mathematical computations.
    - **Neo4j Tool**: Direct Knowledge Graph queries via Cypher.
    - **Web Search**: Real-time information fetching via **Tavily**.
- **Resilience Layer**: **Circuit Breaker** patterns implemented for Groq LLM, ChromaDB, and Neo4j.
- **Real-Time Streaming**: ChatGPT-style UI with Server-Sent Events (SSE) showing internal pipeline status.
- **Observability**: Seamless integration with **LangSmith** for full execution tracing.

---

## 🛠️ Tech Stack

- **Backend**: Python 3.10+, FastAPI
- **Orchestration**: LangGraph, LangChain
- **LLM**: Llama 3.3 70B & Llama 3 8B (via Groq)
- **Vector DB**: ChromaDB
- **Graph DB**: Neo4j (Aura DB)
- **Memory/Cache**: Redis
- **Monitoring**: LangSmith
- **Circuit Breaker**: PyBreaker

---

## ⚙️ Setup & Installation Guide

### 1. Clone the Repository
```bash
git clone <your-repo-url>
cd llm-evaluation
```

### 2. Automated Setup
The project includes a `setup.sh` script that handles pip upgrades and dependency installation:
```bash
chmod +x setup.sh
./setup.sh
```

### 3. Environment Configuration
Create a `.env` file in the root directory. Use the following template as a guide:

```env
# --- LLM Provider (Groq) ---
GROQ_API_KEY="your_groq_api_key_here"

# --- Search Tool (Tavily) ---
TAVILY_API_KEY="your_tavily_api_key_here"

# --- Vector Database (ChromaDB Cloud) ---
CHROMA_API_KEY="your_chroma_api_key"
CHROMA_TENANT="your_tenant_id"
CHROMA_DB_NAME="llm-evaluation"

# --- Graph Database (Neo4j Aura) ---
NEO4J_URI="neo4j+s://your-id.databases.neo4j.io"
NEO4J_USER="neo4j"
NEO4J_PASSWORD="your_neo4j_password"

# --- Cache & Pub/Sub (Redis) ---
REDIS_HOST="localhost"
REDIS_PORT=6379
REDIS_PASSWORD=""

# --- Observability (LangSmith) ---
LANGCHAIN_TRACING_V2=true
LANGCHAIN_ENDPOINT="https://api.smith.langchain.com"
LANGCHAIN_API_KEY="your_langsmith_api_key"
LANGCHAIN_PROJECT="llm-evaluation-pipeline"
```

---

## 🚀 Running the Application

To launch the entire pipeline (including the FastAPI gateway and internal LangGraph logic), simply run:

```bash
chmod +x run.sh
./run.sh
```

The application will be available at: **`http://localhost:8000`**

---

## 🔍 Anti-Hallucination & Guardrails

The system is designed to be "Grounded by Default." 
- Every response is cross-referenced with retrieved context in the **Verifier Agent** node.
- A **Grounding Score** is calculated. 
- The **Guardrails** node enforces a threshold (default: **0.6**). 
- If the score is low, the system provides a safe refusal message: *"I cannot answer this as it may contain hallucinated information."*

## 🛡️ Resilience (Circuit Breakers)
The system monitors the health of external services. If Neo4j, ChromaDB, or Groq becomes unresponsive, the **Circuit Breaker** will open, preventing system-wide crashes and returning a controlled fallback response.

---

## 🤝 Contributing
Feel free to open issues or submit pull requests to improve the pipeline logic or UI.
