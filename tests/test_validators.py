import pytest

from taskflow.utils.validators import validate_title


def test_validate_title_accepts_non_empty():
    validate_title("Buy groceries")


@pytest.mark.parametrize("bad", ["", "   ", None])
def test_validate_title_rejects_blank(bad):
    with pytest.raises(ValueError):
        validate_title(bad)
