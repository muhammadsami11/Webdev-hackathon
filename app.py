# app.py
import streamlit as st
import pandas as pd
from io import BytesIO
from resume_analysis import extract_text_from_pdf_with_fallback

# --- NECESSARY IMPORTS FOR APP.PY ---
# The logic for PDF reading is now self-contained, but the
# analysis file is still required.
from analysis import run_analysis, BLANK_ANALYSIS_DATA
from job_discovery import discover_jobs_for_resume
from job_scraper import scrape_all_sources
from job_database import count_jobs
from dashboard import render_dashboard

# --- INTEGRATED PDF READING FUNCTION (MOVED FROM data_utils.py) ---
def get_raw_text_from_pdf(uploaded_file):
    import tempfile
    import os
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
        tmp.write(uploaded_file.getbuffer())
        tmp_path = tmp.name
    try:
        text = extract_text_from_pdf_with_fallback(tmp_path)
    finally:
        os.remove(tmp_path)
    return text
# --- STREAMLIT UI LAYOUT AND DISPLAY LOGIC ---

st.set_page_config(layout="wide", page_title="AI Career Platform Prototype")
st.title("🤖 AI-Powered Career Preparation Platform")
st.markdown("---")

# --- SIDEBAR: JOB SCRAPING CONTROL ---
with st.sidebar:
    st.subheader("📊 Job Database Control")
    jobs_count = count_jobs()
    st.metric(label="Cached Jobs", value=jobs_count)
    
    if st.button("🔍 Scrape Jobs from Internet", help="Scrapes Indeed, GitHub Jobs, and other sources"):
        with st.spinner("Scraping job listings... (this may take 30-60 seconds)"):
            try:
                new_jobs = scrape_all_sources(keywords="python developer", max_jobs=50)
                st.success(f"✅ Scraped {len(new_jobs)} new jobs!")
            except Exception as e:
                st.error(f"Scraping error: {e}. Using cached jobs instead.")
    
    if st.button("🗑️ Clear Job Cache", help="Deletes all cached jobs"):
        from job_database import clear_jobs
        clear_jobs()
        st.success("Cache cleared!")
    if st.button("📈 Open Dashboard", help="Open user dashboard and analytics"):
        # render the dashboard in the main app area
        try:
            # try to infer resume skills from last analysis if available in session state
            resume_skills = st.session_state.get('last_resume_skills') if 'last_resume_skills' in st.session_state else None
            render_dashboard(resume_skills=resume_skills)
        except Exception as e:
            st.error(f"Error rendering dashboard: {e}")

job_description = ""
# File Upload Section
# File Upload Section
st.header("1. Intelligent Resume Analysis")
uploaded_file = st.file_uploader("Choose a PDF file to analyze:", type="pdf")


# User Input for Job Discovery/Interview Prep (Input field for backend use)
st.markdown("---")
st.header("2. Job Match & Interview Prep Input")
job_description = st.text_area("Paste a Job Description (for matching):", height=150, help="Your friend's job matching logic will use this text.")
st.markdown("---")

# Trigger Analysis and Display Results
if st.button(
        "🚀 Analyze Resume & Run Match/Preps", 
        key="analyze_resume_main",
        help="Triggers PDF analysis, profile generation, and mock matching."
    ):
        
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
                
                st.markdown("---")
                
                # --- JOB DISCOVERY & MATCHING ---
                st.subheader("5. Automated Job Discovery & Matching")
                st.markdown("Discovering job opportunities based on your skills...")
                
                try:
                    # Extract skills from analysis for job matching
                    resume_skills = [skill['skill'] for skill in analysis_data.get('technical_expertise', [])]
                    
                    # Estimate experience years from experience field (simple heuristic)
                    experience_years = 3  # default
                    try:
                        experience_field = analysis_data.get('core_profile', {}).get('summary', '')
                        years_match = __import__('re').search(r'(\d+)\s*(?:\+)?\s*years?', experience_field, __import__('re').IGNORECASE)
                        if years_match:
                            experience_years = int(years_match.group(1))
                    except:
                        pass
                    
                    # Discover jobs
                    job_results = discover_jobs_for_resume(resume_skills, experience_years, min_score_threshold=25.0)
                    
                    st.metric(label="Total Jobs Found", value=job_results['total_jobs_found'])
                    st.metric(label="Matched Jobs", value=job_results['jobs_matched'])
                    
                    if job_results['ranked_jobs']:
                        st.markdown("#### Top Job Matches:")
                        
                        for idx, job in enumerate(job_results['ranked_jobs'][:10], 1):
                            with st.expander(f"#{idx} {job['title']} at {job['company']} ({job['compatibility_score']}% match)"):
                                col1, col2 = st.columns([1, 1])
                                
                                with col1:
                                    st.markdown(f"**Location:** {job['location']}")
                                    st.markdown(f"**Salary:** {job['salary']}")
                                    st.markdown(f"**Level:** {job['experience_level']}")
                                
                                with col2:
                                    st.markdown(f"**Compatibility Score:** {job['compatibility_score']}%")
                                    st.markdown(f"**Matched Skills:** {', '.join(job['compatibility_details']['matched_skills']) if job['compatibility_details']['matched_skills'] else 'None'}")
                                    if job['compatibility_details']['missing_skills']:
                                        st.markdown(f"**Missing Skills:** {', '.join(job['compatibility_details']['missing_skills'])}")
                                
                                st.markdown("**Why This Match:**")
                                st.info(job['justification'])
                                
                                st.markdown("**Job Description:**")
                                st.text(job['description'])
                    else:
                        st.warning("No matching jobs found. Try expanding your skills or lowering the match threshold.")
                
                except Exception as e:
                    st.error(f"Job discovery error: {e}")
            
            else:
                 st.error("Analysis Failed. Check the backend logs/API key.")

# Footer/Initial Instruction
st.markdown("---")
if uploaded_file is None:
    st.warning("Upload a PDF resume above to start the user journey.")