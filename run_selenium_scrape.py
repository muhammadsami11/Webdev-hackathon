"""Helper to run a Selenium-powered scrape from the command line.

Usage (after activating venv):
    pip install selenium webdriver-manager
    python run_selenium_scrape.py "python developer" --max 30

This script will initialize a Chrome WebDriver via webdriver-manager (if installed)
or use the `CHROME_DRIVER_PATH` env var if provided, run `scrape_all_sources(..., use_selenium=True)`
and print a summary.
"""
import argparse
import os
from job_scraper import scrape_all_sources, _init_selenium_driver


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("keywords", help="Search keywords, e.g. 'python developer'")
    parser.add_argument("--max", type=int, default=50, help="Max jobs to collect")
    parser.add_argument("--headless", action="store_true", help="Run Chrome headless")
    args = parser.parse_args()

    driver_path = os.getenv("CHROME_DRIVER_PATH") or None
    driver = _init_selenium_driver(driver_path=driver_path, headless=args.headless)
    use_selenium = bool(driver)

    print(f"Using Selenium: {use_selenium}")

    try:
        jobs = scrape_all_sources(args.keywords, max_jobs=args.max, use_selenium=use_selenium)
        print(f"Scraped {len(jobs)} jobs (requested {args.max})")
    finally:
        if driver:
            try:
                driver.quit()
            except Exception:
                pass


if __name__ == "__main__":
    main()
