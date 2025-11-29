# analysis.py
import streamlit as st
import os
import json
# Attempt to load .env file automatically if python-dotenv is installed
try:
    from dotenv import load_dotenv
    # Load default .env
    load_dotenv()
    # Also attempt to load `file.env` if present in the repo (some users keep credentials there)
    env_path = os.path.join(os.path.dirname(__file__), "file.env")
    if os.path.exists(env_path):
        load_dotenv(env_path)
except Exception:
    pass

from dotenv import load_dotenv
print("GEMINI_API_KEY loaded:", os.getenv("GEMINI_API_KEY")) 
load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")
BLANK_ANALYSIS_DATA = {
    "core_profile": {"name": "Analysis Failed", "email": "N/A", "phone": "N/A", "summary": "Error: Check GEMINI_API_KEY and raw PDF text.", "education": []},
    "technical_expertise": [],
    "job_match_analysis": {"match_score": 0, "justification": "Analysis failed to produce structured output."},
}
def run_analysis(raw_text: str, job_description: str = ""):
    """
    Core function integrating all AI requirements (Extraction, Scoring, Mock Matching).
    """
    st.info("Step 2: Running multi-step AI analysis (LLM) - checking environment...")

    # Check for API key first
    gemini_key = os.getenv("GEMINI_API_KEY")
    if not gemini_key:
        # Provide a helpful message in the UI and fall back to a local heuristic analysis.
        st.warning("GEMINI_API_KEY not found. Falling back to local heuristic analysis (no LLM). Set GEMINI_API_KEY to enable Gemini-based analysis.")
        # Local fallback: use resume_analysis functions to build a reasonable structured output
        try:
            from resume_analysis import build_profile, identify_proficiency

            prof = build_profile(raw_text)
            skills = prof.get("skills", [])
            proficiency_map = prof.get("proficiency", {})

            # Build a simple core_profile with best-effort extraction
            # Try simple regex extraction for name/email/phone
            name = "Unknown"
            email = "N/A"
            phone = "N/A"
            import re
            # email
            m = re.search(r"[\w\.-]+@[\w\.-]+", raw_text)
            if m:
                email = m.group(0)
            # phone (simple patterns)
            m = re.search(r"(\+?\d[\d\s\-()]{7,}\d)", raw_text)
            if m:
                phone = m.group(0)
            # name: look for a line at the top with two capitalized words
            lines = [l.strip() for l in raw_text.splitlines() if l.strip()]
            if lines:
                first = lines[0]
                if re.match(r"^[A-Z][a-z]+\s+[A-Z][a-z]+$", first):
                    name = first

            # technical_expertise array
            technical_expertise = []
            for s in skills:
                technical_expertise.append({
                    "skill": s,
                    "proficiency": proficiency_map.get(s, "Beginner"),
                    "keywords": [s],
                })

            # Simple matching: count overlap between job_description keywords and skills
            jd = (job_description or "").lower()
            overlap = 0
            for s in skills:
                if s.lower() in jd:
                    overlap += 1
            match_score = min(100, int((overlap / max(1, len(skills))) * 100)) if skills else 0
            justification = f"Local heuristic match: {overlap} skill(s) matched out of {len(skills)} detected skills."

            return {
                "core_profile": {"name": name, "email": email, "phone": phone, "summary": prof.get("projects", [])[:1] or "", "education": prof.get("education", [])},
                "technical_expertise": technical_expertise,
                "job_match_analysis": {"match_score": match_score, "justification": justification},
            }
        except Exception as e:
            st.error(f"Local analysis fallback failed: {e}")
            return BLANK_ANALYSIS_DATA

    # Import the provider client lazily so the module can be imported even when the SDK isn't installed
    try:
        from google import genai
        from google.genai import types
    except Exception as e:
        st.error("Required LLM SDK 'google-genai' not available. Install it or run without LLM integration.")
        return BLANK_ANALYSIS_DATA

    # Build schema only when SDK is available
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

    client = genai.Client()
    prompt = (
        "You are an expert career platform AI. Analyze the following resume text and perform two tasks: "
        "1. Structured Extraction: Extract the candidate's full profile, skills, and assign proficiency levels (Beginner, Intermediate, Expert). "
        "2. Mock Matching: Based on the candidate's profile, generate a mock 'match_score' (0-100) and a brief justification for the following job:\n"
        f"{job_description or 'Senior Software Engineer'}\n"
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
        st.error(f"LLM API Error: {e}")
        return BLANK_ANALYSIS_DATA