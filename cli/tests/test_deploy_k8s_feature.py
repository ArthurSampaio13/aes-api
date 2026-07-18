from pathlib import Path

import yaml

from cli.features._builtins.deploy.feature import DeployFeature
from cli.features.installer import FeatureInstaller
from cli.lib.project import ProjectContext


def test_deploy_k8s_plan_produces_six_chart_files(tmp_path: Path) -> None:
    project = ProjectContext(repo_root=tmp_path, backend_dir=tmp_path / "backend")
    feature = DeployFeature()
    plan = feature.plan({"mode": "k8s", "project_name": "aes-api"}, project)

    target_names = {fo.target.name for fo in plan.files}
    assert target_names == {
        "Chart.yaml",
        "values.yaml",
        "deployment-api.yaml",
        "deployment-worker.yaml",
        "service-api.yaml",
        "job-migrate.yaml",
    }


def test_deploy_k8s_renders_valid_yaml_and_preserves_helm_template_syntax(tmp_path: Path) -> None:
    project = ProjectContext(repo_root=tmp_path, backend_dir=tmp_path / "backend")
    feature = DeployFeature()
    plan = feature.plan({"mode": "k8s", "project_name": "aes-api"}, project)

    installer = FeatureInstaller(dry_run=False, assume_yes=True, quiet=True)
    result = installer.apply(plan)
    assert len(result.files_written) == 6

    chart_dir = plan.files[0].target.parent
    chart_yaml = yaml.safe_load((chart_dir / "Chart.yaml").read_text())
    assert chart_yaml["name"] == "aes-api"
    values_yaml = yaml.safe_load((chart_dir / "values.yaml").read_text())
    assert values_yaml["api"]["nodePort"] == 30080

    deployment_api = (chart_dir / "templates" / "deployment-api.yaml").read_text()
    assert "{{ .Release.Name }}" in deployment_api
    assert "{{ .Values.api.replicas }}" in deployment_api

    service_api = (chart_dir / "templates" / "service-api.yaml").read_text()
    assert "{{ .Values.api.nodePort }}" in service_api
    deployment_worker = (chart_dir / "templates" / "deployment-worker.yaml").read_text()
    assert "{{ .Values.worker.image }}" in deployment_worker

    job_migrate = (chart_dir / "templates" / "job-migrate.yaml").read_text()
    assert "{{ .Release.Name }}" in job_migrate
    assert "{{ .Values.api.image }}" in job_migrate
