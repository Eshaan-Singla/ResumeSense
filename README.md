# ResumeSense · AI Resume Intelligence Suite

ResumeSense is an end‑to‑end resume intelligence platform that ingests PDF resumes, compares them against job descriptions, and returns targeted recommendations in seconds. Under the hood it combines NLP pipelines, ML scoring, ATS heuristics, and a modern web front end so job seekers (or career coaches) can iterate quickly with data they trust.

---

## Table of Contents

1. [Core Capabilities](#core-capabilities)  
2. [System Architecture](#system-architecture)  
3. [Quick Start](#quick-start)  
4. [.env Configuration](#env-configuration)  
5. [Daily Developer Workflow](#daily-developer-workflow)  
6. [Feature Deep Dive](#feature-deep-dive)  
7. [REST API Reference](#rest-api-reference)  
8. [Frontend Experience](#frontend-experience)  
9. [Testing & Quality](#testing--quality)  
10. [Troubleshooting Playbook](#troubleshooting-playbook)  
11. [Deployment Notes](#deployment-notes)  
12. [Roadmap & Contributions](#roadmap--contributions)

---

## Core Capabilities

- **Resume ingestion & cleaning** – PyMuPDF extracts raw text, custom cleaners normalize bullets, headers, and spacing.
- **JD ↔ Resume matching** – Semantic keyword engine weighs scientific/technical phrases heavier than filler language, returning match %, top overlaps, and gaps.
- **ATS compliance auditor** – Section detection, contact validation, formatting heuristics, and prescriptive recommendations.
- **Action verb diagnostics** – Finds weak verbs in context and proposes stronger alternatives alongside usage stats.
- **ML quality scoring** – Feature extractor (22 engineered signals) feeds a Random Forest model with rule‑based fallback.
- **Projects & achievements intelligence** – Dedicated parser surfaces technical projects (with tech stack) and co‑curricular achievements directly in the UI.
- **Analysis history** – Every run persists to MySQL for later review, comparison, or API retrieval.

---

## System Architecture

```
┌───────────────┐      ┌────────────────┐      ┌───────────────────────┐
│  Frontend     │ ---> │ Flask REST API │ ---> │ NLP/ML Pipelines       │
│ (HTML/CSS/JS) │      │ /api/*         │      │ • PDF parser (PyMuPDF) │
│               │ <--- │ JSON responses │ <--- │ • JD matcher           │
└───────────────┘      └────────────────┘      │ • ATS checker          │
                                               │ • Power verbs          │
                                               │ • Resume insights      │
                                               │ • Quality scorer       │
                                               └──────────┬─────────────┘
                                                          │
                                                    ┌─────▼──────┐
                                                    │   MySQL    │
                                                    │ (history)  │
                                                    └────────────┘
```

---

## Quick Start

### 1. Requirements
- Python **3.8+** (3.11+ recommended)
- MySQL **5.7+** / MariaDB equivalent
- `pip`, `virtualenv`

### 2. Installation
```bash
git clone https://github.com/<you>/ResumeSense.git
cd ResumeSense-
python -m venv venv
source venv/bin/activate            # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 3. Database
```sql
CREATE DATABASE resumesense;
```
> Optional: skip this step if the configured MySQL user can create databases—the backend will create it on first run.

### 4. Configuration
Copy `env.example` → `.env` and fill in secrets (see [section](#env-configuration)).

### 5. Run
```bash
python run.py
```
Visit `http://localhost:5001` (default host is `0.0.0.0`, port `5001`).

### 6. (Optional) Train ML model
```bash
python backend/ml/train_model.py
```
Creates `backend/ml/resume_quality_model.pkl`. If skipped, the rule-based scorer stays active.

---

## .env Configuration

```env
# Flask
SECRET_KEY=change-me

# Database
MYSQL_HOST=localhost
MYSQL_PORT=3306
MYSQL_USER=root
MYSQL_PASSWORD=your-password
MYSQL_DATABASE=resumesense

# Files / Models
UPLOAD_FOLDER=data/resumes
ML_MODEL_PATH=backend/ml/resume_quality_model.pkl
```

Tips:
- Use dedicated DB users per environment.
- Point `UPLOAD_FOLDER` to persistent storage if running in containers.
- Keep `.env` out of version control (`.gitignore` already covers it).

---

## Daily Developer Workflow

1. **Activate venv** – `source venv/bin/activate`
2. **Run backend** – `python run.py`
3. **Iterate** – Update backend/frontend files; hot reload is enabled via Flask debug mode.
4. **Lint/Test** – `python -m pytest backend/tests`
5. **Commit** – Feature branches only; follow the lightweight Git workflow described in `README`.

Project layout reminder:

```
backend/
  api/          Flask blueprints
  nlp/          PDF parser, JD matcher, ATS checker, power verbs, insights
  ml/           Feature extractor, scorer, training utilities
  db/           MySQL helpers
frontend/
  templates/    index.html, history.html
  static/       css/, js/
data/
  resumes/, jds/ sample artifacts
```

---

## Feature Deep Dive

| Module | Highlights |
|--------|------------|
| **PDF Parser** | Normalizes bullets, strips headers, preserves sentence boundaries for downstream analyzers. |
| **JD Matcher** | Weighted overlap (70% scientific/technical terms, 30% general keywords), richer stop-word list to ignore hiring fluff, detailed matched vs missing keywords list. |
| **ATS Checker** | Heading-aware section detection, regex-based contact validation, table/header heuristics, and recommendation engine tuned for real ATS behavior. |
| **Power Verb Suggester** | Detects weak verbs in context, returns replacements plus stats block (strong vs weak counts, “power verb” score). |
| **Resume Insights (Projects & Achievements)** | Section-aware parser pinpoints technical projects, infers tech stack, and separates co-curricular achievements with impact verbs. Surfaces in a tabbed UI. |
| **Quality Scorer** | 22 handcrafted features → Random Forest (or deterministic fallback) producing 0‑100 quality score with feature breakdown. |
| **History** | Every analysis (resume text, JD, scores) persists for GET `/api/history`, `/api/analysis/<id>`, or frontend browsing. |

---

## REST API Reference

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/analyze` | `POST` (multipart/form-data) | Analyze uploaded PDF or raw text with optional job description. Returns scores, ATS report, power verbs, insights, and database IDs. |
| `/api/history?limit=20` | `GET` | Paginated list of past analyses with previews. |
| `/api/analysis/<id>` | `GET` | Full payload for a specific analysis record. |
| `/api/resume/<id>` | `GET` | Raw resume text + timestamps. |

Typical `POST /api/analyze` response (trimmed):

```json
{
  "match_score": 82.7,
  "match_details": {
    "common_keywords": ["python","kubernetes","ci/cd"],
    "missing_keywords": ["terraform","graphql"],
    "matched_important_keywords": ["Machine Learning", "AWS Lambda"],
    "important_keywords_matched": 6,
    "important_keywords_total": 10
  },
  "ats_score": 91.2,
  "ats_report": {
    "issues": [],
    "recommendations": ["Use bullet points to improve readability"],
    "section_checks": { "education": true, "experience": true, ... },
    "contact_check": { "has_email": true, "has_phone": true, "complete": true },
    "formatting_checks": { "has_tables": false, ... }
  },
  "power_verbs": {...},
  "resume_insights": {
    "projects": [{ "title": "...", "tech_stack": ["Python","React"] }],
    "achievements": [...]
  },
  "quality_score": 88.4,
  "analysis_id": 42
}
```

---

## Frontend Experience

- **Analyze tab** – Upload resume + optional JD, watch cards animate for Quality, ATS, and Match scores.
- **ATS panel** – Issues and recommendations rendered as alert chips for fast scanning.
- **Power Verbs panel** – Highlights weak verbs inline with suggested replacements.
- **Match panel** – “Matched / Missing / Important” keyword pills.
- **Projects & Achievements tabs** – Newly added tabbed panel surfaces extracted technical projects (with inferred tech stack badges) and co-curricular achievements.
- **History tab** – Chronological list of previous analyses with quick score snapshots.

No frontend frameworks are required; everything is vanilla HTML/CSS/JS, making it easy to embed or restyle.

---

## Testing & Quality

```bash
python -m pytest backend/tests
```

Test suites cover:
- PDF parsing edge cases (`test_pdf_parser.py`)
- JD matcher scoring (`test_jd_matcher.py`)
- ATS compliance heuristics (`test_ats_checker.py`)
- Power verb suggestions (`test_power_verbs.py`)

Add new tests alongside new NLP/ML helpers to keep regression coverage high.

---

## Troubleshooting Playbook

| Symptom | Likely Cause | Fix |
|---------|--------------|-----|
| `'cryptography' package is required` | PyMySQL + caching_sha2 auth | `pip install cryptography` inside the venv. |
| `Unknown database 'resumesense'` | DB not created yet | Ensure MySQL user can create DB or run `CREATE DATABASE resumesense;`. |
| PyMuPDF build fails on Windows | Visual Studio Build Tools missing | Install “Desktop Development with C++” workload or use Python 3.12 where wheels exist. |
| Resume text empty | PDF is scanned images | Convert to selectable text or use OCR before uploading. |
| ATS report flags missing sections incorrectly | Resume uses uncommon headings | Rename headings to standard ones (“Experience”, “Skills”, etc.) or enhance `_looks_like_heading`. |
| Frontend stops responding | Flask crashed | Check terminal logs; most errors propagate with stack traces. |

---

## Deployment Notes

- **Procfile (Heroku / Render)**: `web: gunicorn run:app`
- **Gunicorn command**: `gunicorn run:app --bind 0.0.0.0:$PORT`
- **Environment**: set `FLASK_ENV=production`, unique `SECRET_KEY`, and production DB credentials.
- **Static files**: served by Flask; for CDNs, point to `frontend/static`.
- **Uploads**: ensure `UPLOAD_FOLDER` is writable (mount persistent volume or S3 adapter).

---

## Roadmap & Contributions

- [ ] DOCX ingestion & OCR fallback
- [ ] Transformer-based semantic matcher
- [ ] Exportable PDF/HTML reports
- [ ] Multi-user workspace & sharing
- [ ] Job board integrations

Contributions are welcome!  
1. Fork → Branch → PR  
2. Write/extend tests  
3. Document any configuration changes

---

Built with ❤️ for job seekers, recruiters, and career coaches who want feedback they can trust. Happy analyzing!


