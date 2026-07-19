from ...municipio.models import Municipio  # noqa: F401  registers `municipios` so every AES model's FOREIGN KEY("municipios.id") resolves when only `aes.models` is imported (e.g. the standalone Taskiq worker process) — not re-exported, Municipio isn't an AES model
from .correction import CorrectionAttempt, CorrectionJob, CorrectionResult
from .essay_prompt import EssayPrompt
from .rubric import PromptTemplate, Rubric
from .submission import Batch, Submission

__all__ = [
    "Batch",
    "CorrectionAttempt",
    "CorrectionJob",
    "CorrectionResult",
    "EssayPrompt",
    "PromptTemplate",
    "Rubric",
    "Submission",
]
