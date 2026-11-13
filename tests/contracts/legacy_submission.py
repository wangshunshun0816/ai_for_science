"""Explicit adapter for legacy golden submission run references."""

from collections.abc import Mapping

from danus_ai.contracts.references import ScientificRef


def adapt_golden_run_refs(
    legacy: Mapping[str, object], definitions: Mapping[str, ScientificRef]
) -> list[ScientificRef]:
    """Resolve fixture aliases to exact run definitions using the fixture catalog."""
    aliases = legacy.get("run_refs")
    if "run_ids" in legacy or not isinstance(aliases, list) or not aliases:
        raise ValueError("Expected legacy run_refs only")
    refs = []
    for alias in aliases:
        if not isinstance(alias, str) or alias not in definitions:
            raise ValueError("Unknown golden run definition")
        ref = definitions[alias]
        if ref.object_type != "RunRequest":
            raise ValueError("Expected a run definition")
        refs.append(ref)
    return refs
