"""Test Node Parser."""

from pathlib import Path
from parsers.node_parser import NodeParser
from werkzeug.datastructures import FileStorage
from werkzeug.exceptions import BadRequest
import pytest


def test_node_parser_no_files():
    """Test node parser with improper input."""
    with pytest.raises(BadRequest) as e:
        # TODO: add
        # NodeParser.parse_output_files([])
        # assert e is not None
        NodeParser.parse_output_files(["foo", "bar", "baz"])
        assert e is not None


def test_node_parser():
    """Test node parser."""
    with (Path(__file__).parent / "files/npm-list.json").open('rb') as f:
        direct_dependencies, transitive_dependencies = \
            NodeParser.parse_output_files([FileStorage(f)])

        assert direct_dependencies is not None
        assert transitive_dependencies is not None

        assert direct_dependencies == {
            "npm:github-url-to-object:4.0.4",
            "npm:lodash:4.17.10",
            "npm:normalize-registry-metadata:1.1.2",
            "npm:revalidator:0.3.1",
            "npm:semver:5.5.1"
        }
        assert transitive_dependencies == {
            "npm:is-url:1.2.4",
            "npm:semver:5.5.1"
        }


def test_node_parser_transitive_dependencies():
    """Test node parser for transitive dependencies."""
    with (Path(__file__).parent / "files/npm-list-transitive-dependencies.json").open('rb') as f:
        direct_dependencies, transitive_dependencies = \
            NodeParser.parse_output_files([FileStorage(f)])

        assert direct_dependencies is not None
        assert transitive_dependencies is not None

        assert direct_dependencies == {
            "npm:body-parser:1.18.2"
        }
        assert transitive_dependencies == {
            "npm:ms:2.0.0"
        }
