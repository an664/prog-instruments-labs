import pytest

from src.parsers.base import Parser


def test_base_parser_not_implemented():
    class Dummy(Parser):
        def fetch(self, config):
            return super().fetch(config)

    with pytest.raises(NotImplementedError):
        Dummy().fetch(None)
