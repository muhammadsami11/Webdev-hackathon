# app.py
import streamlit as st
import pandas as pd
from io import BytesIO

# --- NECESSARY IMPORTS FOR APP.PY ---
# The logic for PDF reading is now self-contained, but the
# analysis file is still required.
from analysis import run_analysis, BLANK_ANALYSIS_DATA

# --- INTEGRATED PDF READING FUNCTION (MOVED FROM data_utils.py) ---
def get_raw_text_from_pdf(uploaded_file: BytesIO) -> str:
    """
    Placeholder for the full PDF text extraction logic.
    Since 'pypdf2' caused crashes, this is a placeholder function
    to ensure the UI can launch. Your team should put the final, working
    PDF reading logic (with pypdf2 or another library) here.
    """
    st.info("Step 1: Running PDF text extractor (Placeholder)...")
    
    # Return a basic placeholder string for the analysis function to process
    return "Placeholder Resume Text: John Doe, 5 years experience in Python, Streamlit, and Data Analysis. Education from XYZ University."

# --- STREAMLIT UI LAYOUT AND DISPLAY LOGIC ---

st.set_page_config(layout="wide", page_title="AI Career Platform Prototype")
st.title("🤖 AI-Powered Career Preparation Platform")
st.markdown("---")

# File Upload Section
st.header("1. Intelligent Resume Analysis")
uploaded_file = st.file_uploader("Choose a PDF file to analyze:", type="pdf")

# User Input for Job Discovery/Interview Prep (Input field for backend use)
st.markdown("---")
st.header("2. Job Match & Interview Prep Input")
job_description = st.text_area("Paste a Job Description (for matching):", height=150, help="Your friend's job matching logic will use this text.")
st.markdown("---")


if uploaded_file is not None:
    if st.button("🚀 Analyze Resume & Run Match/Prep", help="Triggers PDF analysis, profile generation, and mock matching."):
        
        with st.spinner('Running multi-step AI analysis and data structuring...'):
            
            # 1. Get Raw Text (Calls the function defined above in app.py)
            raw_text = get_raw_text_from_pdf(uploaded_file)
            if not raw_text:
                st.error("Cannot proceed. Raw text extraction failed.")
                st.stop()
                
            # 2. Run Core Analysis (Calls function in analysis.py)
            analysis_data = run_analysis(raw_text, job_description)
            
            # --- DISPLAY RESULTS (MEMBER 1'S CORE TASK) ---
            st.markdown("---")
            
            if analysis_data is not BLANK_ANALYSIS_DATA:
                st.success("✅ Analysis Complete! Structured Profile & Insights:")

                # Display General Profile
                st.subheader("2.1 Candidate Core Profile")
                col1, col2 = st.columns([1, 2])
                
                with col1:
                    st.metric(label="Name", value=analysis_data['core_profile']['name'])
                    st.metric(label="Email", value=analysis_data['core_profile']['email'])
                    st.metric(label="Phone", value=analysis_data['core_profile']['phone'])
                
                with col2:
                    st.markdown(f"**Summary:**")
                    st.info(analysis_data['core_profile']['summary'])
                
                st.markdown("#### Education History")
                if analysis_data['core_profile']['education']:
                    education_df = pd.DataFrame(analysis_data['core_profile']['education'])
                    st.dataframe(education_df, hide_index=True)
                
                st.markdown("---")

                # Display Technical Expertise
                st.subheader("2.2 Technical Expertise & Proficiency Levels")
                
                if analysis_data['technical_expertise']:
                    expertise_df = pd.DataFrame(analysis_data['technical_expertise'])
                    expertise_df['keywords'] = expertise_df['keywords'].apply(lambda x: ", ".join(x))
                    expertise_df.rename(columns={'skill': 'Skill Area', 'proficiency': 'Proficiency Level', 'keywords': 'Related Tools/Keywords'}, inplace=True)
                    st.table(expertise_df)
                else:
                    st.warning("No technical expertise identified.")
                
                st.markdown("---")
                
                # Display Job Match Analysis
                st.subheader("3. Automated Job Discovery & Matching (MVP)")
                st.markdown("*(Match against the job description provided above)*")
                
                match_score = analysis_data['job_match_analysis']['match_score']
                st.metric(label="Match Score", value=f"{match_score}%", help="Compatibility Score explaining why the job fits.")
                
                st.markdown("#### Compatibility Explanation (Justification)")
                st.code(analysis_data['job_match_analysis']['justification'], language=None)
                
                st.markdown("---")

                # Placeholder for Interview Prep
                st.subheader("4. Deep Research-Powered Interview Preparation")
                st.warning("Interview Preparation materials (e.g., questions, study guide) will appear here.")
            
            else:
                 st.error("Analysis Failed. Check the backend logs/API key.")

# Footer/Initial Instruction
st.markdown("---")
if uploaded_file is None:
    st.warning("Upload a PDF resume above to start the user journey.")