Selenium Setup (Optional)

To enable browser-based scraping for sites that render content with JavaScript (e.g., Indeed, LinkedIn), follow these steps inside your project's virtual environment:

1. Activate venv and install Selenium + webdriver-manager:

```powershell
cd C:\Users\i222514\Desktop\Saqib
.\venv\Scripts\Activate.ps1
pip install selenium webdriver-manager
```

2. Option A — Let `webdriver-manager` auto-download the correct ChromeDriver (recommended): no further action required.

3. Option B — Provide your own ChromeDriver binary and set `CHROME_DRIVER_PATH` env var:

```powershell
$env:CHROME_DRIVER_PATH = 'C:\path\to\chromedriver.exe'
```

4. Run the Selenium scraping helper (this will attempt to use Selenium and fall back if unavailable):

```powershell
python run_selenium_scrape.py "python developer" --max 20 --headless
```

Notes:
- Selenium headless mode is enabled via `--headless` flag.
- If a WebDriver cannot be initialized, `job_scraper` will fall back to non-Selenium requests-based scraping.
- Respect site terms of service. Use rate-limiting and proxies for larger scraping tasks.
