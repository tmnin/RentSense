from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import pandas as pd
from models import ChatRequest, ChatResponse
import engine

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # For dev; narrow this down for production!
    allow_methods=["*"],
    allow_headers=["*"],
)

# Load data once
df = pd.read_csv("nta_scores_all.csv")

@app.post("/api/chat", response_model=ChatResponse)
async def chat_endpoint(req: ChatRequest):
    current_weights = req.weights.copy()
    history = req.conversation_history.copy()
    dims_covered = set(req.dimensions_covered)

    # 1. Handle Answer to Previous Question
    if req.selected_options and req.last_question_data:
        target_dim = req.last_question_data.get("dimension")
        for opt in req.last_question_data.get("options", []):
            if opt["id"] in req.selected_options:
                # Add the delta and mark as covered
                current_weights[target_dim] += opt.get("weight_delta", 0)
                dims_covered.add(target_dim)
        history.append({"role": "user", "content": f"Selected: {', '.join(req.selected_options)}"})

    # 2. Analyze Initial Input (Replaces your 'simplified' comment)
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
        results = engine.get_top_neighborhoods(df, current_weights)
        return ChatResponse(
            weights=current_weights,
            conversation_history=history,
            questions_asked=req.questions_asked,
            dimensions_covered=list(dims_covered),
            next_step="show_results",
            results=results
        )

    # 4. Generate Next Question
    q_prompt = f"History: {history}. Ask about a missing dimension from {engine.UI_DIMENSIONS}. Return JSON with question and options."
    question_data = engine.call_gemini(q_prompt)
    
    if question_data:
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
    results = engine.get_top_neighborhoods(df, current_weights)
    return ChatResponse(
        weights=current_weights,
        conversation_history=history,
        questions_asked=req.questions_asked,
        dimensions_covered=list(dims_covered),
        next_step="show_results",
        results=results,
        question=None  # Explicitly set to None so React doesn't look for a question
    )