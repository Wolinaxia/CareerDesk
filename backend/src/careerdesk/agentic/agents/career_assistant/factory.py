"""Sole runtime assembly entry point for the career assistant."""

from pathlib import Path
from collections.abc import Callable
from sqlite3 import Connection
from uuid import UUID

from agentmaker import Agent

from ...memory import build_conversation_memory
from ....platform.ai.tracing import shared_tracer
from ....platform.locale import DEFAULT_OUTPUT_LOCALE, OutputLocale
from ....features.preferences import public as preferences
from ...runtime import TrustedSkillCatalog
from .policy import CHAT_RUN_POLICY, build_history_compactor
from .prompt import build_instructions
from .toolset import build_tool_registry

_BEHAVIOR_PREFERENCE_KEYS = (
    "conversation_style",
    "response_greeting",
    "response_tone",
    "response_format",
)
_MAX_BEHAVIOR_PREFERENCE_CHARS = 1_000
_MAX_CAREER_PREFERENCE_CHARS = 7_000


def _assistant_preferences(items: list[dict]) -> list[dict]:
    """Select bounded preference data, keeping career tracks ahead of legacy keys."""
    candidates = [
        item for item in items
        if isinstance(item, dict)
        and isinstance(item.get("key"), str)
        and isinstance(item.get("value"), str)
    ]

    def priority(item: dict) -> tuple[int, str]:
        key = item["key"]
        if key == "career_strategy" or key.startswith("career_track."):
            return (0, key)
        if key.startswith("career_global."):
            return (1, key)
        return (2, key)

    selected: list[dict] = []
    behavior_used = 0
    for item in candidates:
        if item["key"] not in _BEHAVIOR_PREFERENCE_KEYS:
            continue
        size = len(item["key"]) + len(item["value"])
        if behavior_used + size > _MAX_BEHAVIOR_PREFERENCE_CHARS:
            continue
        selected.append(item)
        behavior_used += size

    career_used = 0
    career_items = [
        item for item in candidates if item["key"] not in _BEHAVIOR_PREFERENCE_KEYS
    ]
    for item in sorted(career_items, key=priority):
        size = len(item["key"]) + len(item["value"])
        if career_used + size > _MAX_CAREER_PREFERENCE_CHARS:
            continue
        selected.append(item)
        career_used += size
    return selected


def build_career_assistant(db_path: str, llm, user_id: str, *,
                           client_turn_id: str | UUID,
                           trusted_review_source: str,
                           review_supplement_reference: str | UUID | None = None,
                           hooks=None,
                           proposal_recorder: Callable[[Connection, str, str], object] | None = None,
                           conversation_embedding_enabled: bool = False,
                           output_locale: OutputLocale = DEFAULT_OUTPUT_LOCALE,
                           trace_path: str | None = None,
                           resource_closers: list | None = None) -> Agent:
    """Build the assistant for the current user and request hooks.

    This remains the single construction path for parallel readers and RunResult behavior;
    no second agent/RAG orchestrator is maintained.
    """
    catalog = TrustedSkillCatalog()
    session_store, conversation = build_conversation_memory(
        db_path,
        embedding_enabled=conversation_embedding_enabled,
        user_id=user_id,
        resource_closers=resource_closers,
    )
    tool_registry = build_tool_registry(
        db_path,
        llm,
        user_id,
        catalog,
        client_turn_id=client_turn_id,
        review_supplement_reference=review_supplement_reference,
        trusted_review_source=trusted_review_source,
        proposal_recorder=proposal_recorder,
        conversation=conversation,
        output_locale=output_locale,
    )
    try:
        preference_items = _assistant_preferences(
            preferences.list_current_preferences(db_path, user_id)["items"],
        )
    except (preferences.PreferenceProjectionConflict, ValueError):
        preference_items = []

    return Agent(
        "careerdesk_assistant",
        llm,
        system_prompt=build_instructions(
            catalog,
            conversation_search=True,
            preference_items=preference_items,
            output_locale=output_locale,
        ),
        tool_registry=tool_registry,
        session_store=session_store,
        hooks=list(hooks or []),
        run_policy=CHAT_RUN_POLICY,
        tracer=shared_tracer(trace_path or str(Path(db_path).parent / "traces.jsonl")),
        compactor=build_history_compactor(llm, output_locale),
        max_turns=10,
    )
