# Registers `municipios` so AES models' FOREIGN KEY("municipios.id") resolves when only
# `aes.models` is imported (e.g. the standalone Taskiq worker process). Not an AES model,
# not re-exported — import kept only for this side effect.
from ...municipio.models import Municipio  # noqa: F401
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
