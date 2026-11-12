"""Deterministic schema bundles from the I-SCHEMA registry (A §6.4)."""

import json
from typing import Any, Literal

from pydantic.json_schema import models_json_schema

from .api import schema_capabilities, schema_registry

Format = Literal["json-schema", "openapi"]


def schema_bytes(format: Format) -> bytes:
    registry = schema_registry()
    if format == "json-schema":
        prefix = "#/$defs/{model}"
    elif format == "openapi":
        prefix = "#/components/schemas/{model}"
    else:
        raise ValueError("Unknown schema format")
    refs, bundle = models_json_schema(
        [registry[name] for name in sorted(registry)], ref_template=prefix
    )
    roots = {name: refs[entry] for name, entry in sorted(registry.items())}
    definitions = bundle["$defs"]
    document: dict[str, Any]
    if format == "json-schema":
        document = {
            "$schema": "https://json-schema.org/draft/2020-12/schema",
            "$defs": definitions,
            "x-r02-contracts": roots,
        }
    else:
        document = {
            "openapi": "3.1.0",
            "info": {"title": "Danus-AI R02 contract components", "version": "1.2"},
            "paths": {},
            "components": {"schemas": definitions},
            "x-r02-contracts": roots,
        }
    document["x-r02-capabilities"] = schema_capabilities()
    return (json.dumps(document, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode(
        "utf-8"
    )
