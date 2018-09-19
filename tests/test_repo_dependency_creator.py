"""Test RepoDependencyCreator."""

from src.repo_dependency_creator import RepoDependencyCreator
from pathlib import Path
import json


def test_generate_report():
    """Test generate report."""
    with (Path(__file__).parent / "files/report.json").open(encoding='utf-8') as f:
        content = json.load(f)
        response = RepoDependencyCreator.generate_report(content, deps_list={})
        assert response is not []
