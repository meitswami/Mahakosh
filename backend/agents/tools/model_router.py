"""Route tasks to the best available LLM based on task type."""

from enum import StrEnum

from backend.core.config import settings


class ModelTask(StrEnum):
    REASONING = "reasoning"
    EXTRACTION = "extraction"
    CLASSIFICATION = "classification"
    SUMMARIZATION = "summarization"
    CODE = "code"
    GENERAL = "general"


MODEL_ROUTING: dict[ModelTask, list[str]] = {
    ModelTask.REASONING: ["deepseek-r1", "qwen2.5:14b", "llama3.2"],
    ModelTask.EXTRACTION: ["qwen2.5:7b", "llama3.2"],
    ModelTask.CLASSIFICATION: ["qwen2.5:7b", "llama3.2"],
    ModelTask.SUMMARIZATION: ["llama3.2", "qwen2.5:7b"],
    ModelTask.CODE: ["deepseek-coder", "qwen2.5-coder:7b"],
    ModelTask.GENERAL: ["llama3.2", "qwen2.5:7b"],
}


class ModelRouter:
    def __init__(self, default_model: str | None = None):
        self.default_model = default_model or settings.OLLAMA_DEFAULT_MODEL

    def select_model(self, task: ModelTask | str = ModelTask.GENERAL) -> str:
        if isinstance(task, str):
            try:
                task = ModelTask(task)
            except ValueError:
                task = ModelTask.GENERAL
        candidates = MODEL_ROUTING.get(task, [self.default_model])
        return candidates[0]

    def get_fallback_chain(self, task: ModelTask | str = ModelTask.GENERAL) -> list[str]:
        if isinstance(task, str):
            try:
                task = ModelTask(task)
            except ValueError:
                task = ModelTask.GENERAL
        return MODEL_ROUTING.get(task, [self.default_model])


model_router = ModelRouter()
