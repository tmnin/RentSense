from pydantic import BaseModel
from typing import List, Dict, Optional, Any

class ChatRequest(BaseModel):
    user_input: Optional[str] = None
    selected_options: Optional[List[str]] = None # For MCQ answers
    last_question_data: Optional[Dict[str, Any]] = None # To know which weights to update
    mode: str = "discovery"
    weights: Dict[str, float]
    conversation_history: List[Dict[str, Any]]
    questions_asked: int
    dimensions_covered: List[str]

class ChatResponse(BaseModel):
    weights: Dict[str, float]
    conversation_history: List[Dict[str, Any]]
    questions_asked: int
    dimensions_covered: List[str]
    next_step: str  # "ask_question" or "show_results"
    question: Optional[Dict[str, Any]] = None
    results: Optional[List[Dict[str, Any]]] = None