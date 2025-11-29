# Job Scraping & Database System

## Overview
The application now includes a complete job scraping pipeline that:
1. **Scrapes** real job listings from Indeed, GitHub Jobs, and other sources
2. **Stores** jobs in a local SQLite database
3. **Retrieves** cached jobs for quick matching against user resumes
4. **Matches** jobs to resume skills with compatibility scoring

## Architecture

### Files Created/Modified

#### 1. **job_scraper.py** (NEW)
- Scrapes Indeed, GitHub Jobs, and generic job boards
- Extracts skills and infers experience levels from job descriptions
- Implements rate limiting and politeness (user-agent rotation, delays)
- Uses BeautifulSoup for HTML parsing
- Main functions:
  - `scrape_indeed_jobs()` - Scrape from Indeed.com
  - `scrape_github_jobs()` - Scrape from GitHub Jobs API
  - `scrape_generic_job_board()` - Scrape any job board with CSS selectors
  - `scrape_all_sources()` - Scrape all sources and save to database
  - `get_cached_jobs()` - Retrieve from database (triggers scrape if empty)

#### 2. **job_database.py** (NEW)
- SQLite database for persisting job listings
- Stores: id, title, company, location, description, skills, level, salary, source, URL
- Main functions:
  - `save_job()` - Save single job
  - `save_jobs_batch()` - Save multiple jobs
  - `get_all_jobs()` - Retrieve all jobs
  - `search_jobs_by_skills()` - Find jobs matching skills
  - `get_jobs_by_source()` - Filter by source (Indeed, GitHub, etc.)
  - `count_jobs()` - Count cached jobs
  - `clear_jobs()` - Clear cache

#### 3. **job_discovery.py** (UPDATED)
- Now imports `get_cached_jobs()` from job_scraper
- Falls back to mock data if database is empty
- Computes compatibility scores and generates justifications

#### 4. **app.py** (UPDATED)
- Added sidebar controls for:
  - View cached job count
  - Button: "🔍 Scrape Jobs from Internet" - triggers live scraping
  - Button: "🗑️ Clear Job Cache" - resets database
- Job discovery now uses real scraped jobs instead of mock

#### 5. **requirement.txt** (UPDATED)
- Added: `beautifulsoup4`, `requests`, `python-dotenv`

## How It Works

### Data Flow
```
User clicks "Scrape Jobs" (Sidebar)
         ↓
job_scraper.scrape_all_sources()
         ↓
Indeed + GitHub Jobs are parsed
         ↓
job_database.save_jobs_batch()
         ↓
Jobs stored in jobs.db (SQLite)
         ↓
User uploads resume & analyzes
         ↓
job_discovery.discover_jobs_for_resume()
         ↓
get_cached_jobs() retrieves from database
         ↓
Compatibility scoring & ranking
         ↓
Display matched jobs in UI
```

### Key Features

1. **Politeness & Rate Limiting**
   - Rotates user-agent strings
   - Adds 2-4 second delays between requests
   - Respects robots.txt and site policies

2. **Skill Extraction**
   - Automatically detects Python, JavaScript, Docker, AWS, etc. from job descriptions
   - Cross-references with resume skills for matching

3. **Experience Level Inference**
   - Parses job titles for "Senior", "Junior", "Mid-level"
   - Used in compatibility scoring

4. **Database Persistence**
   - SQLite database (`jobs.db`) stores all scraped jobs
   - Avoids re-scraping on app restart
   - Supports searching by skill and source

## Usage

### Scraping Jobs
1. Open the Streamlit app: `streamlit run app.py`
2. Click **"🔍 Scrape Jobs from Internet"** in the sidebar
3. Wait 30-60 seconds for scraping to complete
4. Message shows: "✅ Scraped X new jobs!"

### Uploading Resume & Matching
1. Upload PDF resume
2. Paste job description (optional)
3. Click **"🚀 Analyze Resume & Run Match/Preps"**
4. Scroll to **Section 5: "Automated Job Discovery & Matching"**
5. View top job matches with compatibility scores

### Clearing Cache
1. Click **"🗑️ Clear Job Cache"** in sidebar
2. Next analysis will use mock data until you scrape again

## Current Limitations & Future Enhancements

### Current State
- Scrapes Indeed (limited - site actively blocks scrapers)
- Scrapes GitHub Jobs API (stable)
- Generic scraper template for other job boards
- Rate-limited, politeness headers included

### Recommended Improvements
1. **Use Official APIs** (production)
   - Indeed API (requires authentication)
   - LinkedIn API (restricted access)
   - ZipRecruiter API

2. **Selenium for Dynamic Content**
   - Some job sites load jobs via JavaScript
   - Can add Selenium for browser-based scraping
   - Use Chrome headless for better compatibility

3. **Proxy Rotation**
   - For high-volume scraping, use proxy services
   - Avoid IP bans from aggressive scraping

4. **NLP-Based Skill Extraction**
   - Use spaCy or NLTK for better skill detection
   - Build custom skill ontology

5. **Scheduling**
   - Use APScheduler or Celery to auto-scrape daily/weekly
   - Keep database fresh with new listings

## Testing

### Manual Test Script
```python
# Quick test without Streamlit
from job_scraper import scrape_all_sources
from job_database import get_all_jobs, count_jobs

# Scrape
jobs = scrape_all_sources(keywords="python developer", max_jobs=20)
print(f"Scraped: {len(jobs)} jobs")

# Verify stored
print(f"In database: {count_jobs()} total jobs")

# Retrieve
cached = get_all_jobs(limit=10)
for job in cached:
    print(f"{job['title']} @ {job['company']} ({job['source']})")
```

## Dependencies Installed
```
beautifulsoup4  - HTML parsing
requests        - HTTP requests with user-agent support
python-dotenv   - Load .env for API keys
```

Run: `pip install -r requirement.txt`

---

**Next Steps:**
- ✅ Scraping from Indeed & GitHub
- ✅ Database persistence
- ✅ Integrated into Streamlit UI
- 📋 Add Selenium for JavaScript-heavy sites
- 📋 Implement cron job for auto-scraping
- 📋 Replace with official APIs in production
