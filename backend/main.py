from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import pandas as pd
from models import ChatRequest, ChatResponse
import engine

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # For dev; narrow this down for production!
    allow_methods=["*"],
    allow_headers=["*"],
)

# Load data once
df = pd.read_csv("nta_scores_all.csv")

# Map string answers to weight deltas
ANSWER_WEIGHTS = {
    "Very Important": 0.5,
    "Important": 0.25,
    "Neutral": 0.0,
    "Not Important": -0.25,
    "Not Applicable": 0.0
}

# Map question keywords to dimensions
def detect_dimension_from_question(question: str) -> str:
    """Detect which dimension a question is about based on keywords."""
    question_lower = question.lower()
    
    if any(word in question_lower for word in ["commute", "transit", "subway", "transportation", "travel"]):
        return "Commute Convenience"
    elif any(word in question_lower for word in ["safe", "safety", "crime", "secure"]):
        return "Safety"
    elif any(word in question_lower for word in ["quiet", "noise", "peaceful", "calm"]):
        return "Noise"
    elif any(word in question_lower for word in ["restaurant", "shop", "store", "amenit", "convenience", "dining"]):
        return "Amenity Convenience"
    elif any(word in question_lower for word in ["park", "green", "nature", "outdoor", "garden"]):
        return "Green Space Accessibility"
    elif any(word in question_lower for word in ["job", "work", "career", "employment", "business"]):
        return "Job Opportunities"
    elif any(word in question_lower for word in ["school", "education", "learning", "college", "university"]):
        return "Education Access"
    elif any(word in question_lower for word in ["politic", "voting", "liberal", "conservative"]):
        return "Political Leaning"
    
    return None

@app.post("/api/chat", response_model=ChatResponse)
async def chat_endpoint(req: ChatRequest):
    current_weights = req.weights.copy()
    history = req.conversation_history.copy()
    dims_covered = set(req.dimensions_covered)

    # 1. Handle Answer to Previous Question
    if req.selected_options and req.last_question_data:
        question_text = req.last_question_data.get("question", "")
        target_dim = req.last_question_data.get("dimension")
        
        # If no dimension provided, detect from question text
        if not target_dim:
            target_dim = detect_dimension_from_question(question_text)
        
        if target_dim:
            options = req.last_question_data.get("options", [])
            
            for selected in req.selected_options:
                # Handle string options (e.g., "Very Important")
                if isinstance(selected, str):
                    weight_delta = ANSWER_WEIGHTS.get(selected, 0.0)
                    current_weights[target_dim] = current_weights.get(target_dim, 1.0) + weight_delta
                    dims_covered.add(target_dim)
                # Handle object options with id/weight_delta
                elif isinstance(selected, dict):
                    weight_delta = selected.get("weight_delta", 0.0)
                    current_weights[target_dim] = current_weights.get(target_dim, 1.0) + weight_delta
                    dims_covered.add(target_dim)
                # Handle when options are objects and selected is an id
                else:
                    for opt in options:
                        if isinstance(opt, dict) and opt.get("id") == selected:
                            weight_delta = opt.get("weight_delta", 0.0)
                            current_weights[target_dim] = current_weights.get(target_dim, 1.0) + weight_delta
                            dims_covered.add(target_dim)

            history.append({"role": "user", "content": f"Selected: {', '.join(req.selected_options)}"})

    # 2. Analyze Initial Input
    elif req.user_input:
        prompt = f"Analyze: '{req.user_input}' for these dimensions: {engine.UI_DIMENSIONS}. Return JSON with 'clear' weight deltas (0 to 2.0)."
        analysis = engine.call_gemini(prompt)
        history.append({"role": "user", "content": req.user_input})
        
        # Apply deltas from initial analysis
        if "clear" in analysis:
            for dim, info in analysis["clear"].items():
                if dim in current_weights:
                    current_weights[dim] += info.get("weight_delta", 0)
                    dims_covered.add(dim)

    # ALWAYS Normalize weights before moving forward
    current_weights = engine.normalize_weights(current_weights)

    # 3. Decision: Should we show results?
    if req.questions_asked >= 4 or len(dims_covered) >= 7:
        results = engine.get_top_neighborhoods(df, current_weights, top_n=10)
        return ChatResponse(
            weights=current_weights,
            conversation_history=history,
            questions_asked=req.questions_asked,
            dimensions_covered=list(dims_covered),
            next_step="show_results",
            results=results
        )

    # 4. Generate Next Question
    remaining_dims = [d for d in engine.UI_DIMENSIONS if d not in dims_covered]
    q_prompt = f"""Based on conversation history: {history}
    
Ask a question about one of these dimensions that hasn't been covered yet: {remaining_dims}

Return JSON in this exact format:
{{
    "dimension": "<dimension name from the list>",
    "question": "<your question>",
    "options": ["Very Important", "Important", "Neutral", "Not Important", "Not Applicable"]
}}"""
    
    question_data = engine.call_gemini(q_prompt)
    
    if question_data and "question" in question_data:
        # Ensure dimension is set
        if "dimension" not in question_data and remaining_dims:
            question_data["dimension"] = detect_dimension_from_question(question_data["question"]) or remaining_dims[0]
        
        # Ensure options exist
        if "options" not in question_data:
            question_data["options"] = ["Very Important", "Important", "Neutral", "Not Important", "Not Applicable"]
        
        history.append({"role": "assistant", "content": question_data["question"]})
        return ChatResponse(
            weights=current_weights,
            conversation_history=history,
            questions_asked=req.questions_asked + 1,
            dimensions_covered=list(dims_covered),
            next_step="ask_question",
            question=question_data
        )
    
    # Fallback to results if Gemini fails to make a question
    results = engine.get_top_neighborhoods(df, current_weights, top_n=10)
    return ChatResponse(
        weights=current_weights,
        conversation_history=history,
        questions_asked=req.questions_asked,
        dimensions_covered=list(dims_covered),
        next_step="show_results",
        results=results,
        question=None
    )
