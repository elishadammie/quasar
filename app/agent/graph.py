# app/agent/graph.py (Phase 4 - With Query Transformation)

from typing import List, Literal
import httpx

from langchain_core.documents import Document
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.pydantic_v1 import BaseModel, Field
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_community.vectorstores.pgvector import PGVector
from langgraph.graph import StateGraph, END
from typing import TypedDict

from app.core.config import settings

# --- Shared Components ---
insecure_client = httpx.Client(verify=False)
llm_args = {"temperature": 0, "openai_api_key": settings.OPENAI_API_KEY, "http_client": insecure_client}

# --- 1. DEFINE THE STATE ---
class GraphState(TypedDict):
    question: str
    context: List[Document]
    answer: str
    route: str
    relevance: str

# --- 2. DEFINE ROUTING AND EVALUATION TOOLS ---
class GradeDocuments(BaseModel):
    decision: Literal["relevant", "irrelevant"]


# This is new: A Pydantic model for our query transformer's output
class GeneratedQueries(BaseModel):
    """A list of rewritten queries for better retrieval."""
    queries: List[str] = Field(description="A list of 3 search queries generated from the user's question.")


class RouteQuery(BaseModel):
    """Route a user query to the most appropriate tool."""
    route: Literal["vectorstore", "conversational"]

# This is our improved prompt with examples (few-shot prompting)
router_prompt_template = """You are an expert at routing a user question to a vectorstore or to a conversational agent.
A 'vectorstore' question is one that requires looking up information from a knowledge base.
A 'conversational' question is a simple greeting, a thank you, or a question about the AI itself.

For example:
- User question: 'Hi there', route: 'conversational'
- User question: 'thanks!', route: 'conversational'
- User question: 'What is the main purpose of the ADRD model?', route: 'vectorstore'
- User question: 'Summarize the document.', route: 'vectorstore'

Route the following user question.

User question: {question}
"""
router_prompt = ChatPromptTemplate.from_template(router_prompt_template)


# --- 3. DEFINE LLM CHAINS ---
# Router Chain
# We bind the structured output and the new prompt to the LLM
routing_llm = ChatOpenAI(
    model="gpt-4o", 
    temperature=0, 
    openai_api_key=settings.OPENAI_API_KEY, 
    http_client=insecure_client
).with_structured_output(RouteQuery)

# The router chain now uses the more detailed prompt
router_chain = router_prompt | routing_llm

def query_router(state: GraphState):
    """
    This node will be the new entry point. It decides which path to take.
    """
    print("---NODE: QUERY ROUTER---")
    question = state["question"]
    # We now invoke the chain which includes the detailed prompt
    route_decision = router_chain.invoke({"question": question})
    
    print(f"Router decision: '{route_decision.route}'")
    return {"route": route_decision.route}


# Query Transformer Chain (New)
query_transformer_llm = ChatOpenAI(model="gpt-4o", **llm_args).with_structured_output(GeneratedQueries)
query_transformer_prompt_template = """You are an expert at crafting search queries.
Your task is to take a user's question and generate a list of 3 search queries that are optimized for a vector database.
The queries should be different from each other and cover different aspects or phrasings of the original question.

Original Question: {question}
"""
query_transformer_prompt = ChatPromptTemplate.from_template(query_transformer_prompt_template)
query_transformer_chain = query_transformer_prompt | query_transformer_llm

# Content Evaluator Chain
evaluator_llm = ChatOpenAI(model="gpt-4o", **llm_args).with_structured_output(GradeDocuments)
evaluator_prompt_template = "You are a grader assessing the relevance of a retrieved context to a user question...\nHere is the retrieved context:\n{context}\n\nHere is the user question:\n{question}\n\nGrade the relevance..."
evaluator_prompt = ChatPromptTemplate.from_template(evaluator_prompt_template)
evaluator_chain = evaluator_prompt | evaluator_llm
def content_evaluator(state: GraphState):
    print("---NODE: CONTENT EVALUATOR---")
    question = state["question"]
    context = state["context"]
    relevance_decision = evaluator_chain.invoke({"question": question, "context": context})
    print(f"Evaluator decision: '{relevance_decision.decision}'")
    return {"relevance": relevance_decision.decision}

# RAG Generation Chain
# rag_prompt_template = "You are an assistant for question-answering tasks...\nQuestion: {question}\nContext: {context}\nAnswer:"
rag_prompt_template = """You are an assistant for question-answering tasks.
Use the following pieces of retrieved context to answer the question.
Each piece of context is prefixed with its source number (e.g., [SOURCE 1], [SOURCE 2], ...).
When you use information from a specific source, you MUST cite it in your answer by including the corresponding source number (e.g., [1], [2]).

If you don't know the answer, just say that you don't know.
Use three sentences maximum and keep the answer concise.

Question: {question}
Context:
{context}

Answer (with citations):
"""

rag_prompt = ChatPromptTemplate.from_template(rag_prompt_template)
rag_llm = ChatOpenAI(model="gpt-4o", **llm_args)
rag_chain = rag_prompt | rag_llm | StrOutputParser()
def generate_answer(state: GraphState):
    print("---NODE: GENERATING ANSWER---")
    question = state["question"]
    context = state["context"]
    answer = rag_chain.invoke({"question": question, "context": context})
    return {"answer": answer}

# --- 4. DEFINE RAG PIPELINE NODES ---
embeddings = OpenAIEmbeddings(model="text-embedding-3-large", openai_api_key=settings.OPENAI_API_KEY, http_client=insecure_client)
vector_store = PGVector(connection_string=settings.DATABASE_URL, embedding_function=embeddings, collection_name="quasar_doc_collection")
retriever = vector_store.as_retriever()

# This is our new, adaptive retriever function
def retrieve_context(state: GraphState):
    """
    This node now transforms the query and then retrieves documents.
    """
    print("---NODE: ADAPTIVE RETRIEVAL---")
    question = state["question"]
    
    # 1. Transform the query
    print("Transforming query...")
    generated_queries = query_transformer_chain.invoke({"question": question})
    all_queries = [question] + generated_queries.queries
    print(f"Generated queries for retrieval: {all_queries}")
    
    # 2. Retrieve documents for all queries
    all_retrieved_docs = []
    for q in all_queries:
        docs = retriever.invoke(q)
        all_retrieved_docs.extend(docs)
        
    # 3. De-duplicate the results
    unique_docs = {doc.page_content: doc for doc in all_retrieved_docs}.values()
    print(f"Retrieved {len(unique_docs)} unique documents.")
    
    return {"context": list(unique_docs)}

# Conversational Node
conversational_llm = ChatOpenAI(model="gpt-4o", temperature=0.7, openai_api_key=settings.OPENAI_API_KEY, http_client=insecure_client)
def conversational_agent(state: GraphState):
    print("---NODE: CONVERSATIONAL AGENT---")
    answer = conversational_llm.invoke(state["question"])
    return {"answer": answer.content}

# Clarification Node
def clarification_node(state: GraphState):
    print("---NODE: CLARIFICATION / FAILURE---")
    message = "I'm sorry, but I could not find any documents in my knowledge base that are relevant to your question."
    return {"answer": message}

# --- 5. BUILD THE GRAPH ---
def decide_query_route(state: GraphState):
    return state["route"]

def decide_relevance(state: GraphState):
    return state["relevance"]

print("---BUILDING THE FULL AGENTIC GRAPH---")
workflow = StateGraph(GraphState)

workflow.add_node("router", query_router)
workflow.add_node("retrieve", retrieve_context)
workflow.add_node("content_evaluator", content_evaluator)
workflow.add_node("generate", generate_answer)
workflow.add_node("conversational_agent", conversational_agent)
workflow.add_node("clarification_node", clarification_node)

workflow.set_entry_point("router")
workflow.add_conditional_edges("router", decide_query_route, {"vectorstore": "retrieve", "conversational": "conversational_agent"})
workflow.add_edge("retrieve", "content_evaluator")
workflow.add_conditional_edges("content_evaluator", decide_relevance, {"relevant": "generate", "irrelevant": "clarification_node"})
workflow.add_edge("generate", END)
workflow.add_edge("conversational_agent", END)
workflow.add_edge("clarification_node", END)

rag_graph = workflow.compile()
print("---AGENTIC GRAPH COMPILED---")