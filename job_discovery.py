"""
Job Discovery and Matching Module

Discovers and matches job listings based on resume qualifications,
ranks by relevance, and computes compatibility scores with explanations.
"""

from typing import List, Dict, Any, Optional
import re
from job_scraper import get_cached_jobs
from job_database import search_jobs_by_skills


# --- FALLBACK MOCK JOB DATA (if scraping fails) ---
FALLBACK_MOCK_JOBS = [
    {
        "id": "job_1",
        "title": "Senior Python Developer",
        "company": "TechCorp",
        "location": "Remote",
        "description": "We are looking for a Python expert with 5+ years experience in Django and FastAPI. Must know SQL, Docker, and AWS.",
        "required_skills": ["Python", "Django", "FastAPI", "SQL", "Docker", "AWS"],
        "experience_level": "Senior",
        "salary": "$120,000 - $150,000",
        "source": "Mock Data"
    },
    {
        "id": "job_2",
        "title": "Full Stack JavaScript Developer",
        "company": "WebSolutions",
        "location": "New York, NY",
        "description": "React and Node.js expert needed. Experience with TypeScript, MongoDB, and REST APIs required.",
        "required_skills": ["JavaScript", "React", "Node.js", "TypeScript", "MongoDB", "REST APIs"],
        "experience_level": "Mid-level",
        "salary": "$90,000 - $120,000",
        "source": "Mock Data"
    },
    {
        "id": "job_3",
        "title": "Data Scientist",
        "company": "DataDriven Inc",
        "location": "San Francisco, CA",
        "description": "Seeking a data scientist with expertise in Python, pandas, numpy, scikit-learn, and deep learning frameworks.",
        "required_skills": ["Python", "pandas", "numpy", "scikit-learn", "Deep Learning", "SQL"],
        "experience_level": "Mid-level",
        "salary": "$110,000 - $140,000",
        "source": "Mock Data"
    },
    {
        "id": "job_4",
        "title": "DevOps Engineer",
        "company": "CloudOps",
        "location": "Remote",
        "description": "Docker, Kubernetes, CI/CD pipelines, AWS/GCP experience. Must have 3+ years in DevOps.",
        "required_skills": ["Docker", "Kubernetes", "AWS", "CI/CD", "Linux"],
        "experience_level": "Mid-level",
        "salary": "$100,000 - $130,000",
        "source": "Mock Data"
    },
    {
        "id": "job_5",
        "title": "Junior Web Developer",
        "company": "StartupXYZ",
        "location": "Remote",
        "description": "Looking for enthusiastic junior developers. HTML, CSS, JavaScript, and Git knowledge required.",
        "required_skills": ["JavaScript", "HTML", "CSS", "Git"],
        "experience_level": "Junior",
        "salary": "$50,000 - $70,000",
        "source": "Mock Data"
    },
]


def normalize_skill(skill: str) -> str:
    """Normalize skill name for matching (lowercase, strip whitespace)."""
    return skill.lower().strip()


def compute_skill_overlap(resume_skills: List[str], job_required_skills: List[str]) -> tuple:
    """
    Compute overlap between resume skills and job requirements.
    Returns (matched_skills, unmatched_required, overlap_percentage).
    """
    resume_normalized = {normalize_skill(s) for s in resume_skills}
    job_normalized = {normalize_skill(s) for s in job_required_skills}
    
    matched = resume_normalized & job_normalized
    unmatched = job_normalized - resume_normalized
    
    overlap_pct = (len(matched) / len(job_normalized) * 100) if job_normalized else 0
    
    return matched, unmatched, overlap_pct


def compute_compatibility_score(
    resume_skills: List[str],
    resume_experience_years: int,
    job_required_skills: List[str],
    job_experience_level: str
) -> Dict[str, Any]:
    """
    Compute a comprehensive compatibility score (0-100) based on:
    - Skill overlap (40% weight)
    - Experience level alignment (30% weight)
    - Required skills coverage (30% weight)
    """
    matched, unmatched, overlap_pct = compute_skill_overlap(resume_skills, job_required_skills)
    
    # Skill overlap component (40%)
    skill_score = overlap_pct * 0.4
    
    # Experience level alignment (30%)
    # Map job level to expected years
    level_to_years = {
        "junior": (0, 2),
        "mid-level": (2, 5),
        "senior": (5, 20),
        "lead": (7, 20),
    }
    job_level_lower = job_experience_level.lower()
    expected_min, expected_max = level_to_years.get(job_level_lower, (0, 20))
    
    if resume_experience_years >= expected_min:
        exp_score = min(100, (resume_experience_years / expected_max) * 100) * 0.3
    else:
        exp_score = max(0, (resume_experience_years / expected_min) * 100) * 0.3
    
    # Required skills coverage (30%)
    required_coverage = (len(matched) / len(job_required_skills) * 100) if job_required_skills else 0
    coverage_score = required_coverage * 0.3
    
    total_score = skill_score + exp_score + coverage_score
    
    return {
        "total_score": round(total_score, 1),
        "skill_match_pct": round(overlap_pct, 1),
        "matched_skills": list(matched),
        "missing_skills": list(unmatched),
        "experience_alignment": "✓ Aligned" if resume_experience_years >= expected_min else "✗ Below expected",
    }


def generate_justification(
    compatibility: Dict[str, Any],
    job_title: str,
    resume_skills: List[str]
) -> str:
    """Generate a human-readable explanation of the match."""
    score = compatibility["total_score"]
    matched = compatibility["matched_skills"]
    missing = compatibility["missing_skills"]
    
    justification_parts = []
    
    if score >= 80:
        justification_parts.append(f"🟢 Excellent match ({score}%).")
    elif score >= 60:
        justification_parts.append(f"🟡 Good match ({score}%).")
    elif score >= 40:
        justification_parts.append(f"🟡 Fair match ({score}%).")
    else:
        justification_parts.append(f"🔴 Low match ({score}%).")
    
    if matched:
        justification_parts.append(f"You have {len(matched)} of {len(matched) + len(missing)} required skills: {', '.join(list(matched)[:3])}{'...' if len(matched) > 3 else ''}.")
    
    if missing:
        justification_parts.append(f"You may want to develop: {', '.join(list(missing)[:2])}.")
    
    if compatibility["experience_alignment"] == "✓ Aligned":
        justification_parts.append("Your experience level aligns well with the role.")
    else:
        justification_parts.append("Your experience level may be below expectations for this role.")
    
    return " ".join(justification_parts)


def filter_and_rank_jobs(
    resume_skills: List[str],
    jobs_to_rank: List[Dict[str, Any]],
    experience_years: int = 3,
    min_compatibility_threshold: float = 30.0
) -> List[Dict[str, Any]]:
    """
    Filter and rank jobs by compatibility score.
    Now accepts a list of jobs to rank (instead of using hardcoded MOCK_JOBS).
    Returns a sorted list (best matches first) with compatibility details.
    """
    ranked_jobs = []
    
    for job in jobs_to_rank:
        compatibility = compute_compatibility_score(
            resume_skills=resume_skills,
            resume_experience_years=experience_years,
            job_required_skills=job["required_skills"],
            job_experience_level=job["experience_level"]
        )
        
        score = compatibility["total_score"]
        
        # Filter by minimum threshold
        if score >= min_compatibility_threshold:
            justification = generate_justification(compatibility, job["title"], resume_skills)
            
            ranked_jobs.append({
                **job,
                "compatibility_score": score,
                "compatibility_details": compatibility,
                "justification": justification,
            })
    
    # Sort by score (highest first)
    ranked_jobs.sort(key=lambda x: x["compatibility_score"], reverse=True)
    
    return ranked_jobs


def scrape_real_jobs(keywords: str, location: str = "Remote") -> List[Dict[str, Any]]:
    """
    Get REAL job listings from internet sources via scraper.
    Automatically scrapes if database is empty.
    Returns actual jobs or empty list if scraping fails.
    """
    try:
        from job_scraper import scrape_all_sources, get_cached_jobs
        
        # Try to get from cache first
        cached = get_cached_jobs(max_results=100)
        
        if cached and len(cached) > 5:
            print(f"[CACHE] Using {len(cached)} cached jobs from database")
            return cached
        
        # If cache is empty or too small, trigger a live scrape
        print("[SCRAPER] Cache empty - triggering live scrape from Indeed, GitHub, LinkedIn...")
        scraped = scrape_all_sources(keywords=keywords, max_jobs=50)
        
        if scraped:
            print(f"[SUCCESS] Scraped {len(scraped)} REAL jobs from internet sources")
            return scraped
        else:
            print("[WARNING] Scraping returned no results. Using fallback mock data.")
            return FALLBACK_MOCK_JOBS
            
    except Exception as e:
        print(f"[ERROR] Scraping error: {e}. Using fallback mock data.")
        return FALLBACK_MOCK_JOBS


def discover_jobs_for_resume(
    resume_skills: List[str],
    experience_years: int = 3,
    min_score_threshold: float = 30.0
) -> Dict[str, Any]:
    """
    Main entry point: discover and rank jobs for a resume.
    
    Returns:
    {
        "total_jobs_found": int,
        "jobs_matched": int,
        "ranked_jobs": [...]
    }
    """
    # Get REAL jobs from internet sources
    all_jobs = scrape_real_jobs(" ".join(resume_skills))
    
    # Rank them by compatibility with resume
    ranked = filter_and_rank_jobs(resume_skills, all_jobs, experience_years, min_score_threshold)
    
    return {
        "total_jobs_found": len(all_jobs),
        "jobs_matched": len(ranked),
        "ranked_jobs": ranked,
    }
