# app/api/v1/chat.py (Updated to return sources)

from fastapi import APIRouter
from pydantic import BaseModel, Field
from typing import List, Dict, Any

# Import our compiled graph
from app.agent.graph import rag_graph

# Define the API router
router = APIRouter()

# --- Pydantic Models ---
class ChatRequest(BaseModel):
    question: str

# Our response will now include the answer and a list of source documents
class Source(BaseModel):
    source: str = Field(description="The filename of the source document.")
    page: Any = Field(description="The page number of the source document, if available.")

class ChatResponse(BaseModel):
    answer: str
    sources: List[Source]


# --- Primary Chat Endpoint (Updated) ---
@router.post("/chat", summary="Chat with the agent")
async def chat_with_agent(request: ChatRequest) -> ChatResponse:
    """
    This endpoint takes a user's question, runs it through the RAG agent,
    and returns the final answer along with the source documents used.
    """
    print("--- CHAT ENDPOINT: Waiting for full response... ---")
    
    final_result = rag_graph.invoke({"question": request.question})
    
    print("--- CHAT ENDPOINT: Full response received. ---")

    # Extract the context documents and format them for the response
    source_documents = []
    if final_result.get("context"):
        for doc in final_result["context"]:
            # Ensure metadata and source exist before trying to access them
            if doc.metadata and 'source' in doc.metadata:
                source_documents.append(
                    Source(
                        source=doc.metadata.get('source', 'Unknown'),
                        page=doc.metadata.get('page_number', 'N/A')
                    )
                )
    
    return ChatResponse(
        answer=final_result.get("answer", "No answer found."),
        sources=source_documents
    )