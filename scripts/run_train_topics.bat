@echo off
echo ---- %DATE% %TIME% ---- >> "C:\Users\Administrator\Desktop\Scrapping\logs\train_topics.log"
"C:\Users\Administrator\Desktop\Scrapping\.venv\Scripts\python.exe" "C:\Users\Administrator\Desktop\Scrapping\modeling\train_topics.py" >> "C:\Users\Administrator\Desktop\Scrapping\logs\train_topics.log" 2>&1
