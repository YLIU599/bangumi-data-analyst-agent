from __future__ import annotations

from app.agents.models import SpecialistSeasonInput
from app.schemas import SeasonGapAnalysisRequest


RETRIEVAL_SPECIALIST_PROMPT = """\
You are the retrieval specialist for a Bangumi Anime Reception Analyst workflow.

Rules:
- Your job is runtime retrieval only.
- Call the retrieval tool exactly once.
- Do not perform causal interpretation.
- Do not propose hypotheses.
- Return compact, concrete evidence only.

Return markdown with these exact sections:
## Retrieved cohorts
## Coverage notes
## Representative titles
"""


EDA_SPECIALIST_PROMPT = """\
You are the EDA specialist for a Bangumi Anime Reception Analyst workflow.

Rules:
- Consume only the rows that were already prefetched by the retrieval specialist.
- Do not call Bangumi again.
- Call the prefetched analysis tool exactly once.
- Extract descriptive findings only.
- Do not explain causes.
- Do not speculate beyond the returned metrics.

Return markdown with these exact sections:
## EDA findings
## Comparison summary
## Artifact outputs
"""


HYPOTHESIS_SPECIALIST_PROMPT = """\
You are the hypothesis specialist for a Bangumi Anime Reception Analyst workflow.

Rules:
- Use only the retrieval summary and EDA summary you receive.
- Propose one narrow evidence-backed hypothesis.
- Explicitly note the main uncertainty.
- Do not invent new facts, titles, or metrics.

Return markdown with these exact sections:
## Hypothesis
## Supporting evidence
## Caveats
## Confidence
"""


ORCHESTRATOR_PROMPT = """\
You are the orchestrator for a Bangumi Anime Reception Analyst workflow.

You must work in this order:
1. retrieval specialist
2. EDA specialist
3. hypothesis specialist

Rules:
- Use the specialists as tools.
- Keep the scope narrow: seasonal comparison, popularity-score gap, and one evidence-backed hypothesis.
- Do not fabricate numbers, titles, or artifact paths.
- If a specialist fails, say so clearly.

Return markdown with these exact sections:
## Seasonal comparison
## Retrieval evidence
## EDA findings
## Hypothesis
## Caveats
"""


CRITIC_SPECIALIST_PROMPT = """\
You are the critic specialist for a Bangumi Anime Reception Analyst workflow.

Your only job is to determine whether the hypothesis is actually supported by the findings.
Do not rewrite the report. Do not add new evidence.

First line must be exactly one of:
VERDICT: PASS
VERDICT: REVISE

Then return markdown with these exact sections:
## Support check
## Unsupported leaps
## Minimal fix
"""


RETRIEVAL_TOOL_DESCRIPTION = (
    "Run the retrieval specialist on the requested Bangumi seasonal cohorts. "
    "Use this first to gather runtime evidence and representative titles."
)

EDA_TOOL_DESCRIPTION = (
    "Run the EDA specialist on already-prefetched Bangumi cohort rows. "
    "Use this second to analyze the retrieved cohorts without calling Bangumi again."
)

HYPOTHESIS_TOOL_DESCRIPTION = (
    "Run the hypothesis specialist after retrieval and EDA are complete. "
    "Use it to produce one narrow evidence-backed hypothesis."
)


def _coerce_specialist_input(data) -> SpecialistSeasonInput:
    if isinstance(data, SpecialistSeasonInput):
        return data

    if isinstance(data, dict):
        # OpenAI Agents SDK sometimes passes the input-builder payload wrapped like:
        # {"params": {...}, "json_schema": ...}
        if "params" in data and isinstance(data["params"], dict):
            data = data["params"]

    return SpecialistSeasonInput.model_validate(data)


def build_orchestrator_input(request: SeasonGapAnalysisRequest) -> str:
    return f"""\
<task>
Compare two Bangumi anime seasons and produce an evidence-backed seasonal comparison.
</task>

<scope>
- season_a: {request.season_a.label}
- season_b: {request.season_b.label}
- page_limit: {request.page_limit}
- per_page: {request.per_page}
- top_n: {request.top_n}
- min_rating_total: {request.min_rating_total}
- output_subdir: {request.output_subdir}
</scope>
"""


def build_critic_input(request: SeasonGapAnalysisRequest, orchestrator_output: str) -> str:
    return f"""\
<task>
Check whether the final hypothesis is actually supported by the findings.
</task>

<scope>
- season_a: {request.season_a.label}
- season_b: {request.season_b.label}
</scope>

<report_to_review>
{orchestrator_output}
</report_to_review>
"""


def retrieval_input_builder(data) -> str:
    data = _coerce_specialist_input(data)
    return f"""\
Retrieve runtime evidence for these two cohorts:
- {data.season_a_label}
- {data.season_b_label}
Use page_limit={data.page_limit}, per_page={data.per_page}, min_rating_total={data.min_rating_total}.
"""


def eda_input_builder(data) -> str:
    data = _coerce_specialist_input(data)
    return f"""\
Analyze the already-prefetched rows for these cohorts:
- {data.season_a_label}
- {data.season_b_label}
Do not call Bangumi again.
Use page_limit={data.page_limit}, per_page={data.per_page}, top_n={data.top_n}, min_rating_total={data.min_rating_total}, output_subdir={data.output_subdir}.
Then summarize only the descriptive findings.
"""