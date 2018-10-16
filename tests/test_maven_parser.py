"""Tests maven parser."""

from src.parsers.maven_parser import MavenParser
from pathlib import Path


def test_maven_parser_output_file():
    """Test maven parser."""
    with (Path(__file__).parent / "files/direct-dependencies.txt").open(encoding='utf-8') as f:
        content = f.read()
        resp = MavenParser.parse_output_file(content)
        assert resp == {"maven:resolved::",
                        "maven:org.apache.geronimo.modules:geronimo-tomcat6:2.2.1"}


def test_maven_parser_output_file_transitive_dependencies():
    """Test maven parser."""
    with (Path(__file__).parent / "files/transitive-dependencies.txt").open(encoding='utf-8') as f:
        content = f.read()
        resp = MavenParser.parse_output_file(content)
        assert resp is not None
        print(resp)
