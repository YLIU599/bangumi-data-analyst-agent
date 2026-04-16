from __future__ import annotations

import re

from agents import Agent, Runner, set_tracing_disabled
from agents.extensions.models.litellm_model import LitellmModel

from app.agents.backend import AgentWorkflowBackend
from app.agents.models import AgentSeasonGapResponse, HypothesisToolInput, SpecialistSeasonInput
from app.agents.prompts import (
    CRITIC_SPECIALIST_PROMPT,
    EDA_SPECIALIST_PROMPT,
    EDA_TOOL_DESCRIPTION,
    HYPOTHESIS_SPECIALIST_PROMPT,
    HYPOTHESIS_TOOL_DESCRIPTION,
    ORCHESTRATOR_PROMPT,
    RETRIEVAL_SPECIALIST_PROMPT,
    RETRIEVAL_TOOL_DESCRIPTION,
    build_critic_input,
    build_orchestrator_input,
    eda_input_builder,
    retrieval_input_builder,
)
from app.agents.tools import fetch_runtime_bangumi_snapshots, run_existing_season_gap_analysis_tool
from app.core.config import Settings
from app.schemas import SeasonGapAnalysisRequest


def _build_model(settings: Settings) -> LitellmModel:
    set_tracing_disabled(True)
    return LitellmModel(model=settings.agent_model)


async def _default_output_extractor(result) -> str:
    final_output = getattr(result, "final_output", None)
    return "" if final_output is None else str(final_output)


def _extract_verdict(text: str) -> str:
    match = re.search(r"VERDICT:\s*(PASS|REVISE)", text, flags=re.IGNORECASE)
    if not match:
        return "UNKNOWN"
    return match.group(1).upper()


def _build_agents(settings: Settings):
    model = _build_model(settings)

    retrieval_specialist = Agent[AgentWorkflowBackend](
        name="retrieval_specialist",
        instructions=RETRIEVAL_SPECIALIST_PROMPT,
        model=model,
        tools=[fetch_runtime_bangumi_snapshots],
    )

    eda_specialist = Agent[AgentWorkflowBackend](
        name="eda_specialist",
        instructions=EDA_SPECIALIST_PROMPT,
        model=model,
        tools=[run_existing_season_gap_analysis_tool],
    )

    hypothesis_specialist = Agent[AgentWorkflowBackend](
        name="hypothesis_specialist",
        instructions=HYPOTHESIS_SPECIALIST_PROMPT,
        model=model,
    )

    critic_specialist = Agent[AgentWorkflowBackend](
        name="critic_specialist",
        instructions=CRITIC_SPECIALIST_PROMPT,
        model=model,
    )

    orchestrator = Agent[AgentWorkflowBackend](
        name="analysis_orchestrator",
        instructions=ORCHESTRATOR_PROMPT,
        model=model,
        tools=[
            retrieval_specialist.as_tool(
                tool_name="run_retrieval_specialist",
                tool_description=RETRIEVAL_TOOL_DESCRIPTION,
                custom_output_extractor=_default_output_extractor,
                failure_error_function=None,
                parameters=SpecialistSeasonInput,
                input_builder=retrieval_input_builder,
                max_turns=4,
            ),
            eda_specialist.as_tool(
                tool_name="run_eda_specialist",
                tool_description=EDA_TOOL_DESCRIPTION,
                custom_output_extractor=_default_output_extractor,
                failure_error_function=None,
                parameters=SpecialistSeasonInput,
                input_builder=eda_input_builder,
                max_turns=4,
            ),
            hypothesis_specialist.as_tool(
                tool_name="run_hypothesis_specialist",
                tool_description=HYPOTHESIS_TOOL_DESCRIPTION,
                custom_output_extractor=_default_output_extractor,
                failure_error_function=None,
                parameters=HypothesisToolInput,
                max_turns=3,
            ),
        ],
    )

    return orchestrator, critic_specialist


async def run_agent_season_gap_analysis(
    request: SeasonGapAnalysisRequest,
    settings: Settings,
) -> AgentSeasonGapResponse:
    backend = AgentWorkflowBackend(settings)
    orchestrator, critic_specialist = _build_agents(settings)

    orchestrator_output = str(
        (
            await Runner.run(
                orchestrator,
                build_orchestrator_input(request),
                context=backend,
                max_turns=10,
            )
        ).final_output
        or ""
    ).strip()

    critic_feedback = str(
        (
            await Runner.run(
                critic_specialist,
                build_critic_input(request, orchestrator_output),
                context=backend,
                max_turns=4,
            )
        ).final_output
        or ""
    ).strip()
    critic_verdict = _extract_verdict(critic_feedback)

    final_report = (
        f"{orchestrator_output}\n\n## Critic check\n- Verdict: {critic_verdict}\n\n{critic_feedback}"
    )

    return AgentSeasonGapResponse(
        request=request,
        orchestrator_output=orchestrator_output,
        critic_verdict=critic_verdict,
        critic_feedback=critic_feedback,
        final_report=final_report,
        artifacts=backend.latest_artifacts,
    )
