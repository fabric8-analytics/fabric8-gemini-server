"""Test Node Parser."""

from pathlib import Path
from parsers.node_parser import NodeParser
from werkzeug.datastructures import FileStorage


def test_node_parser():
    """Test node parser."""
    with (Path(__file__).parent / "files/npm-list.json").open('rb') as f:
        direct_dependencies, transitive_dependencies = \
            NodeParser.parse_output_files([FileStorage(f)])
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
