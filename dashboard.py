import sqlite3
import json
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "jobs.db")


def init_analytics_table():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS interview_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT,
            questions TEXT,
            notes TEXT,
            completed INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()


def record_interview_session(title: str, questions: List[str], notes: str = "", completed: bool = False) -> int:
    init_analytics_table()
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('INSERT INTO interview_history (title, questions, notes, completed) VALUES (?, ?, ?, ?)',
              (title, json.dumps(questions), notes, 1 if completed else 0))
    conn.commit()
    rowid = c.lastrowid
    conn.close()
    return rowid


def get_interview_history(limit: int = 50) -> List[Dict[str, Any]]:
    init_analytics_table()
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute('SELECT * FROM interview_history ORDER BY created_at DESC LIMIT ?', (limit,))
    rows = c.fetchall()
    sessions = []
    for r in rows:
        sessions.append({
            'id': r['id'],
            'title': r['title'],
            'questions': json.loads(r['questions']) if r['questions'] else [],
            'notes': r['notes'],
            'completed': bool(r['completed']),
            'created_at': r['created_at']
        })
    conn.close()
    return sessions


def job_search_progress() -> Dict[str, Any]:
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('SELECT COUNT(*) FROM jobs')
    total = c.fetchone()[0]

    # jobs in last 7 days
    seven_days_ago = datetime.utcnow() - timedelta(days=7)
    c.execute('SELECT COUNT(*) FROM jobs WHERE scraped_at >= ?', (seven_days_ago,))
    recent = c.fetchone()[0]

    # breakdown by source
    c.execute('SELECT source, COUNT(*) as cnt FROM jobs GROUP BY source')
    rows = c.fetchall()
    sources = {r[0]: r[1] for r in rows}

    conn.close()
    return {'total_jobs': total, 'jobs_last_7_days': recent, 'by_source': sources}


def skill_coverage_analysis(resume_skills: List[str], sample_limit: int = 500) -> Dict[str, Any]:
    """Compute coverage of resume skills against required skills in the job DB.

    Returns overall coverage percentage, top missing skills, and a histogram of coverage.
    """
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute('SELECT required_skills FROM jobs LIMIT ?', (sample_limit,))
    rows = c.fetchall()

    resume_norm = {s.lower() for s in resume_skills}
    total_jobs = 0
    match_counts = []
    missing_counter = {}

    for r in rows:
        total_jobs += 1
        skills = []
        try:
            skills = json.loads(r['required_skills']) if r['required_skills'] else []
        except Exception:
            skills = []

        skills_norm = {s.lower() for s in skills}
        matched = resume_norm & skills_norm
        match_counts.append(len(matched) / (len(skills_norm) if skills_norm else 1))

        for sk in skills_norm:
            if sk not in resume_norm:
                missing_counter[sk] = missing_counter.get(sk, 0) + 1

    conn.close()

    avg_coverage = (sum(match_counts) / len(match_counts) * 100) if match_counts else 0.0
    # top missing skills
    top_missing = sorted(missing_counter.items(), key=lambda x: x[1], reverse=True)[:20]

    return {'avg_coverage_pct': round(avg_coverage, 1), 'top_missing': top_missing, 'total_sampled_jobs': total_jobs}


def render_dashboard(resume_skills: Optional[List[str]] = None):
    """Streamlit-ready dashboard renderer. Call from `app.py` where Streamlit is available."""
    try:
        import streamlit as st
        import pandas as pd
    except Exception:
        raise RuntimeError("Streamlit is required to render the dashboard")

    st.header("User Dashboard & Analytics")

    progress = job_search_progress()
    col1, col2, col3 = st.columns(3)
    col1.metric("Total Jobs Cached", progress['total_jobs'])
    col2.metric("Jobs (last 7 days)", progress['jobs_last_7_days'])
    col3.metric("Sources", len(progress['by_source']))

    st.markdown("**Jobs by Source**")
    if progress['by_source']:
        df_src = pd.DataFrame(list(progress['by_source'].items()), columns=['source', 'count'])
        st.bar_chart(df_src.set_index('source'))
    else:
        st.write("No jobs yet")

    st.markdown("---")

    # Skill coverage
    st.subheader("Skill Coverage Analysis")
    if resume_skills:
        analysis = skill_coverage_analysis(resume_skills)
        st.metric("Avg Coverage", f"{analysis['avg_coverage_pct']}%")
        st.write(f"Sampled jobs: {analysis['total_sampled_jobs']}")
        if analysis['top_missing']:
            missing_df = pd.DataFrame(analysis['top_missing'], columns=['skill', 'occurrences'])
            st.table(missing_df.head(10))
    else:
        st.info("Upload a resume or provide your skill list to see skill coverage.")

    st.markdown("---")

    # Interview prep history
    st.subheader("Interview Preparation History")
    sessions = get_interview_history(limit=20)
    if sessions:
        for s in sessions:
            with st.expander(f"{s['title']} - {s['created_at']}"):
                st.write("Questions:")
                for q in s['questions']:
                    st.write(f"- {q}")
                st.write("Notes:")
                st.write(s['notes'])
                st.write("Completed:" , s['completed'])
    else:
        st.write("No interview sessions recorded yet.")

    st.markdown("---")
    st.subheader("AI Insights & Recommendations")
    if resume_skills:
        st.write("Top missing skills across job listings (see Skill Coverage table).")
        st.write("Recommendation: prioritize learning the top missing skills shown above; practice interview questions around them.")
    else:
        st.write("Upload your resume to get AI-driven insights here.")
