import pytest
from pydantic import ValidationError

from app.models import QueryRequest


def test_question_is_trimmed():
    assert QueryRequest(question="  hello  ").question == "hello"


@pytest.mark.parametrize("question", ["", "   "])
def test_blank_question_is_rejected(question):
    with pytest.raises(ValidationError):
        QueryRequest(question=question)


@pytest.mark.parametrize("top_k", [0, -1, 11, 10_000])
def test_invalid_top_k_is_rejected(top_k):
    with pytest.raises(ValidationError):
        QueryRequest(question="hello", top_k=top_k)
