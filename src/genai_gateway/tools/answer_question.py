"""Answer a question from already retrieved context."""

from __future__ import annotations

from typing import Any

from genai_gateway.evaluation.pricing import compute_request_cost
from genai_gateway.prompts.manager import PromptManager
from genai_gateway.providers.chat import get_chat_provider
from genai_gateway.runtime.agent.state import AgentExecutionState
from genai_gateway.runtime.policies.model_routing import ModelRoutingPolicy
from genai_gateway.tools.base import AgentCapability


class AnswerQuestionCapability(AgentCapability):
    """Capability for context-grounded question answering."""

    name = "answer_question"

    def __init__(
        self,
        *,
        prompt_manager: PromptManager | None = None,
        routing_policy: ModelRoutingPolicy | None = None,
    ) -> None:
        self.prompt_manager = prompt_manager or PromptManager()
        self.routing_policy = routing_policy or ModelRoutingPolicy()

    def execute(self, *, inputs: dict[str, Any], state: AgentExecutionState) -> dict[str, Any]:
        """Answer the question using the retrieved chunks already in state."""
        question = str(inputs["question"])
        task = str(inputs.get("task") or state.task)
        quality_mode = str(inputs.get("quality_mode") or state.request.quality_mode)
        prompt_version = str(inputs.get("prompt_version") or state.request.prompt_version)
        prompt_text = self.prompt_manager.load_prompt(task=task, version=prompt_version)
        final_prompt = self.prompt_manager.render_prompt(
            prompt_text=prompt_text,
            question=question,
            retrieved_chunks=state.retrieved_chunks,
        )
        routing = self.routing_policy.select(
            task=task,
            quality_mode=quality_mode,
            prompt_version=prompt_version,
        )
        selected_provider = routing.provider
        selected_model = routing.model
        fallback_used = False
        chat_provider = get_chat_provider(provider_name=selected_provider, model_name=selected_model)
        try:
            answer, usage, provider_metadata = chat_provider.generate(
                prompt=final_prompt,
                question=question,
            )
        except Exception:
            if not routing.fallback_provider:
                raise
            fallback_used = True
            selected_provider = routing.fallback_provider
            selected_model = routing.fallback_model or routing.model
            fallback_provider = get_chat_provider(
                provider_name=selected_provider,
                model_name=selected_model,
            )
            answer, usage, provider_metadata = fallback_provider.generate(
                prompt=final_prompt,
                question=question,
            )

        cost = compute_request_cost(
            provider=selected_provider,
            model=selected_model,
            prompt_tokens=usage.prompt_tokens,
            completion_tokens=usage.completion_tokens,
        )
        state.answer = answer
        state.answer_metadata = {
            "provider": selected_provider,
            "model": selected_model,
            "fallback_used": fallback_used,
            "prompt_tokens": usage.prompt_tokens,
            "completion_tokens": usage.completion_tokens,
            "total_tokens": usage.total_tokens,
            "estimated_cost_usd": cost.total_cost_usd,
            "provider_reported_cost_usd": provider_metadata.provider_reported_cost_usd,
            "provider_generation_id": provider_metadata.provider_generation_id,
        }
        return {
            "answer": answer,
            "provider": selected_provider,
            "model": selected_model,
            "fallback_used": fallback_used,
            "token_usage": usage.model_dump(),
            "estimated_cost_usd": cost.total_cost_usd,
            "pricing_source": cost.pricing_source,
            "provider_reported_cost_usd": provider_metadata.provider_reported_cost_usd,
            "provider_generation_id": provider_metadata.provider_generation_id,
            "provider_usage_source": provider_metadata.provider_usage_source,
        }
