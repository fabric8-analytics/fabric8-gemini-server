"""Tests maven parser."""

from src.parsers.maven_parser import MavenParser
from pathlib import Path
from werkzeug.datastructures import FileStorage


def test_maven_parser_output_file():
    """Test maven parser."""
    with (Path(__file__).parent / "files/direct-dependencies.txt").open('rb') as f:
        resp = MavenParser.parse_output_files([FileStorage(f, filename='direct-dependencies.txt')])
        assert resp == ({"maven:resolved::",
                        "maven:org.apache.geronimo.modules:geronimo-tomcat6:2.2.1"}, set())
