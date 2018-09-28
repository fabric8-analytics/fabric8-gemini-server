"""Test Node Parser."""

from pathlib import Path
from parsers.node_parser import NodeParser
import json


def test_node_parser():
    """Test node parser."""
    with (Path(__file__).parent / "files/package.json").open(encoding='utf-8') as f:
        content = json.load(f)
        direct_dependencies, transitive_dependencies = \
            NodeParser.parse_output_file(content)
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
