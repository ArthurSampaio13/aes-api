from pathlib import Path

import pytest

from cli.features._builtins.deploy.feature import SUPPORTED_MODES, DeployFeature
from cli.lib.project import ProjectContext


def test_supported_modes_no_longer_include_k8s() -> None:
    assert SUPPORTED_MODES == ("local", "prod", "nginx")


def test_local_plan_targets_docker_compose_and_localstack_init(tmp_path: Path) -> None:
    project = ProjectContext(repo_root=tmp_path, backend_dir=tmp_path / "backend")
    feature = DeployFeature()
    plan = feature.plan({"mode": "local"}, project)

    target_names = {fo.target.name for fo in plan.files}
    assert target_names == {"docker-compose.yml", "01-provision.sh"}


def test_unsupported_mode_raises(tmp_path: Path) -> None:
    project = ProjectContext(repo_root=tmp_path, backend_dir=tmp_path / "backend")
    feature = DeployFeature()
    with pytest.raises(ValueError, match="Unsupported deploy mode"):
        feature.plan({"mode": "k8s"}, project)
