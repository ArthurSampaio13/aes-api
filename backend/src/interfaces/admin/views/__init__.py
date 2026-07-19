"""SQLAdmin model views for the admin interface."""

from sqladmin import Admin

from .batch import BatchAdmin
from .correction import CorrectionAttemptAdmin, CorrectionJobAdmin, CorrectionResultAdmin
from .essay_prompt import EssayPromptAdmin
from .municipio import MunicipioAdmin
from .prompt_template import PromptTemplateAdmin
from .rubric import RubricAdmin
from .submission import SubmissionAdmin
from .tiers import TierAdmin
from .users import UserAdmin

__all__ = [
    "UserAdmin",
    "TierAdmin",
    "MunicipioAdmin",
    "RubricAdmin",
    "PromptTemplateAdmin",
    "EssayPromptAdmin",
    "BatchAdmin",
    "SubmissionAdmin",
    "CorrectionJobAdmin",
    "CorrectionAttemptAdmin",
    "CorrectionResultAdmin",
    "register_admin_views",
]


def register_admin_views(admin: Admin) -> None:
    """Register all model views with the admin interface."""
    admin.add_view(UserAdmin)
    admin.add_view(TierAdmin)
    admin.add_view(MunicipioAdmin)
    admin.add_view(RubricAdmin)
    admin.add_view(PromptTemplateAdmin)
    admin.add_view(EssayPromptAdmin)
    admin.add_view(BatchAdmin)
    admin.add_view(SubmissionAdmin)
    admin.add_view(CorrectionJobAdmin)
    admin.add_view(CorrectionAttemptAdmin)
    admin.add_view(CorrectionResultAdmin)
