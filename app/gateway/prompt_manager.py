"""Prompt registry and rendering helpers."""

from pathlib import Path

from app.config.settings import get_settings


class PromptManager:
    """Loads prompt templates from the filesystem."""

    def __init__(self) -> None:
        self.settings = get_settings()

    def load_prompt(self, task: str, version: str) -> str:
        """Load a prompt file for the requested task/version pair."""
        prompt_path = Path(self.settings.prompt_root) / task / f"{version}.txt"
        if not prompt_path.exists():
            raise FileNotFoundError(f"Prompt template not found: {prompt_path}")
        return prompt_path.read_text(encoding="utf-8")

    def render_prompt(self, prompt_text: str, question: str, retrieved_chunks: list[dict]) -> str:
        """Render a final prompt from the template and retrieval context."""
        context = "\n\n".join(
            f"[{idx}] {chunk['source']}\n{chunk['content']}"
            for idx, chunk in enumerate(retrieved_chunks, start=1)
        )
        return (
            f"{prompt_text}\n\n"
            f"Retrieved context:\n{context or 'No relevant context found.'}\n\n"
            f"User question:\n{question}"
        )
