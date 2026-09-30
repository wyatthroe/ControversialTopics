# Trending Topic Finder

A small Python console tool that uses Twikit to fetch Twitter/X trends and list topics that match a visible keyword rubric for polarizing public issues. It does not use an official X API, and the matches are heuristic rather than an objective measure of controversy.

## Setup

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

## Run

```powershell
python main.py
python main.py --limit 100
python main.py --location "United States"
python main.py --json
```

Trends are fetched without account credentials. Location names must match one of the locations Twikit reports. The JSON option prints an array of topic names, matching signal categories, and post counts when available.

Twitter/X may change its website endpoints or restrict scraping; Twikit's trend retrieval can stop working when that happens. Use the data in accordance with X's terms and applicable law.