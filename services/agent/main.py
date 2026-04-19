import os
import json
from typing import List, Optional, TypedDict
from pydantic import BaseModel, Field
from langgraph.graph import StateGraph, START, END
from langchain_groq import ChatGroq
from langchain_core.messages import SystemMessage, HumanMessage
import httpx
from langgraph.checkpoint.sqlite import SqliteSaver
import sqlite3
from dotenv import load_dotenv

load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
VECTOR_SERVICE_URL = os.getenv("VECTOR_SERVICE_URL", "http://127.0.0.1:8001")
HF_TOKEN = os.getenv("HF_TOKEN")

# Embeddings function for local use inside the agent if we need to embed the query
# Actually, the ingestion service does HF API embeddings. The Vector service `/query` takes `query_embeddings`.
# So the agent MUST embed the rewritten query before calling Vector service!
from langchain_huggingface import HuggingFaceEndpointEmbeddings
embeddings_model = HuggingFaceEndpointEmbeddings(
    model="sentence-transformers/all-MiniLM-L6-v2",
    task="feature-extraction",
    huggingfacehub_api_token=HF_TOKEN
)

llm = ChatGroq(model_name="llama-3.1-8b-instant", temperature=0)
critic_llm = ChatGroq(model_name="llama-3.3-70b-versatile", temperature=0) # use 70b for critic for better JSON compliance

# 1. State Definition
class SearchState(TypedDict):
    question: str
    collection_name: str
    
    rewritten_query: str
    intent: str
    documents: List[str]
    sources: List[str]
    generation: str
    confidence: float
    
    retry_count: int
    final_answer: Optional[str]

# 2. Nodes

class QueryAnalysisOutput(BaseModel):
    intent: str = Field(description="factual, comparative, or summarisation")
    rewritten_query: str = Field(description="Optimized query for semantic vector search")

def query_analyser(state: SearchState) -> SearchState:
    prompt = f"""You are a query analysis expert.
Classify the intent of the question (factual, comparative, or summarisation).
Rewrite the question to be optimal for semantic vector search. Do not include question marks, just include keywords and core concepts.

Question: {state['question']}
"""
    # Llama-3-8b struggles with native structural outputs sometimes but we'll use bind_tools or with_structured_output if possible.
    # We will use simple prompt.
    structured_llm = llm.with_structured_output(QueryAnalysisOutput)
    res = structured_llm.invoke(prompt)
    
    return {
        "intent": res.intent,
        "rewritten_query": res.rewritten_query,
        "retry_count": state.get("retry_count", 0)  # initialize if not present
    }

def retriever(state: SearchState) -> SearchState:
    query = state.get("rewritten_query", state["question"])
    
    print(f"Embedding query: {query}")
    query_emb = embeddings_model.embed_query(query)
    
    print("Fetching from Vector DB...")
    payload = {
        "collection_name": state["collection_name"],
        "query_embeddings": [query_emb],
        "n_results": 5
    }
    
    try:
        res = httpx.post(f"{VECTOR_SERVICE_URL}/query", json=payload)
        res.raise_for_status()
        data = res.json()
        documents = data.get("documents", [])
        metadatas = data.get("metadatas", [])
        
        # metadatas might contain sources
        sources = [m.get("source", "unknown") for m in metadatas] if metadatas else []
        
        return {
            "documents": documents,
            "sources": sources
        }
    except Exception as e:
        print("Vector API Error:", e)
        return {
            "documents": [],
            "sources": []
        }

def synthesiser(state: SearchState) -> SearchState:
    docs_context = "\n\n".join([f"[Source: {s}] {d}" for s, d in zip(state["sources"], state["documents"])])
    
    prompt = f"""You are a professional research assistant. Answer the question using ONLY the provided sources. 
Cite your sources in your answer using [Source: ...]. Do not hallucinate. If the answer is not in the sources, say "I cannot answer this based on the retrieved documents."

Question: {state['question']}

Sources:
{docs_context}
"""
    res = llm.invoke(prompt)
    
    return {"generation": res.content}

class CriticOutput(BaseModel):
    relevance: float = Field(description="Score between 0.0 and 1.0 representing how relevant the answer is")
    groundedness: float = Field(description="Score between 0.0 and 1.0 representing how well the answer is grounded in the sources")
    completeness: float = Field(description="Score between 0.0 and 1.0 representing how completely it answers the question")

def critic(state: SearchState) -> SearchState:
    prompt = f"""Evaluate this generated answer on 3 dimensions. Return a JSON structure.
Scores should be between 0.0 and 1.0.

Question: {state['question']}
Answer: {state['generation']}
Sources Provided: {state['documents']}
"""
    structured_critic = critic_llm.with_structured_output(CriticOutput)
    eval_res = structured_critic.invoke(prompt)
    
    relevance = eval_res.relevance
    groundedness = eval_res.groundedness
    completeness = eval_res.completeness
    
    avg_confidence = (relevance + groundedness + completeness) / 3.0
    print(f"Critic Confidence: {avg_confidence:.2f}")
    
    return {
        "confidence": avg_confidence,
        "retry_count": state["retry_count"] + 1,
        "final_answer": state["generation"] if avg_confidence >= 0.7 else None
    }

# 3. Graph Logic
def should_retry(state: SearchState) -> str:
    conf = state.get("confidence", 0.0)
    retries = state.get("retry_count", 0)
    
    if conf < 0.7 and retries < 3:
        print(f"Retrying... Confidence {conf:.2f} is too low. (Retry {retries}/3)")
        return "retriever"
    return "end"

def build_graph():
    workflow = StateGraph(SearchState)
    
    workflow.add_node("query_analyser", query_analyser)
    workflow.add_node("retriever", retriever)
    workflow.add_node("synthesiser", synthesiser)
    workflow.add_node("critic", critic)
    
    workflow.add_edge(START, "query_analyser")
    workflow.add_edge("query_analyser", "retriever")
    workflow.add_edge("retriever", "synthesiser")
    workflow.add_edge("synthesiser", "critic")
    
    workflow.add_conditional_edges("critic", should_retry, {"retriever": "retriever", "end": END})
    
    # Configure local sqlite persistent checkpointer
    conn = sqlite3.connect("agent_state.db", check_same_thread=False)
    saver = SqliteSaver(conn)
    app = workflow.compile(checkpointer=saver)
    return app

agent_app = build_graph()

def run_agent(question: str, collection: str, thread_id: str):
    config = {"configurable": {"thread_id": thread_id}}
    initial_state = {
        "question": question,
        "collection_name": collection,
        "retry_count": 0
    }
    
    print(f"--- Running Agent for: {question} ---")
    final_state = agent_app.invoke(initial_state, config=config)
    
    return {
        "answer": final_state.get("final_answer", final_state.get("generation")),
        "confidence": final_state.get("confidence"),
        "retries": final_state.get("retry_count")
    }

if __name__ == "__main__":
    # Test executing the agent standalone if run directly
    res = run_agent(
        question="What does SmartSearch optimize?",
        collection="test_collection",
        thread_id="test_thread_1"
    )
    print("\n--- Final Agent Output ---")
    print(json.dumps(res, indent=2))
