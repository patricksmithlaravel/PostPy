import pytest

from postpy import PostPy


def test_get_and_post(echo_server):
    client = PostPy()

    assert client.get(f"{echo_server}/users", params={"page": "2"}).json()["args"] == {
        "page": ["2"]
    }
    assert client.post(f"{echo_server}/users", json={"a": 1}).json()["json"] == {"a": 1}
    assert client.delete(f"{echo_server}/users/1").json()["method"] == "DELETE"


def test_url_variables(echo_server):
    client = PostPy(environment={"base": echo_server, "id": "5"})
    assert client.get("{{base}}/users/{{id}}").json()["path"] == "/users/5"


def test_environment_file(echo_server, tmp_path):
    env = tmp_path / ".env"
    env.write_text(f"base={echo_server}\n")
    assert PostPy(environment=env).get("{{base}}/x").status_code == 200
    assert PostPy(environment=str(env)).variables == {"base": echo_server}


@pytest.mark.parametrize("name", ["Authorization", "authorization"])
def test_authorization_header_takes_precedence_over_netrc(echo_server, netrc, name):
    echoed = PostPy().get(f"{echo_server}/me", headers={name: "Bearer mine"}).json()
    assert echoed["headers"]["authorization"] == "Bearer mine"


def test_session_authorization_header_takes_precedence_over_netrc(echo_server, netrc):
    client = PostPy()
    client.session.headers["Authorization"] = "Bearer session"

    echoed = client.get(f"{echo_server}/me").json()
    assert echoed["headers"]["authorization"] == "Bearer session"

    # A None header removes the session's, so .netrc applies again.
    echoed = client.get(f"{echo_server}/me", headers={"Authorization": None}).json()
    assert echoed["headers"]["authorization"] == netrc


def test_netrc_still_applies_without_authorization_header(echo_server, netrc):
    echoed = PostPy().get(f"{echo_server}/me").json()
    assert echoed["headers"]["authorization"] == netrc


def test_auth_argument_is_not_overridden(echo_server, netrc):
    response = PostPy().get(
        f"{echo_server}/me", headers={"Authorization": "Bearer mine"}, auth=("u", "p")
    )
    assert response.json()["headers"]["authorization"] == "Basic dTpw"  # u:p


def test_default_timeout_is_applied(monkeypatch):
    client = PostPy(timeout=3)
    seen = {}
    monkeypatch.setattr(client.session, "request", lambda *a, **kw: seen.update(kw))

    client.get("http://h")
    client.get("http://h", timeout=9)

    assert seen["timeout"] == 9
    client.head("http://h")
    assert seen["timeout"] == 3


def test_load_collection_and_execute(echo_server, write_collection):
    path = write_collection(
        "{{base}}",
        [
            {"name": "Login", "method": "GET", "endpoint": "/cookie/set"},
            {
                "name": "Get Users",
                "method": "GET",
                "endpoint": "/users",
                "tests": {
                    "status_code": 200,
                    "json_field_equals": {"cookies.session": "abc"},
                },
            },
        ],
    )
    with PostPy(environment={"base": echo_server}) as client:
        collection = client.load_collection(path)

        assert [r.name for r in collection.requests] == ["Login", "Get Users"]
        assert collection.execute("Login").status_code == 200
        with pytest.raises(KeyError, match="No request named 'Nope'"):
            collection.execute("Nope")

        results = collection.run()
        assert [r.passed for r in results] == [True, True]
        assert len(collection.history) == 3

        # The client and its collections share cookies.
        assert client.get(f"{echo_server}/x").json()["cookies"] == {"session": "abc"}
