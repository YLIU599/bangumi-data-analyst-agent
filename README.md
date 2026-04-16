# Bangumi Anime Reception Analyst

## Project description

This project compares two Bangumi anime seasonal cohorts using runtime API retrieval, performs exploratory analysis, generates artifacts, and exposes both a deterministic analysis path and an agent-backed analysis path through a FastAPI app with a minimal browser demo.

The workflow is intentionally scoped around a concrete analyst loop:

**Collect → Explore → Hypothesize**

- **Collect**: fetch two seasonal anime cohorts from the official Bangumi API at runtime
- **Explore**: compute cohort-level and title-level comparison signals
- **Hypothesize**: produce a narrow evidence-backed seasonal interpretation

## What is Bangumi.tv?

Bangumi.tv is a Chinese community platform used to track and rate anime, manga, games, books, and related media. In this project, Bangumi is used as the runtime external data source because:

- it is a real community-driven rating source rather than a toy dataset
- it has an official API, so the project can do live retrieval instead of static CSV-only analysis
- it fits the seasonal anime comparison use case naturally
- it is also a platform I already use, which made the project direction practical and interpretable

This project uses Bangumi.tv specifically as a runtime anime cohort source, not as a generic chatbot knowledge base.

## System architecture

The system has three layers:

1. **Data retrieval layer**
   - official Bangumi API client
   - seasonal cohort retrieval at runtime

2. **Analysis layer**
   - deterministic season gap analysis
   - cohort summaries
   - title-level gap signals
   - artifact generation

3. **Agent layer**
   - orchestrated multi-agent workflow built on top of the existing analysis flow
   - retrieval specialist
   - EDA specialist
   - hypothesis specialist
   - critic specialist

A minimal frontend workbench is mounted inside the FastAPI app for local demo and submission use.

## Deterministic path vs agent-backed path

### Deterministic path

Endpoint:

- `POST /api/v1/analysis/season-gap`

Purpose:

- fetch two seasonal cohorts
- run the existing season gap analysis
- return structured summaries and artifacts

This is the stable baseline path and the best first demo step.

### Agent-backed path

Endpoint:

- `POST /api/v1/agent/season-gap`

Purpose:

- orchestrate specialist agents over the same seasonal comparison task
- preserve the existing retrieval/analysis logic
- generate a final report
- run a critic check on the hypothesis

This path demonstrates the multi-agent layer rather than replacing the deterministic analytics core.

## Agent roles

The current agent workflow includes these roles:

- **Orchestrator**: coordinates the analysis workflow
- **Retrieval specialist**: performs runtime Bangumi retrieval only
- **EDA specialist**: consumes prefetched rows and produces descriptive findings only
- **Hypothesis specialist**: proposes one narrow evidence-backed hypothesis
- **Critic specialist**: checks whether the hypothesis is supported by the evidence

This separation keeps the retrieval / EDA / hypothesis / critique responsibilities explicit.

## Runtime data source and artifacts

### Runtime data source

- official Bangumi API
- anime seasonal cohorts
- examples used in demo: `2025 spring` vs `2025 summer`

### Artifacts generated per run

- `combined_cohorts.csv`
- `summary.json`
- `score_vs_popularity.png`

Artifacts are written under:

- `outputs/runs/<timestamp_or_slug>/...`

They are also browsable locally through:

- `/outputs/...`

## Local setup (Windows 11 PowerShell)

### 1. Enter the project directory

```powershell
cd .\bangumi_scaffold
```

### 2. Sync dependencies

```powershell
uv sync
```

### 3. Create `.env` if needed

```powershell
if (-not (Test-Path .env)) { Copy-Item .env.example .env }
notepad .env
```

### 4. Minimum `.env` values

For deterministic mode:

- `BANGUMI_TOKEN`
- `BANGUMI_USER_AGENT`

For agent mode, also make sure these are valid in your environment:

- `AGENT_MODEL`
- `VERTEX_PROJECT`
- `VERTEX_LOCATION`

If agent mode uses Vertex, also ensure local Google auth is configured, for example:

```powershell
gcloud auth application-default login
```

## How to run backend

```powershell
uv run uvicorn app.main:app --reload
```

## How to open frontend

Open this in the browser:

```text
http://127.0.0.1:8000/
```

## How to demo deterministic mode

Recommended first run:

- Season A: `2025` + `spring`
- Season B: `2025` + `summer`
- Mode: `Deterministic`

Expected UI outputs:

- **Summary / Comparison**
- **Hypothesis**
- **Artifacts**
- scatter plot preview

PowerShell API check:

```powershell
$body = @{
  season_a = @{ year = 2025; season = "spring" }
  season_b = @{ year = 2025; season = "summer" }
  page_limit = 4
  per_page = 25
  top_n = 5
  min_rating_total = 30
} | ConvertTo-Json -Depth 5

Invoke-RestMethod `
  -Method Post `
  -Uri "http://127.0.0.1:8000/api/v1/analysis/season-gap" `
  -ContentType "application/json" `
  -Body $body | ConvertTo-Json -Depth 8
```

## How to demo agent mode

After deterministic mode is confirmed, switch:

- Mode: `Agent`

Expected UI outputs:

- **Summary / Comparison**: main display now prioritizes `final_report`
- **Hypothesis**
- **Critic**
  - verdict badge
  - critic feedback
- **Raw orchestrator output** in a secondary collapsible section
- **Artifacts**

PowerShell API check:

```powershell
$body = @{
  season_a = @{ year = 2025; season = "spring" }
  season_b = @{ year = 2025; season = "summer" }
  page_limit = 4
  per_page = 25
  top_n = 5
  min_rating_total = 30
} | ConvertTo-Json -Depth 5

Invoke-RestMethod `
  -Method Post `
  -Uri "http://127.0.0.1:8000/api/v1/agent/season-gap" `
  -ContentType "application/json" `
  -Body $body | ConvertTo-Json -Depth 8
```

## Project structure

```text
app/
  agents/        multi-agent workflow, prompts, models, tools, service
  analysis/      deterministic seasonal comparison logic
  api/           FastAPI routes
  artifacts/     artifact writing and plotting
  bangumi/       Bangumi API client
  core/          config
  schemas.py     shared request/response schemas
  main.py        FastAPI app entrypoint

frontend/
  templates/     HTML template for the demo page
  static/        JS and CSS for the demo page

scripts/
  run_spike.py
  run_agent_seasonal.py

tests/
  test_analysis.py

outputs/
  runtime-generated artifacts
```

## Mapping from course requirements to code locations

### Runtime external data source

- `app/bangumi/client.py`
- `app/api/routes_analysis.py`
- `app/api/routes_agents.py`

### Real exploratory analysis

- `app/analysis/season_gap.py`
- `app/artifacts/plotting.py`
- `app/artifacts/files.py`

### Evidence-backed hypothesis generation

- deterministic hypothesis construction: `app/analysis/season_gap.py`
- agent hypothesis + critique: `app/agents/service.py`, `app/agents/prompts.py`

### Multi-agent structure

- `app/agents/service.py`
- `app/agents/prompts.py`
- `app/agents/tools.py`
- `app/agents/models.py`
- `app/agents/backend.py`

### Web app / deployment-ready structure

- app entrypoint: `app/main.py`
- frontend demo: `frontend/templates/index.html`, `frontend/static/app.js`, `frontend/static/styles.css`
- local artifact serving: `app/main.py`
- containerization stub: `Dockerfile`

## Notes

- `outputs/` is created safely at startup if it does not already exist.
- `/static` serves frontend assets.
- `/outputs` serves generated local artifacts.
- the frontend is intentionally a small analysis workbench rather than a general chat UI.
