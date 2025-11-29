# analysis.py
import streamlit as st
from google import genai
from google.genai import types
import os
import json

# Define the definitive structured output schema expected by the frontend (app.py)
ANALYSIS_SCHEMA = types.Schema(
    type=types.Type.OBJECT,
    properties={
        "core_profile": types.Schema(
            type=types.Type.OBJECT,
            properties={
                "name": types.Schema(type=types.Type.STRING),
                "email": types.Schema(type=types.Type.STRING),
                "phone": types.Schema(type=types.Type.STRING),
                "summary": types.Schema(type=types.Type.STRING),
                "education": types.Schema(
                    type=types.Type.ARRAY,
                    items=types.Schema(
                        type=types.Type.OBJECT,
                        properties={"degree": types.Schema(type=types.Type.STRING), "institution": types.Schema(type=types.Type.STRING), "year": types.Schema(type=types.Type.STRING)},
                        required=["degree", "institution"],
                    ),
                ),
            },
            required=["name", "email", "summary"],
        ),
        "technical_expertise": types.Schema(
            type=types.Type.ARRAY,
            items=types.Schema(
                type=types.Type.OBJECT,
                properties={"skill": types.Schema(type=types.Type.STRING), "proficiency": types.Schema(type=types.Type.STRING), "keywords": types.Schema(type=types.Type.ARRAY, items=types.Schema(type=types.Type.STRING))},
                required=["skill", "proficiency"],
            ),
        ),
        "job_match_analysis": types.Schema(
            type=types.Type.OBJECT,
            properties={"match_score": types.Schema(type=types.Type.INTEGER), "justification": types.Schema(type=types.Type.STRING)},
        ),
    },
)

BLANK_ANALYSIS_DATA = {
    "core_profile": {"name": "Analysis Failed", "email": "N/A", "phone": "N/A", "summary": "Error: Check GEMINI_API_KEY and raw PDF text.", "education": []},
    "technical_expertise": [],
    "job_match_analysis": {"match_score": 0, "justification": "Analysis failed to produce structured output."},
}

def run_analysis(raw_text: str):
    """
    Core function integrating all AI requirements (Extraction, Scoring, Mock Matching).
    """
    st.info("Step 2: Running multi-step AI analysis via Gemini API...")
    
    if not os.getenv("GEMINI_API_KEY"):
        st.error("Error: GEMINI_API_KEY not found. Set environment variable in your terminal.")
        return BLANK_ANALYSIS_DATA

    client = genai.Client()
    
    prompt = (
        "You are an expert career platform AI. Analyze the following resume text and perform two tasks: "
        "1. **Structured Extraction**: Extract the candidate's full profile, skills, and assign proficiency levels (Beginner, Intermediate, Expert). "
        "2. **Mock Matching**: Based on the candidate's profile, generate a mock 'match_score' (0-100) and a brief justification for a hypothetical 'Senior Software Engineer' role. "
        "Return the output strictly in the specified JSON schema."
        f"\n\nRESUME TEXT:\n{raw_text[:10000]}"
    )

    try:
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=ANALYSIS_SCHEMA,
            ),
        )
        return json.loads(response.text)
        
    except Exception as e:
        st.error(f"Gemini API Error: {e}")
        return BLANK_ANALYSIS_DATA