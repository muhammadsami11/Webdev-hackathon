"""
Job Database Module

Handles persistence of scraped job listings using SQLite.
Provides methods to save, retrieve, and query jobs.
"""

import sqlite3
import json
from typing import List, Dict, Any, Optional
from datetime import datetime
import os


DB_PATH = os.path.join(os.path.dirname(__file__), "jobs.db")


def init_database():
    """Initialize SQLite database with jobs table."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    c.execute('''
        CREATE TABLE IF NOT EXISTS jobs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            job_id TEXT UNIQUE,
            title TEXT NOT NULL,
            company TEXT NOT NULL,
            location TEXT,
            description TEXT,
            required_skills TEXT,
            experience_level TEXT,
            salary TEXT,
            source TEXT,
            job_url TEXT,
            scraped_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(job_id)
        )
    ''')
    
    conn.commit()
    conn.close()


def save_job(job: Dict[str, Any]) -> bool:
    """
    Save a job to the database.
    Returns True if successful, False if job already exists.
    """
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        
        # Convert list fields to JSON
        required_skills = json.dumps(job.get('required_skills', []))
        
        c.execute('''
            INSERT OR IGNORE INTO jobs 
            (job_id, title, company, location, description, required_skills, 
             experience_level, salary, source, job_url)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            job.get('id', f"{job.get('company')}_{job.get('title')}_{datetime.now().timestamp()}"),
            job.get('title'),
            job.get('company'),
            job.get('location'),
            job.get('description'),
            required_skills,
            job.get('experience_level', 'Not specified'),
            job.get('salary'),
            job.get('source', 'Unknown'),
            job.get('job_url')
        ))
        
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"Error saving job: {e}")
        return False


def save_jobs_batch(jobs: List[Dict[str, Any]]) -> int:
    """Save multiple jobs to database. Returns count of successfully saved jobs."""
    count = 0
    for job in jobs:
        if save_job(job):
            count += 1
    return count


def get_all_jobs(limit: int = 100) -> List[Dict[str, Any]]:
    """Retrieve all jobs from database."""
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        
        c.execute('SELECT * FROM jobs LIMIT ?', (limit,))
        rows = c.fetchall()
        
        jobs = []
        for row in rows:
            job = dict(row)
            # Convert JSON back to list
            job['required_skills'] = json.loads(job['required_skills']) if job['required_skills'] else []
            jobs.append(job)
        
        conn.close()
        return jobs
    except Exception as e:
        print(f"Error retrieving jobs: {e}")
        return []


def search_jobs_by_skills(skills: List[str], limit: int = 50) -> List[Dict[str, Any]]:
    """Search for jobs that match any of the provided skills."""
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        
        # Get all jobs and filter in Python (SQLite JSON support varies)
        c.execute('SELECT * FROM jobs LIMIT ?', (limit * 3,))  # Get extra to filter
        rows = c.fetchall()
        
        matched_jobs = []
        skills_normalized = {s.lower() for s in skills}
        
        for row in rows:
            job = dict(row)
            job['required_skills'] = json.loads(job['required_skills']) if job['required_skills'] else []
            
            job_skills_normalized = {s.lower() for s in job['required_skills']}
            
            # Check for skill overlap
            if job_skills_normalized & skills_normalized:
                matched_jobs.append(job)
        
        conn.close()
        return matched_jobs[:limit]
    except Exception as e:
        print(f"Error searching jobs: {e}")
        return []


def get_jobs_by_source(source: str, limit: int = 50) -> List[Dict[str, Any]]:
    """Retrieve jobs from a specific source."""
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        
        c.execute('SELECT * FROM jobs WHERE source = ? LIMIT ?', (source, limit))
        rows = c.fetchall()
        
        jobs = []
        for row in rows:
            job = dict(row)
            job['required_skills'] = json.loads(job['required_skills']) if job['required_skills'] else []
            jobs.append(job)
        
        conn.close()
        return jobs
    except Exception as e:
        print(f"Error retrieving jobs by source: {e}")
        return []


def count_jobs() -> int:
    """Get total count of jobs in database."""
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        
        c.execute('SELECT COUNT(*) FROM jobs')
        count = c.fetchone()[0]
        
        conn.close()
        return count
    except Exception as e:
        print(f"Error counting jobs: {e}")
        return 0


def clear_jobs(source: Optional[str] = None):
    """Clear all jobs or jobs from a specific source."""
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        
        if source:
            c.execute('DELETE FROM jobs WHERE source = ?', (source,))
        else:
            c.execute('DELETE FROM jobs')
        
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"Error clearing jobs: {e}")


# Initialize database on module import
init_database()
