from src.interfaces.admin.views import (
    BatchAdmin,
    CorrectionAttemptAdmin,
    CorrectionJobAdmin,
    CorrectionResultAdmin,
    SubmissionAdmin,
    register_admin_views,
)
from src.modules.aes.models.correction import CorrectionAttempt, CorrectionJob, CorrectionResult
from src.modules.aes.models.submission import Batch, Submission


def test_batch_admin_targets_batch_model():
    assert BatchAdmin.model is Batch


def test_submission_admin_targets_submission_model():
    assert SubmissionAdmin.model is Submission


def test_correction_job_admin_targets_correction_job_model():
    assert CorrectionJobAdmin.model is CorrectionJob


def test_correction_attempt_admin_targets_correction_attempt_model():
    assert CorrectionAttemptAdmin.model is CorrectionAttempt


def test_correction_result_admin_targets_correction_result_model():
    assert CorrectionResultAdmin.model is CorrectionResult


def test_correction_views_are_read_only():
    for view in (BatchAdmin, SubmissionAdmin, CorrectionJobAdmin, CorrectionAttemptAdmin, CorrectionResultAdmin):
        assert view.can_create is False
        assert view.can_edit is False
        assert view.can_delete is False


def test_register_admin_views_includes_correction_views():
    import sqladmin

    admin = sqladmin.Admin.__new__(sqladmin.Admin)
    admin._views = []
    admin.add_view = lambda view: admin._views.append(view)

    register_admin_views(admin)

    registered_models = {v.model for v in admin._views}
    assert Batch in registered_models
    assert Submission in registered_models
    assert CorrectionJob in registered_models
    assert CorrectionAttempt in registered_models
    assert CorrectionResult in registered_models
