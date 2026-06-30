import json
from unittest.mock import MagicMock, patch

from app.classifier import FALLBACK_CLASSIFICATION, classify_ticket


def _mock_response(payload: dict, status_code: int = 200) -> MagicMock:
    response = MagicMock()
    response.status_code = status_code
    response.json.return_value = {
        "choices": [{"message": {"content": json.dumps(payload)}}]
    }
    response.raise_for_status = MagicMock()
    return response


def test_classify_ticket_returns_valid_classification():
    expected = {"category": "bug", "priority": "P1", "tags": ["login", "crash"]}

    with patch("httpx.post", return_value=_mock_response(expected)):
        result = classify_ticket("App crashes on login", "The app crashes every time I log in")

    assert result["category"] == "bug"
    assert result["priority"] == "P1"
    assert result["tags"] == ["login", "crash"]


def test_classify_ticket_uses_fallback_on_http_error():
    with patch("httpx.post", side_effect=Exception("Connection error")):
        result = classify_ticket("Some title", "Some description")

    assert result == FALLBACK_CLASSIFICATION


def test_classify_ticket_uses_fallback_on_invalid_category():
    bad = {"category": "invented_category", "priority": "P1", "tags": []}

    with patch("httpx.post", return_value=_mock_response(bad)):
        result = classify_ticket("Title", "Description")

    assert result == FALLBACK_CLASSIFICATION


def test_classify_ticket_truncates_tags_to_five():
    many_tags = {"category": "bug", "priority": "P2", "tags": ["a", "b", "c", "d", "e", "f", "g"]}

    with patch("httpx.post", return_value=_mock_response(many_tags)):
        result = classify_ticket("Title", "Description")

    assert len(result["tags"]) <= 5
