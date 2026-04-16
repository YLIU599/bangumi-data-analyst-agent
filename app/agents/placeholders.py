from agents import Agent
from agents.extensions.models.litellm_model import LitellmModel

from app.core.config import Settings


def _litellm_model(settings: Settings) -> LitellmModel:
    return LitellmModel(model=settings.agent_model)


def build_placeholder_agents(settings: Settings) -> dict[str, Agent]:
    """
    These are intentionally not wired into the current API path yet.
    They reserve the future multi-agent structure while the first scaffold
    stays focused on runtime data collection, EDA, and artifact output.
    """
    model = _litellm_model(settings)

    collector = Agent(
        name="bangumi_data_collector",
        instructions=(
            "Collect Bangumi data at runtime. Use retrieval tools only. "
            "Do not perform high-level interpretation beyond describing what was fetched."
        ),
        model=model,
        handoff_description="Fetches Bangumi subject data for requested cohorts.",
    )

    explorer = Agent(
        name="season_explorer",
        instructions=(
            "Perform exploratory analysis over already-collected cohort data. "
            "Surface concrete numbers, patterns, and anomalies. Do not jump to a broad thesis."
        ),
        model=model,
        handoff_description="Performs focused EDA over collected Bangumi cohort data.",
    )

    hypothesis = Agent(
        name="hypothesis_writer",
        instructions=(
            "Form a narrow evidence-based hypothesis from the exploration results. "
            "State which findings support the claim and note the main uncertainty."
        ),
        model=model,
        handoff_description="Turns exploration findings into a cautious hypothesis.",
    )

    orchestrator = Agent(
        name="analysis_orchestrator",
        instructions=(
            "Route the task through collect, then explore, then hypothesize. "
            "Keep each specialist within its role."
        ),
        model=model,
        handoffs=[collector, explorer, hypothesis],
    )

    return {
        "collector": collector,
        "explorer": explorer,
        "hypothesis": hypothesis,
        "orchestrator": orchestrator,
    }
