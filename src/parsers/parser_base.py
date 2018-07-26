"""Base class for parsers."""

from abc import ABC, abstractmethod


class Parser(ABC):
    """Base class for parsers to inherit."""

    @staticmethod
    @abstractmethod
    def parse_output_file(content):
        """Parse output file."""
        raise NotImplementedError("Please implement this method")
