"""
Enhanced Job Web Scraper Module

Scrapes REAL job listings from multiple internet sources:
- Indeed.com
- LinkedIn Jobs 
- GitHub Jobs API
- Generic job board scraper

Implements rate limiting, user-agent rotation, and proper error handling.
Stores all jobs in SQLite database for reuse.
"""

import os
import requests
from bs4 import BeautifulSoup
import time
from typing import List, Dict, Any, Optional
from urllib.parse import urljoin, quote
import random
from datetime import datetime

# Optional Selenium support
try:
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options
    from selenium.common.exceptions import WebDriverException
    SELENIUM_AVAILABLE = True
except Exception:
    SELENIUM_AVAILABLE = False

try:
    from job_database import save_jobs_batch, get_all_jobs
except ImportError:
    print("Warning: job_database module not found.")


# Realistic user agents to avoid being blocked
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/121.0",
]


def get_random_user_agent() -> str:
    """Get a random user agent."""
    return random.choice(USER_AGENTS)


def scrape_indeed_jobs(keywords: str, location: str = "", pages: int = 2, driver: Optional[object] = None) -> List[Dict[str, Any]]:
    """Scrape Indeed.com for job listings.

    If a Selenium `driver` is provided, it will be used to render pages (useful when
    sites rely on JS). Otherwise, a requests-based fetch is attempted.
    """
    jobs = []
    base_url = "https://www.indeed.com/jobs"
    print(f"[SCRAPER] Scraping Indeed for: {keywords}")
    
    for page in range(pages):
        try:
            params = {
                "q": keywords,
                "l": location if location else "Remote",
                "start": page * 10,
            }
            
            headers = {
                "User-Agent": get_random_user_agent(),
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Referer": "https://www.google.com/",
            }
            
            # If a Selenium driver was provided, use it to render the page (helps with JS-heavy pages)
            if driver is not None and SELENIUM_AVAILABLE:
                search_url = f"{base_url}?q={quote(keywords)}&l={quote(location if location else 'Remote')}&start={page * 10}"
                try:
                    driver.get(search_url)
                    time.sleep(2)  # allow JS to render
                    html = driver.page_source
                    soup = BeautifulSoup(html, "html.parser")
                except Exception as e:
                    print(f"   [SELENIUM] Indeed render error: {e}. Falling back to requests")
                    response = requests.get(base_url, params=params, headers=headers, timeout=10)
                    response.raise_for_status()
                    soup = BeautifulSoup(response.content, "html.parser")
            else:
                response = requests.get(base_url, params=params, headers=headers, timeout=10)
                response.raise_for_status()
                soup = BeautifulSoup(response.content, "html.parser")
            
            # Find job cards on Indeed
            job_cards = soup.find_all("div", class_="job_seen_beacon")
            
            for card in job_cards:
                try:
                    title_elem = card.find("h2", class_="jobTitle")
                    company_elem = card.find("span", class_="companyName")
                    location_elem = card.find("div", class_="companyLocation")
                    snippet_elem = card.find("div", class_="job-snippet")
                    salary_elem = card.find("div", class_="salary-snippet")
                    link_elem = card.find("a")
                    
                    if not (title_elem and company_elem):
                        continue
                    
                    title = title_elem.get_text(strip=True)
                    company = company_elem.get_text(strip=True)
                    location_text = location_elem.get_text(strip=True) if location_elem else location
                    description = snippet_elem.get_text(strip=True) if snippet_elem else ""
                    salary = salary_elem.get_text(strip=True) if salary_elem else "Not specified"
                    job_url = link_elem.get("href", "") if link_elem else ""
                    
                    if job_url and not job_url.startswith("http"):
                        job_url = urljoin(base_url, job_url)
                    
                    job = {
                        "id": f"indeed_{hash(title + company) % 1000000}",
                        "title": title,
                        "company": company,
                        "location": location_text,
                        "description": description,
                        "salary": salary,
                        "job_url": job_url,
                        "source": "Indeed",
                        "required_skills": extract_skills_from_text(description),
                        "experience_level": infer_experience_level(title),
                    }
                    jobs.append(job)
                    
                except Exception:
                    continue
            
            print(f"   [PAGE] Page {page + 1}: Found {len(job_cards)} jobs")
            time.sleep(random.uniform(2, 4))
            
        except Exception as e:
            print(f"   [ERROR] Error on page {page}: {str(e)[:200]}")
            continue
    
    return jobs


def scrape_github_jobs_api(keywords: str = "python", pages: int = 1) -> List[Dict[str, Any]]:
    """Scrape from GitHub Jobs API."""
    jobs = []
    
    print(f"[SCRAPER] Scraping GitHub Jobs for: {keywords}")
    
    try:
        for page in range(pages):
            url = "https://jobs.github.com/api/positions.json"
            
            params = {
                "description": keywords,
                "page": page,
            }
            
            headers = {"User-Agent": get_random_user_agent()}
            
            response = requests.get(url, params=params, headers=headers, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            
            if not data:
                break
            
            for job_data in data:
                try:
                    job = {
                        "id": f"github_{job_data.get('id', '')}",
                        "title": job_data.get('title', ''),
                        "company": job_data.get('company', ''),
                        "location": job_data.get('location', 'Remote'),
                        "description": job_data.get('description', ''),
                        "salary": "Not specified",
                        "job_url": job_data.get('url', ''),
                        "source": "GitHub Jobs",
                        "required_skills": extract_skills_from_text(job_data.get('description', '')),
                        "experience_level": infer_experience_level(job_data.get('title', '')),
                    }
                    jobs.append(job)
                except Exception:
                    continue
            
            print(f"   [PAGE] Page {page + 1}: Found {len(data)} jobs")
            time.sleep(random.uniform(1, 2))
            
    except Exception as e:
        print(f"   [ERROR] GitHub Jobs error: {str(e)[:200]}")
    
    return jobs


def scrape_linkedin_jobs(keywords: str = "python", pages: int = 1, driver: Optional[object] = None) -> List[Dict[str, Any]]:
    """Scrape LinkedIn Jobs.

    Uses requests by default; LinkedIn is often dynamic and may require Selenium.
    """
    jobs = []
    
    print(f"[SCRAPER] Scraping LinkedIn for: {keywords}")
    
    try:
        for page in range(pages):
            # LinkedIn search page (guest) - prefer Selenium when available
            search_url = f"https://www.linkedin.com/jobs/search/?keywords={quote(keywords)}&start={page * 25}"
            headers = {"User-Agent": get_random_user_agent()}

            # Use provided Selenium driver if available, otherwise fall back to requests
            if driver is not None and SELENIUM_AVAILABLE:
                try:
                    driver.get(search_url)
                    time.sleep(2)
                    html = driver.page_source
                    soup = BeautifulSoup(html, "html.parser")
                except Exception:
                    response = requests.get(search_url, headers=headers, timeout=10)
                    response.raise_for_status()
                    soup = BeautifulSoup(response.content, "html.parser")
            
            else:
                response = requests.get(search_url, headers=headers, timeout=10)
                response.raise_for_status()
                soup = BeautifulSoup(response.content, "html.parser")
            job_cards = soup.find_all("div", class_="base-card")
            
            for card in job_cards:
                try:
                    title_elem = card.find("h3")
                    company_elem = card.find("h4")
                    location_elem = card.find("span", class_="job-search-card__location")
                    link_elem = card.find("a", class_="base-card__full-link")
                    
                    if title_elem and company_elem:
                        job = {
                            "id": f"linkedin_{hash(title_elem.text + company_elem.text) % 1000000}",
                            "title": title_elem.get_text(strip=True),
                            "company": company_elem.get_text(strip=True),
                            "location": location_elem.get_text(strip=True) if location_elem else "Not specified",
                            "description": title_elem.get_text(strip=True),
                            "salary": "Not specified",
                            "job_url": link_elem.get("href", "") if link_elem else "",
                            "source": "LinkedIn",
                            "required_skills": extract_skills_from_text(title_elem.get_text()),
                            "experience_level": infer_experience_level(title_elem.get_text()),
                        }
                        jobs.append(job)
                except Exception:
                    continue
            
            print(f"   [PAGE] Page {page + 1}: Found {len(job_cards)} jobs")
            time.sleep(random.uniform(2, 4))
            
    except Exception as e:
        print(f"   [ERROR] LinkedIn error: {str(e)[:200]}")
    
    return jobs


def extract_skills_from_text(text: str) -> List[str]:
    """Extract common programming skills from text."""
    skills_dict = {
        "python": "Python", "javascript": "JavaScript", "typescript": "TypeScript",
        "java": "Java", "c++": "C++", "c#": "C#", "go": "Go", "rust": "Rust",
        "react": "React", "vue": "Vue", "angular": "Angular",
        "node.js": "Node.js", "django": "Django", "flask": "Flask", "fastapi": "FastAPI",
        "sql": "SQL", "mysql": "MySQL", "postgresql": "PostgreSQL", "mongodb": "MongoDB",
        "docker": "Docker", "kubernetes": "Kubernetes", "aws": "AWS", "gcp": "GCP",
        "git": "Git", "ci/cd": "CI/CD", "devops": "DevOps", "linux": "Linux",
        "machine learning": "Machine Learning", "tensorflow": "TensorFlow",
        "pandas": "pandas", "numpy": "numpy", "scikit-learn": "scikit-learn",
        "rest api": "REST API", "graphql": "GraphQL",
        "html": "HTML", "css": "CSS",
    }
    
    text_lower = text.lower()
    found_skills = []
    
    for skill_key, skill_name in skills_dict.items():
        if skill_key in text_lower:
            found_skills.append(skill_name)
    
    return list(set(found_skills))


def infer_experience_level(title: str) -> str:
    """Infer experience level from job title."""
    title_lower = title.lower()
    
    if any(word in title_lower for word in ["senior", "lead", "principal", "architect"]):
        return "Senior"
    elif any(word in title_lower for word in ["mid", "intermediate"]):
        return "Mid-level"
    elif any(word in title_lower for word in ["junior", "entry", "graduate"]):
        return "Junior"
    else:
        return "Not specified"


def _init_selenium_driver(driver_path: Optional[str] = None, headless: bool = True):
    """Initialize a Chrome WebDriver. Returns driver or None if not available."""
    if not SELENIUM_AVAILABLE:
        return None

    chrome_options = Options()
    if headless:
        chrome_options.add_argument("--headless=new")
        chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--window-size=1920,1080")

    try:
        if driver_path:
            driver = webdriver.Chrome(executable_path=driver_path, options=chrome_options)
        else:
            # Try to auto-install driver with webdriver-manager if available
            try:
                from webdriver_manager.chrome import ChromeDriverManager
                driver_path_auto = ChromeDriverManager().install()
                driver = webdriver.Chrome(executable_path=driver_path_auto, options=chrome_options)
            except Exception:
                driver = webdriver.Chrome(options=chrome_options)
        return driver
    except WebDriverException as e:
        print(f"[SELENIUM] WebDriver error: {e}")
        return None


def scrape_all_sources(keywords: str = "python developer", max_jobs: int = 100, use_selenium: bool = True) -> List[Dict[str, Any]]:
    """Scrape from ALL sources and save to database."""
    all_jobs = []
    
    print(f"\n{'='*60}")
    print(f"[SCRAPER] STARTING JOB SCRAPE: {keywords}")
    print(f"{'='*60}\n")

    # Initialize Selenium driver if requested and available
    driver = None
    if use_selenium:
        driver_path = os.getenv("CHROME_DRIVER_PATH") or None
        driver = _init_selenium_driver(driver_path=driver_path, headless=True)
        if driver:
            print("[SELENIUM] WebDriver initialized and will be used for dynamic pages")
        else:
            print("[SELENIUM] WebDriver not available; falling back to requests-based scraping")

    # Scrape from each source (pass driver to scrapers so they can use the same browser instance)
    indeed_jobs = scrape_indeed_jobs(keywords, pages=2, driver=driver)
    all_jobs.extend(indeed_jobs)
    
    github_jobs = scrape_github_jobs_api(keywords, pages=1)
    all_jobs.extend(github_jobs)
    
    linkedin_jobs = scrape_linkedin_jobs(keywords, pages=1, driver=driver)
    all_jobs.extend(linkedin_jobs)
    
    # Remove duplicates by ID
    unique_jobs = {job['id']: job for job in all_jobs}
    all_jobs = list(unique_jobs.values())
    
    # Limit to max_jobs
    all_jobs = all_jobs[:max_jobs]
    
    # Save to database
    print(f"\n[SUMMARY]")
    print(f"   Total jobs scraped: {len(all_jobs)}")
    
    try:
        saved_count = save_jobs_batch(all_jobs)
        print(f"   Saved to database: {saved_count}")
    except Exception as e:
        print(f"   Database save error: {e}")
        if driver:
            try:
                driver.quit()
            except Exception:
                pass
        return all_jobs
    
    print(f"\n[COMPLETE] Scraping complete!\n")
    if driver:
        try:
            driver.quit()
        except Exception:
            pass
    
    return all_jobs


def get_cached_jobs(max_results: int = 100) -> List[Dict[str, Any]]:
    """Get jobs from cache (database). If empty, scrape."""
    try:
        cached = get_all_jobs(limit=max_results)
        
        if cached and len(cached) > 0:
            return cached
        else:
            return scrape_all_sources(keywords="python developer", max_jobs=max_results)
    except Exception as e:
        print(f"Cache error: {e}")
        return []
