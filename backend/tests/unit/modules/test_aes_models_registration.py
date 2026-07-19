import subprocess
import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[3]


def test_importing_aes_models_alone_resolves_municipio_foreign_keys():
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            "import src.modules.aes.models; "
            "from src.infrastructure.database.session import Base; "
            "assert 'municipios' in Base.metadata.tables",
        ],
        cwd=str(BACKEND_ROOT),
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
