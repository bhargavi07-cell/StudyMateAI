# StudyMate AI – Intelligent Student Study Planner

A hackathon-ready Streamlit prototype that helps students organize subjects, topics, exams, and study hours. It includes an explainable rule-based priority engine, a conflict-free timetable generator, progress tracking, charts, reminders, demo data, and an optional AI API connection with a useful offline fallback.

## Problem statement

College students must balance several subjects, difficult topics, upcoming exams, and limited study hours. Manual planners are time-consuming and often fail to adapt when deadlines or workloads change.

## Solution

StudyMate AI turns a student's subjects, exam dates, topic difficulty, remaining hours, subject importance, and daily availability into a prioritized study plan. Recommendations are explainable: each score shows the factors that influenced it. Students can mark topics complete and regenerate the timetable as their workload changes.

## Features

- **Dashboard:** today's scheduled sessions, completion metrics, remaining hours, upcoming exams, and study-load chart.
- **Personalized planner:** add/delete subjects and add topics with difficulty and estimated hours.
- **Smart timetable:** schedules sessions in sequential blocks within a configured daily time window and hour cap; no overlapping sessions.
- **Explainable priority engine:** score uses exam urgency (40%), difficulty (30%), remaining workload (20%), and subject importance (10%). Completed topics score zero.
- **Task tracking:** mark topics complete, edit estimated hours and difficulty, and view overall and subject progress.
- **Progress analytics:** interactive Plotly charts.
- **Reminders:** upcoming exam countdowns appear on the dashboard.
- **Study assistant:** optional OpenAI-compatible API using `OPENAI_API_KEY`; if no key is configured, an offline strategy assistant remains available. Offline mode does not pretend to generate custom textbook facts.
- **Demo mode:** realistic sample subjects are loaded automatically; use **Reset demo data** in the sidebar to restore them.
- **Local persistence:** edits are saved to `studymate_data.json` in the app directory.

## Project files

- `app.py` — Streamlit interface and interactions
- `planner.py` — testable priority scoring and timetable logic
- `tests/test_planner.py` — automated logic tests
- `sample_data.json` — sample-data schema/config starter

## Technology stack

- Python 3
- Streamlit
- Pandas
- Plotly
- Python `datetime`, `json`, and `uuid`
- Optional OpenAI-compatible Chat Completions API via Python standard library `urllib`

## Run locally

1. Install Python 3.10 or newer.
2. Unzip the project and open a terminal in the `studymate_ai` folder.
3. Create and activate a virtual environment:

   **Windows PowerShell**
   ```powershell
   py -m venv .venv
   .\.venv\Scripts\Activate.ps1
   ```

   **macOS/Linux**
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   ```

4. Install dependencies:
   ```bash
   python -m pip install --upgrade pip
   pip install -r requirements.txt
   ```
5. Start the app:
   ```bash
   streamlit run app.py
   ```
6. Streamlit will print a local URL, usually `http://localhost:8501`. Open it in your browser.

No API key is needed for the core app.

## Optional AI API

Set `OPENAI_API_KEY` in the environment before starting Streamlit. The app uses the OpenAI-compatible `/v1/chat/completions` endpoint and defaults to `gpt-4o-mini`. You can override the model with `STUDYMATE_AI_MODEL`.

**Windows PowerShell**
```powershell
$env:OPENAI_API_KEY="your-key"
$env:STUDYMATE_AI_MODEL="gpt-4o-mini"
streamlit run app.py
```

**macOS/Linux**
```bash
export OPENAI_API_KEY="your-key"
export STUDYMATE_AI_MODEL="gpt-4o-mini"
streamlit run app.py
```

The optional API may incur provider charges. Core planning does not use the API.

## Run tests

```bash
pytest -q
```

Tests cover priority ranking and explanations, daily capacity, session overlap, past exams, and empty schedules.

## Deploy

### Streamlit Community Cloud
1. Push the project to a GitHub repository.
2. Go to [Streamlit Community Cloud](https://share.streamlit.io/) and create an app from that repository.
3. Set the main file path to `app.py`.
4. Deploy. Add `OPENAI_API_KEY` and optionally `STUDYMATE_AI_MODEL` under app secrets/environment configuration only if you want the API integration.
5. Note: Community Cloud filesystems may not be durable across restarts/redeploys. For persistent multi-user production data, connect a database rather than relying on the local JSON file.

### Other hosting
Use a Python host that supports long-running Streamlit processes. Install `requirements.txt`, expose Streamlit's configured port, and keep user data in a persistent volume or database.

## 2–3 minute judge demo flow

1. **Dashboard (20 sec):** point out study hours, completion, and upcoming exam cards.
2. **Planner (35 sec):** add a sample subject such as “Operating Systems,” set an exam date, and add “CPU scheduling” and “Deadlocks” topics with different difficulty levels.
3. **Priority Engine (25 sec):** show the explainable score and why the nearest/hardest topic rises.
4. **Smart Timetable (35 sec):** generate the next seven days, show sequential sessions, and download CSV.
5. **Tasks & Progress (20 sec):** mark a topic complete and show progress change.
6. **AI Study Assistant (20 sec):** ask for a revision plan. Demonstrate offline fallback or configure an API key before the presentation.
7. **Close (10 sec):** explain that the planner uses transparent rules rather than claiming a trained ML model.

## Design and implementation notes

- Responsive layout is provided by Streamlit's column and container layout.
- The schedule uses a greedy priority-first algorithm. Sessions are sequential, capped at one hour, fit inside the configured same-day start/end window, and never exceed the daily hours cap.
- The schedule does not place sessions after the related exam date.
- Priority scoring is heuristic and explainable; it is **not** a trained machine-learning model.
- The offline assistant provides study methods and revision frameworks. It does not claim to know course-specific answers without content.

## Limitations and future improvements

- Scheduling is a deterministic heuristic, not an optimizer; it may not find the mathematically best allocation.
- Data is stored in a local JSON file, suited to a single-user prototype, not concurrent multi-user use.
- Study sessions are scheduled from a single daily time window; breaks and calendar integrations are not modeled.
- Past-exam topics are excluded from new schedules but remain visible so users can update their dates or mark completion.
- A production version could add authentication, SQLite/PostgreSQL, calendar sync, spaced-repetition intervals, richer course-material grounding, and a trained recommendation model evaluated on real student outcomes.
