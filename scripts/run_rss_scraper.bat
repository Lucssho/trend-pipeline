@echo off
echo ---- %DATE% %TIME% ---- >> "C:\Users\Administrator\Desktop\Scrapping\logs\rss_scraper.log"
"C:\Users\Administrator\Desktop\Scrapping\.venv\Scripts\python.exe" "C:\Users\Administrator\Desktop\Scrapping\scraper\rss_scraper.py" >> "C:\Users\Administrator\Desktop\Scrapping\logs\rss_scraper.log" 2>&1
"C:\Users\Administrator\Desktop\Scrapping\.venv\Scripts\python.exe" "C:\Users\Administrator\Desktop\Scrapping\dashboard\generate_data.py" >> "C:\Users\Administrator\Desktop\Scrapping\logs\rss_scraper.log" 2>&1
