from job_database import count_jobs, get_all_jobs

print(f"Total jobs in database: {count_jobs()}")
jobs = get_all_jobs(limit=5)
for job in jobs:
    print(f"  - {job['title']} @ {job['company']} ({job['source']})")
