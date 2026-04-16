# Bangumi Anime Reception Analyst

## Live demo

Deployed website: `https://bangumi-data-analyst-agent-407136000438.us-central1.run.app/`

## Project description

This project is a multi-agent data analyst system for comparing two anime seasonal cohorts from **Bangumi.tv**, a Chinese community platform where users track, rate, and discuss anime and related media.

In this project, Bangumi is used as a **real runtime external data source**, not as a static dataset and not as a generic chatbot knowledge base.

The system is intentionally scoped around a concrete analyst workflow:

**Collect → Explore → Hypothesize**

- **Collect**: retrieve two anime seasonal cohorts from the official Bangumi API at runtime
- **Explore**: compute cohort-level and title-level comparison signals over the retrieved data
- **Hypothesize**: produce a narrow evidence-backed seasonal interpretation

This directly matches the Project 2 requirement to implement the first three steps of a real data analyst workflow with real-world data.

## Why Bangumi

Bangumi is a good fit for this project because:

- it is a real community-driven rating platform
- it has an official API for runtime retrieval
- it naturally supports anime seasonal cohort analysis
- it provides enough scale and variety to count as a non-trivial external dataset

This project uses Bangumi specifically as a runtime source for **anime reception analysis**. It is not a generic anime QA bot or recommendation system.

## System overview

The system has three layers:

1. **Data retrieval layer**
   - Bangumi API client
   - runtime seasonal cohort retrieval

2. **Analysis layer**
   - deterministic season-gap analysis
   - cohort summaries
   - title-level gap signals
   - artifact generation

3. **Agent layer**
   - orchestrator
   - retrieval specialist
   - EDA specialist
   - hypothesis specialist
   - critic specialist

A minimal frontend workbench is mounted inside the FastAPI app for interactive use.

## Deterministic path vs agent-backed path

### Deterministic path

Endpoint:

- `POST /api/v1/analysis/season-gap`

Purpose:

- retrieve two seasonal cohorts
- run the deterministic analysis pipeline
- return structured comparison results and artifacts

This is the stable baseline path.

### Agent-backed path

Endpoint:

- `POST /api/v1/agent/season-gap`

Purpose:

- orchestrate specialist agents over the same seasonal comparison task
- reuse the existing retrieval and analysis logic
- generate a final report
- run a critic check on the hypothesis

This path demonstrates the multi-agent layer without replacing the deterministic analytics core.

## Agent roles

The current multi-agent workflow includes:

- **Orchestrator**: controls the workflow and combines specialist outputs
- **Retrieval specialist**: performs runtime Bangumi retrieval only
- **EDA specialist**: analyzes prefetched rows only
- **Hypothesis specialist**: produces one narrow evidence-backed hypothesis
- **Critic specialist**: checks whether the hypothesis is supported by the evidence

This separation is intentional: different agents have different prompts and responsibilities, rather than one single persona pretending to be multiple roles.

## Runtime data source and artifacts

### Runtime data source

- official Bangumi API
- anime seasonal cohorts
- recommended comparison pair: `2025 spring` vs `2025 summer`

### Artifacts generated per run

- `combined_cohorts.csv`
- `summary.json`
- `score_vs_popularity.png`

Artifacts are written under:

- `outputs/runs/<timestamp_or_slug>/...`

They are also browsable through:

- `/outputs/...`

## Implemented concepts checklist

### Required concepts

- **Frontend**
  - `frontend/templates/index.html`
  - `frontend/static/app.js`
  - `frontend/static/styles.css`
  - `app/main.py`

- **Agent framework**
  - `app/agents/service.py`

- **Tool calling**
  - `app/agents/tools.py`

- **Non-trivial dataset**
  - `app/bangumi/client.py`

- **Multi-agent pattern**
  - `app/agents/service.py`
  - `app/agents/prompts.py`
  - `app/agents/backend.py`

- **Deployed application**
  - Cloud Run deployment
  - `Dockerfile`

- **README**
  - `README.md`

### Grab-Bag concepts

- **Artifacts**
  - `app/artifacts/files.py`
  - `app/artifacts/plotting.py`

- **Structured output**
  - `app/schemas.py`
  - `app/agents/models.py`

- **Data visualization**
  - `app/artifacts/plotting.py`
  - frontend preview in `frontend/static/app.js`

## How the three project steps are implemented

### Step 1: Collect

The system retrieves real Bangumi data at runtime from the official API. This is implemented in:

- `app/bangumi/client.py`
- `app/api/routes_analysis.py`
- `app/api/routes_agents.py`

### Step 2: Explore and Analyze (EDA)

The system computes over the collected cohort data rather than jumping directly to an answer. It performs aggregation, comparison, and gap analysis, and writes artifacts. This is implemented in:

- `app/analysis/season_gap.py`
- `app/artifacts/files.py`
- `app/artifacts/plotting.py`

### Step 3: Hypothesize

The system forms a narrow hypothesis from the analysis results and communicates supporting evidence.

- deterministic hypothesis construction:
  - `app/analysis/season_gap.py`
- agent hypothesis and critique:
  - `app/agents/service.py`
  - `app/agents/prompts.py`

## Local run

From the project root:

```powershell
uv sync
Copy-Item .env.example .env
notepad .env
uv run uvicorn app.main:app --reload
```

Then open:

```text
http://127.0.0.1:8000/
```

## How to use the deployed site

Open the live site:

- `https://bangumi-data-analyst-agent-407136000438.us-central1.run.app/`

Recommended flow:

1. Use:
   - Season A: `2025 spring`
   - Season B: `2025 summer`
2. Run **Agent** mode first if you want to highlight the multi-agent workflow
3. Run **Deterministic** mode if you want to show the stable baseline

### In Deterministic mode, check:

- `Summary / Comparison`
- `Hypothesis`
- `Artifacts`
- scatter plot preview

### In Agent mode, check:

- `final_report`
- `critic_verdict`
- `critic_feedback`
- raw orchestrator output in a secondary collapsible section
- artifacts and plot preview

## API endpoints

### Deterministic analysis

- `POST /api/v1/analysis/season-gap`

### Agent-backed analysis

- `POST /api/v1/agent/season-gap`

### Health check

- `GET /healthz`

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
