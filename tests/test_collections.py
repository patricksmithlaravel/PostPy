import json

import pytest
from pydantic import ValidationError

from postpy.core.loader import CollectionLoader
from postpy.core.models import Collection, Request
from tests.conftest import EXAMPLES


def test_method_is_normalized_to_upper_case():
    assert Request(name="r", method="get", endpoint="/").method == "GET"


def test_unknown_method_is_rejected():
    with pytest.raises(ValidationError, match="unsupported method 'FETCH'"):
        Request(name="r", method="fetch", endpoint="/")


def test_body_and_query_params_accept_json_values():
    request = Request(
        name="r",
        method="POST",
        endpoint="/",
        query_params={"limit": 10, "tags": ["a", "b"]},
        body=[{"id": 1}],
    )
    assert request.query_params == {"limit": 10, "tags": ["a", "b"]}
    assert request.body == [{"id": 1}]


@pytest.mark.parametrize(
    "base_url",
    ["http://localhost:5001", "https://api.example.com/v1/", "{{base_url}}"],
)
def test_valid_base_urls(base_url):
    assert (
        Collection(collection_name="c", base_url=base_url, requests=[]).base_url
        == base_url
    )


@pytest.mark.parametrize(
    "base_url", ["api.example.com", "ftp://example.com", "http://"]
)
def test_invalid_base_urls(base_url):
    with pytest.raises(ValidationError, match="base_url must be an absolute http"):
        Collection(collection_name="c", base_url=base_url, requests=[])


def test_load_json_and_yaml(tmp_path):
    data = {
        "collection_name": "C",
        "base_url": "http://localhost",
        "requests": [{"name": "A", "method": "GET", "endpoint": "/a"}],
    }
    json_path = tmp_path / "c.json"
    json_path.write_text(json.dumps(data))
    yaml_path = tmp_path / "c.yml"
    yaml_path.write_text(
        "collection_name: C\nbase_url: http://localhost\n"
        "requests:\n  - {name: A, method: GET, endpoint: /a}\n"
    )

    assert CollectionLoader.load_collection(
        json_path
    ) == CollectionLoader.load_collection(yaml_path)


def test_load_missing_collection(tmp_path):
    with pytest.raises(FileNotFoundError, match="Collection file not found"):
        CollectionLoader.load_collection(tmp_path / "nope.json")


@pytest.mark.parametrize(
    "name, text, message",
    [
        ("c.json", "{not json", "is not valid JSON"),
        ("c.yaml", "a: [", "is not valid YAML"),
        ("c.json", "[]", "must contain a collection object"),
    ],
)
def test_load_unparseable_collection(tmp_path, name, text, message):
    path = tmp_path / name
    path.write_text(text)
    with pytest.raises(ValueError, match=message):
        CollectionLoader.load_collection(path)


def test_load_environment(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME_SECRET", "leak")
    path = tmp_path / ".env"
    path.write_text(
        "# comment\n"
        "\n"
        "token=abc123\n"
        "export REGION=us-east-1\n"
        'quoted="hello world"\n'
        "url=https://x.test/?a=1&b=2\n"
        "literal=${HOME_SECRET}\n"
        "NO_VALUE\n"
    )

    variables = CollectionLoader.load_environment(path).variables

    assert variables == {
        "token": "abc123",
        "REGION": "us-east-1",
        "quoted": "hello world",
        "url": "https://x.test/?a=1&b=2",
        "literal": "${HOME_SECRET}",
    }


def test_load_missing_environment(tmp_path):
    with pytest.raises(FileNotFoundError, match="Environment file not found"):
        CollectionLoader.load_environment(tmp_path / ".env")


@pytest.mark.parametrize("name", ["api_tests.json", "mock_api_tests.json"])
def test_example_collections_are_valid(name):
    collection = CollectionLoader.load_collection(EXAMPLES / name)
    assert collection.requests
