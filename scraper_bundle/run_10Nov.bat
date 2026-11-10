@echo off
rem C/V/D delivery scraper - Windows launcher (resumable)
cd /d "%~dp0"
python run_new_pages.py --input input.xlsx --output hiring_10Nov_CVD_delivery.csv --workers 25