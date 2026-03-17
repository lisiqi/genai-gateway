"""Config-driven model routing policy."""

from __future__ import annotations

from dataclasses import dataclass
import json

from genai_gateway.config.settings import get_settings


@dataclass(slots=True)
class ModelRoutingDecision:
    """Resolved provider/model selection for one runtime request."""

    provider: str
    model: str
    reason: str
    fallback_provider: str | None = None
    fallback_model: str | None = None


class ModelRoutingPolicy:
    """Select provider and model based on task and config."""

    def __init__(self) -> None:
        self.settings = get_settings()

    def select(self, *, task: str, prompt_version: str) -> ModelRoutingDecision:
        """Return the routing decision for a request."""
        rules = self._load_rules()
        task_rule = rules.get(task, {})
        provider = str(task_rule.get("provider", self.settings.chat_provider)).strip().lower()
        model = str(task_rule.get("model", self._default_model_for_provider(provider))).strip()
        fallback_provider = task_rule.get("fallback_provider")
        fallback_model = task_rule.get("fallback_model")
        if fallback_provider is not None:
            fallback_provider = str(fallback_provider).strip().lower()
        if fallback_model is not None:
            fallback_model = str(fallback_model).strip()
        reason = (
            f"task override for '{task}'"
            if task_rule
            else f"default provider for prompt version '{prompt_version}'"
        )
        if fallback_provider and not fallback_model:
            fallback_model = self._default_model_for_provider(fallback_provider)
        return ModelRoutingDecision(
            provider=provider,
            model=model,
            reason=reason,
            fallback_provider=fallback_provider,
            fallback_model=fallback_model,
        )

    def _load_rules(self) -> dict[str, dict[str, str]]:
        """Parse task-based routing rules from config."""
        raw = self.settings.model_routing_rules_json.strip()
        if not raw:
            return {}
        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise ValueError("MODEL_ROUTING_RULES_JSON must be valid JSON.") from exc
        if not isinstance(parsed, dict):
            raise ValueError("MODEL_ROUTING_RULES_JSON must decode to an object.")
        normalized: dict[str, dict[str, str]] = {}
        for task, rule in parsed.items():
            if not isinstance(rule, dict):
                raise ValueError("Each routing rule must be an object with provider/model fields.")
            normalized[str(task)] = {
                key: str(value)
                for key, value in rule.items()
                if key in {"provider", "model", "fallback_provider", "fallback_model"}
            }
        return normalized

    def _default_model_for_provider(self, provider: str) -> str:
        """Return the configured default model for a provider."""
        if provider == "openai":
            return self.settings.openai_model
        if provider == "openrouter":
            return self.settings.openrouter_model
        raise ValueError(
            f"Unsupported routed provider '{provider}'. Expected one of: openai, openrouter."
        )
