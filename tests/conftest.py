import shutil
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def database_path(tmp_path: Path) -> Path:
    target = tmp_path / "test.sqlite"
    shutil.copy(ROOT / "mtr_play_e1.sqlite", target)
    return target
