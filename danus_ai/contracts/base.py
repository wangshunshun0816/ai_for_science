"""G §3.4 / A §5.1, §6.4 / R §3.5: shape validation, not authentication.

Trusted-code model_construct / model_copy(update=...) are not ingestion APIs.
Business schemas, authorization, reference resolution and hash policy remain pending.
"""

from typing import Any, ClassVar, Literal, Self

from pydantic import BaseModel, ConfigDict, model_validator

from .parsing import ensure_finite, parse_json


class StrictContract(BaseModel):
    """Strict foundation whose validation entry points cannot relax policy."""

    model_config = ConfigDict(
        strict=True,
        extra="forbid",
        allow_inf_nan=False,
        validate_default=True,
        validate_assignment=True,
        revalidate_instances="always",
        hide_input_in_errors=True,
    )

    @model_validator(mode="before")
    @classmethod
    def finite_values(cls, value: Any) -> Any:
        ensure_finite(value)
        return value

    @classmethod
    def model_validate(
        cls,
        obj: Any,
        *,
        strict: bool | None = None,
        extra: Literal["allow", "ignore", "forbid"] | None = None,
        from_attributes: bool | None = None,
        context: Any | None = None,
        by_alias: bool | None = None,
        by_name: bool | None = None,
    ) -> Self:
        if strict is False or extra not in (None, "forbid") or from_attributes:
            raise ValueError("Contract validation policy cannot be relaxed")
        return super().model_validate(
            obj,
            strict=True,
            extra="forbid",
            from_attributes=False,
            context=context,
            by_alias=by_alias,
            by_name=by_name,
        )

    @classmethod
    def model_validate_json(
        cls,
        json_data: str | bytes | bytearray,
        *,
        strict: bool | None = None,
        extra: Literal["allow", "ignore", "forbid"] | None = None,
        context: Any | None = None,
        by_alias: bool | None = None,
        by_name: bool | None = None,
    ) -> Self:
        # Never let the native JSON parser silently collapse duplicate keys.
        return cls.model_validate(
            parse_json(json_data),
            strict=strict,
            extra=extra,
            context=context,
            by_alias=by_alias,
            by_name=by_name,
        )


class DraftContract(StrictContract):
    """Service-owned root fields are not permitted in model-authored drafts."""

    authority_fields: ClassVar[frozenset[str]] = frozenset(
        {
            "tenant_id",
            "project_id",
            "principal",
            "principal_id",
            "on_behalf_of_account",
            "on_behalf_of_account_id",
            "approved",
            "approved_by",
            "approved_at",
            "locked_at",
            "created_at",
            "server_time",
            "content_hash",
            "measured",
            "supported",
            "paid",
        }
    )

    @model_validator(mode="before")
    @classmethod
    def reject_authority(cls, value: Any) -> Any:
        if isinstance(value, dict) and cls.authority_fields.intersection(value):
            raise ValueError("Service-owned fields are forbidden in a draft")
        return value


class AuthoritativeRecord(StrictContract):
    """Service record shape base; constructing one does not confer authority."""
