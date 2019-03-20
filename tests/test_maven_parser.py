"""Tests maven parser."""

from src.parsers.maven_parser import MavenParser
from pathlib import Path
from werkzeug.datastructures import FileStorage
from werkzeug.exceptions import BadRequest
import pytest


def test_maven_parser_output_files_direct_dependencies():
    """Test maven parser."""
    with (Path(__file__).parent / "files/direct-dependencies.txt").open('rb') as f:
        # the method MavenParser returns two values:
        # 1) direct dependencies
        # 2) transitive dependencies
        r, t = MavenParser.parse_output_files([FileStorage(f, filename='direct-dependencies.txt')])

        # check the existence of both sets
        assert r is not None
        assert t is not None
        assert isinstance(r, set)
        assert isinstance(t, set)

        # check the returned values
        assert r == {"maven:resolved::", "maven:org.apache.geronimo.modules:geronimo-tomcat6:2.2.1"}
        assert t == set()


def test_maven_parser_output_files_transitive_dependencies():
    """Test maven parser."""
    with (Path(__file__).parent / "files/transitive-dependencies.txt").open('rb') as f:
        filename = 'transitive-dependencies.txt'
        resp = MavenParser.parse_output_files([FileStorage(f, filename=filename)])
        assert resp is not None
        # TODO: more comprehensible tests


def test_maven_parser_output_files_bad_filename():
    """Test maven parser."""
    with (Path(__file__).parent / "files/bad-filename.txt").open('rb') as f:
        filename = 'bad-filename.txt'
        with pytest.raises(BadRequest) as e:
            MavenParser.parse_output_files([FileStorage(f, filename=filename)])
            assert e is not None


def test_maven_parser_changed_coordinates():
    """Test maven parser with input file with changed coordinates."""
    with (Path(__file__).parent / "files/dependencies-different-coordinates.txt").open('rb') as f:
        filename = 'direct-dependencies.txt'
        resp = MavenParser.parse_output_files([FileStorage(f, filename=filename)])
        assert resp is not None
