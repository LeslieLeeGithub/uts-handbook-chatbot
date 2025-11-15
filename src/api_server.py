#!/usr/bin/env python3
"""
FastAPI backend server for Handbook Chatbot
Connects the RAG query functions to the frontend

IMPORTANT: This server should run in the 'stormai' conda environment (or your Handbook environment)
where all the RAG dependencies (sentence-transformers, qdrant-client, ollama) are installed.
"""

import sys
import os
import re
from pathlib import Path

# Add the rag directory to the path so we can import query functions
HANDBOOK_ROOT = Path(os.environ.get('HANDBOOK_ROOT', Path(__file__).parent.parent))
RAG_DIR = HANDBOOK_ROOT / "src" / "rag"
sys.path.insert(0, str(RAG_DIR))

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List, Dict
import traceback

# Import the query functions
try:
    from query_hybrid_rag import query_courses
    from query_with_preprocessing import query_with_full_pipeline
    print("✅ Successfully imported RAG query functions")
except ImportError as e:
    print(f"❌ Warning: Could not import query functions: {e}")
    print("Make sure you're running in the correct conda environment")
    print("Required packages: sentence-transformers, qdrant-client, ollama, etc.")
    raise

app = FastAPI(title="Handbook Chatbot API", version="1.0.0")

# CORS middleware - allow frontend to connect
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:8080",
        "http://localhost:3000",
        "http://127.0.0.1:8080",
        "http://127.0.0.1:3000",
        "http://0.0.0.0:8080",
        "*"  # Allow all origins for development
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

# Default configuration - use environment variables or relative paths
DEFAULT_EMBED_DIR = os.environ.get('HANDBOOK_EMBED_DIR', str(HANDBOOK_ROOT / "models" / "hf" / "qwen3-embedding-0.6b"))
DEFAULT_COLLECTION = os.environ.get('HANDBOOK_DEFAULT_COLLECTION', "courses")
DEFAULT_K = int(os.environ.get('HANDBOOK_K', 30))
DEFAULT_TOPN = int(os.environ.get('HANDBOOK_TOPN', 8))
DEFAULT_MODEL = os.environ.get('HANDBOOK_MODEL', "qwen2.5:7b")


def extract_course_code_from_text(text: str) -> Optional[str]:
    """
    Extract UTS course code from text.
    UTS course codes follow the pattern: C followed by 5 digits (e.g., C04379, C10302)
    
    Args:
        text: Input text that may contain a course code
        
    Returns:
        Course code in uppercase (e.g., "C04379") or None if not found
    """
    # Pattern: C followed by exactly 5 digits
    # Case-insensitive, word boundaries to avoid matching partial codes
    pattern = r'\b[Cc]\d{5}\b'
    matches = re.findall(pattern, text)
    
    if matches:
        # Return the first match in uppercase
        code = matches[0].upper()
        print(f"  🔍 Extracted course code from message: {code}")
        return code
    
    return None


# Request/Response models
class ChatRequest(BaseModel):
    message: str
    course_code: Optional[str] = None
    course_name: Optional[str] = None
    history: Optional[List[Dict]] = None
    concise: Optional[bool] = True
    use_preprocessing: Optional[bool] = True


class ChatResponse(BaseModel):
    response: str
    success: bool
    error: Optional[str] = None


@app.get("/")
async def root():
    """Health check endpoint"""
    return {
        "status": "ok",
        "service": "Handbook Chatbot API",
        "version": "1.0.0",
        "environment": os.environ.get("CONDA_DEFAULT_ENV", "unknown")
    }


@app.get("/health")
async def health():
    """Health check endpoint"""
    return {"status": "healthy"}


@app.get("/api/chatbot/courses/")
async def get_courses():
    """
    Get list of available courses from Qdrant collection
    
    Returns:
        List of course codes and names available in the knowledge base
    """
    try:
        from qdrant_client import QdrantClient
        
        # Connect to Qdrant
        cli = QdrantClient(host="localhost", port=6333)
        
        # Check if courses collection exists
        if not cli.collection_exists(DEFAULT_COLLECTION):
            return {
                "courses": [],
                "success": False,
                "error": f"Collection '{DEFAULT_COLLECTION}' not found"
            }
        
        # Get sample points to extract unique course codes
        # We'll use scroll to get a sample of points
        try:
            points, _ = cli.scroll(
                collection_name=DEFAULT_COLLECTION,
                limit=1000,  # Get up to 1000 points
                with_payload=True
            )
            
            # Extract unique course codes and names
            courses_dict = {}
            for point in points:
                payload = point.payload or {}
                course_code = payload.get("course_code")
                course_name = payload.get("course_name")
                
                if course_code and course_code not in courses_dict:
                    courses_dict[course_code] = course_name or ""
            
            # Convert to list of dicts
            courses = [
                {"code": code, "name": name}
                for code, name in sorted(courses_dict.items())
            ]
            
            print(f"Found {len(courses)} unique courses")
            
            return {
                "courses": courses,
                "success": True
            }
        except Exception as e:
            print(f"Error scrolling collection: {e}")
            return {
                "courses": [],
                "success": False,
                "error": str(e)
            }
    except Exception as e:
        print(f"Error getting courses: {e}")
        traceback.print_exc()
        return {
            "courses": [],
            "success": False,
            "error": str(e)
        }


@app.post("/api/chatbot/chat/", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    Main chat endpoint - processes user messages using RAG pipeline
    
    Args:
        request: ChatRequest with message, course_code/course_name (optional), and other parameters
        
    Returns:
        ChatResponse with bot's response
    """
    try:
        print(f"\n{'='*70}")
        print(f"Received chat request:")
        print(f"  Message: {request.message}")
        print(f"  Course Code (provided): {request.course_code}")
        print(f"  Course Name: {request.course_name}")
        print(f"  Concise: {request.concise}")
        print(f"  Use preprocessing: {request.use_preprocessing}")
        if request.history:
            print(f"  History: {len(request.history)} previous messages")
        print(f"{'='*70}\n")
        
        # Extract query
        query = request.message.strip()
        
        if not query:
            raise HTTPException(status_code=400, detail="Message cannot be empty")
        
        # Extract course code from message if not provided explicitly
        extracted_course_code = None
        if not request.course_code:
            extracted_course_code = extract_course_code_from_text(query)
            # Also check conversation history for course codes
            if not extracted_course_code and request.history:
                for msg in request.history:
                    if msg.get("type") == "user":
                        extracted_course_code = extract_course_code_from_text(msg.get("text", ""))
                        if extracted_course_code:
                            break
        
        # Use extracted course code if available, otherwise use provided one
        final_course_code = request.course_code or extracted_course_code
        if final_course_code:
            if extracted_course_code and not request.course_code:
                print(f"  ✅ Using extracted course code: {final_course_code}")
            else:
                print(f"  ✅ Using provided course code: {final_course_code}")
        else:
            print(f"  ℹ️  No course code specified (will search all courses)")
        
        # Convert history format from frontend to backend format
        conversation_history = []
        if request.history:
            for msg in request.history:
                # Convert frontend format {type: "user"/"bot", text: "..."} to backend format
                conversation_history.append({
                    "type": msg.get("type", "user"),  # "user" or "bot"
                    "text": msg.get("text", "")
                })
            print(f"Converted {len(conversation_history)} messages from conversation history")
        
        # Use preprocessing pipeline if requested (default)
        if request.use_preprocessing:
            try:
                response_text = query_with_full_pipeline(
                    query=query,
                    embed_dir=DEFAULT_EMBED_DIR,
                    collection=DEFAULT_COLLECTION,
                    course_code=final_course_code,
                    course_name=request.course_name,
                    generate=True,
                    topn=DEFAULT_TOPN,
                    model=DEFAULT_MODEL,
                    concise=request.concise if request.concise is not None else True
                )
            except Exception as e:
                print(f"Error in preprocessing pipeline: {e}")
                traceback.print_exc()
                # Fallback to hybrid RAG
                response_text = query_courses(
                    query=query,
                    embed_dir=DEFAULT_EMBED_DIR,
                    collection=DEFAULT_COLLECTION,
                    course_code=final_course_code,
                    course_name=request.course_name,
                    k=DEFAULT_K,
                    topn=DEFAULT_TOPN,
                    generate=True,
                    concise=request.concise if request.concise is not None else True
                )
        else:
            # Use hybrid RAG directly
            response_text = query_courses(
                query=query,
                embed_dir=DEFAULT_EMBED_DIR,
                collection=DEFAULT_COLLECTION,
                course_code=final_course_code,
                course_name=request.course_name,
                k=DEFAULT_K,
                topn=DEFAULT_TOPN,
                generate=True,
                concise=request.concise if request.concise is not None else True
            )
        
        if not response_text or response_text.strip() == "":
            response_text = "I couldn't generate a response. Please try rephrasing your question."
        
        print(f"\n{'='*70}")
        print(f"Response generated successfully")
        print(f"{'='*70}\n")
        
        return ChatResponse(
            response=response_text,
            success=True
        )
        
    except HTTPException:
        raise
    except Exception as e:
        error_msg = str(e)
        print(f"\n{'='*70}")
        print(f"Error processing chat request:")
        print(f"  Error: {error_msg}")
        print(f"{'='*70}\n")
        traceback.print_exc()
        
        return ChatResponse(
            response="Sorry, there was an error processing your request. Please try again.",
            success=False,
            error=error_msg
        )


@app.post("/api/chatbot/test/")
async def test_chat():
    """Test endpoint to verify the API is working"""
    test_request = ChatRequest(
        message="What courses are available?",
        concise=True
    )
    return await chat(test_request)


if __name__ == "__main__":
    import uvicorn
    
    # Check if we're in the right environment
    conda_env = os.environ.get("CONDA_DEFAULT_ENV", "")
    if not conda_env:
        print("⚠️  Warning: No conda environment detected")
        print("   Make sure you have the required packages installed")
        print()
    
    # Run the server
    print("Starting Handbook Chatbot API server...")
    print(f"API will be available at: http://localhost:8000")
    print(f"API docs available at: http://localhost:8000/docs")
    print("\nMake sure Qdrant and Ollama are running!")
    print("  Qdrant: http://127.0.0.1:6333")
    print("  Ollama: http://127.0.0.1:11434\n")
    
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        log_level="info"
    )
