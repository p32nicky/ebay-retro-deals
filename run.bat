@echo off
cd /d "%~dp0"

python scraper.py

git add feed.xml
git diff --cached --quiet && echo No changes || (git commit -m "Update RSS feed %date%" && git push)
