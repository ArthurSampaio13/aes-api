import importlib

import pytest

SCRIPT_MODULES = [
    "scripts.create_tables",
    "scripts.create_first_tier",
    "scripts.create_first_superuser",
    "scripts.setup_initial_data",
]


@pytest.mark.parametrize("module_name", SCRIPT_MODULES)
def test_bootstrap_script_is_importable(module_name: str):
    assert importlib.import_module(module_name) is not None
