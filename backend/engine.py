import json
import pandas as pd
import numpy as np
from google import genai

# ============================================================
# CONFIG & MAPPING
# ============================================================
API_KEY = "AIzaSyAvw2-ReZ2fQRm8BaUVa1xWkJBF7eTEEUI"
client = genai.Client(api_key=API_KEY)

# Map the AI names to your CSV column names
DIMENSIONS_MAP = {
    "Commute Convenience": "commute_score",
    "Safety": "safety_score",
    "Noise": "quiet_score",
    "Amenity Convenience": "amenities_score",
    "Green Space Accessibility": "parks_score",
    "Job Opportunities": "jobs_score",
    "Education Access": "schools_score",
    "Political Leaning": "politics_score"
}

UI_DIMENSIONS = list(DIMENSIONS_MAP.keys())

# ============================================================
# UTILS: The "No-Crash" Functions
# ============================================================

def call_gemini(prompt: str):
    """Safe wrapper to call Gemini and force-parse JSON."""
    try:
        response = client.models.generate_content(
            model='gemini-2.0-flash', # Use 2.0 or 1.5 based on your setup
            contents=prompt
        )
        text = response.text.strip()
        # Clean markdown if present
        if text.startswith("```json"): text = text[7:]
        if text.startswith("```"): text = text[3:]
        if text.endswith("```"): text = text[:-3]
        return json.loads(text.strip())
    except Exception as e:
        print(f"Gemini Error: {e}")
        return {}

def normalize_weights(weights: dict):
    """Strictly ensures weights are >= 0 and sum to exactly 8.0."""
    # Step 1: Force all weights to be non-negative (Fixes your bug!)
    cleaned = {k: max(0.0, float(v)) for k, v in weights.items()}
    
    total = sum(cleaned.values())
    if total > 0:
        # Scale everything so it sums to 8
        return {k: round((v / total) * 8, 2) for k, v in cleaned.items()}
    
    # Fallback to even distribution if everything is 0
    return {k: 1.0 for k in weights.keys()}

def get_top_neighborhoods(df: pd.DataFrame, weights_ui: dict, top_n=5):
    """Calculates the Fit Index using the current weights and the CSV data."""
    # Convert UI weights to column names
    col_weights = {DIMENSIONS_MAP[k]: v for k, v in weights_ui.items() if k in DIMENSIONS_MAP}
    
    def score_row(row):
        score = sum(row[col] * weight for col, weight in col_weights.items())
        return score / sum(col_weights.values())

    temp_df = df.copy()
    temp_df["fit_index"] = temp_df.apply(score_row, axis=1)
    # Convert to list of dicts for JSON response
    return temp_df.sort_values(by="fit_index", ascending=False).head(top_n).to_dict(orient="records")