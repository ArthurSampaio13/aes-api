from fastcrud import FastCRUD

from .models.correction import CorrectionAttempt, CorrectionJob, CorrectionResult
from .models.essay_prompt import EssayPrompt
from .models.rubric import PromptTemplate, Rubric
from .models.submission import Batch, Submission

crud_rubrics: FastCRUD = FastCRUD(Rubric)
crud_prompt_templates: FastCRUD = FastCRUD(PromptTemplate)
crud_essay_prompts: FastCRUD = FastCRUD(EssayPrompt)
crud_batches: FastCRUD = FastCRUD(Batch)
crud_submissions: FastCRUD = FastCRUD(Submission)
crud_correction_jobs: FastCRUD = FastCRUD(CorrectionJob)
crud_correction_attempts: FastCRUD = FastCRUD(CorrectionAttempt)
crud_correction_results: FastCRUD = FastCRUD(CorrectionResult)
