"""Base class for parsers."""

from abc import ABC, abstractmethod


class Parser(ABC):  # pragma: no cover
    """Base class for parsers to inherit."""

    @staticmethod
    @abstractmethod
    def parse_output_files(_content):
        """Parse output file."""
        raise NotImplementedError("Please implement this method")
