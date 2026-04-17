# Bangumi Anime Reception Analyst

## Live demo
https://bangumi-data-analyst-agent-407136000438.us-central1.run.app

## Project overview

This project is a deployed **multi-agent data analyst system** for Bangumi.tv, a Chinese anime rating and community website. It uses the official Bangumi API as a **runtime external data source** and is scoped around a concrete analyst workflow:

**Collect → Explore → Hypothesize**

- **Collect:** retrieve seasonal anime cohorts from the Bangumi API at runtime
- **Explore:** compute cohort-level and title-level comparison signals
- **Hypothesize:** produce an evidence-backed interpretation and check it with a critic

The frontend supports both structured seasonal comparison and a topic-limited Bangumi DA chat interface for follow-up questions.

## Why Bangumi

Bangumi is a strong fit for this project because it is:

- a real community-driven anime rating platform
- accessible through an official API
- naturally suited to seasonal cohort analysis
- rich enough to count as a non-trivial external dataset

This project uses Bangumi specifically for **anime reception analysis**, not as a general anime chatbot.

## System architecture

The system has four layers:

1. **Retrieval layer**
   - runtime Bangumi API client
   - seasonal cohort fetching

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

4. **Frontend interaction layer**
   - seasonal comparison workbench
   - Bangumi DA follow-up chat
   - artifact and cover preview

## Core paths

### Deterministic analysis
Endpoint:
- `POST /api/v1/analysis/season-gap`

Purpose:
- compare two selected seasons
- return structured comparison results
- generate artifacts

### Agent-backed analysis
Endpoint:
- `POST /api/v1/agent/season-gap`

Purpose:
- orchestrate specialist agents over the same comparison task
- generate a final report
- run a critic check on the conclusion

### Topic-limited Bangumi DA chat
Endpoint:
- `POST /api/v1/chat/season-gap`

Purpose:
- answer English follow-up questions about Bangumi seasonal analysis
- support year-level questions such as:
  - `Which season was more popular in 2012?`
  - `Which season had the highest average score in 2025?`
  - `What are the top rated anime in spring 2024?`
  - `What are the most popular anime in 2023?`

The chat is intentionally restricted to Bangumi data-analysis topics such as score, popularity, standout titles, hypotheses, and season-level comparisons.

## Agent roles

- **Orchestrator:** coordinates the multi-agent workflow
- **Retrieval specialist:** performs runtime Bangumi retrieval
- **EDA specialist:** analyzes retrieved cohort data
- **Hypothesis specialist:** writes a narrow evidence-backed interpretation
- **Critic specialist:** checks whether the interpretation is adequately supported

This follows the course’s multi-agent pattern more directly than a single agent with multiple labels.

## Runtime data and artifacts

### Runtime source
- official Bangumi API
- anime seasonal cohorts
- recommended comparison pair: `2025 spring` vs `2025 summer`

### Generated artifacts
- `combined_cohorts.csv`
- `summary.json`
- `score_vs_popularity.png`

Artifacts are written under:
- `outputs/runs/<timestamp_or_slug>/...`

They are also exposed through:
- `/outputs/...`

## Course requirement mapping

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

### Additional implemented concepts

- **Artifacts**
  - `app/artifacts/files.py`
  - `app/artifacts/plotting.py`

- **Structured output**
  - `app/schemas.py`
  - `app/agents/models.py`

- **Data visualization**
  - `app/artifacts/plotting.py`
  - frontend artifact preview in `frontend/static/app.js`

## How Collect → Explore → Hypothesize is implemented

### Collect
Real Bangumi data is retrieved at runtime in:
- `app/bangumi/client.py`
- `app/api/routes_analysis.py`
- `app/api/routes_agents.py`
- `app/api/routes_chat.py`

### Explore
Collected cohort data is analyzed, summarized, and written to artifacts in:
- `app/analysis/season_gap.py`
- `app/artifacts/files.py`
- `app/artifacts/plotting.py`
- `app/chat/service.py`

### Hypothesize
Evidence-backed conclusions are produced in:
- `app/analysis/season_gap.py`
- `app/agents/service.py`
- `app/agents/prompts.py`
- `app/chat/service.py`

## How to use the live site

1. Open the live demo
2. Pick two seasons and run either:
   - **Deterministic** for the direct baseline
   - **Agent** for the multi-agent report + critic check
3. Review:
   - summary / comparison
   - hypothesis
   - critic verdict
   - artifacts and plot preview
4. Use the chat panel for follow-up Bangumi DA questions

Recommended starting pair:
- `2025 spring` vs `2025 summer`

## Local run

```powershell
uv sync
Copy-Item .env.example .env
notepad .env
uv run python -m uvicorn app.main:app --reload
```

Open:
- `http://127.0.0.1:8000/`

## API endpoints

- `POST /api/v1/analysis/season-gap`
- `POST /api/v1/agent/season-gap`
- `POST /api/v1/chat/season-gap`
- `GET /healthz`

## Project structure

```text
app/
  agents/        multi-agent workflow, prompts, tools, service
  analysis/      deterministic seasonal comparison logic
  api/           FastAPI routes
  artifacts/     artifact writing and plotting
  bangumi/       Bangumi API client
  chat/          Bangumi DA chat service
  core/          config
  schemas.py     shared request/response schemas
  main.py        FastAPI entrypoint

frontend/
  templates/     HTML template
  static/        JS, CSS, images

scripts/
  run_spike.py
  run_agent_seasonal.py

tests/
  test_analysis.py

outputs/
  runtime-generated artifacts
```
