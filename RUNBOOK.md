# Runbook: Running API Tests Safely with PostPy

Procedures for running PostPy collections and mock servers without exposing
credentials, hitting the wrong environment, or opening ports to your network.
Follow sections 1 to 3 once per machine and project, and section 4 before every
run.

---

## 1. Install

1. Create a virtual environment for PostPy rather than installing it globally:

   ```bash
   python3 -m venv .venv
   . .venv/bin/activate
   ```

2. Install from GitHub, pinned to a commit SHA (or a release tag once one
   exists) so an upstream change cannot alter what runs against your APIs:

   ```bash
   pip install "git+https://github.com/patricksmithlaravel/PostPy.git@<commit-sha>"
   ```

   Do not run `pip install postpy`. That name on PyPI belongs to an unrelated
   package from another author.

3. Check the versions:

   ```bash
   postpy --version                                     # 1.4.0 or later
   python -c "import requests; print(requests.__version__)"  # 2.32.4 or later
   ```

   requests below 2.32.4 can leak `~/.netrc` credentials to crafted URLs
   (CVE-2024-47081). pip keeps an older installed copy if it already meets the
   minimum, so check this in existing environments.

4. Run PostPy as your normal user. Never run it with `sudo` or as root.

---

## 2. Addresses and Ports

### Where to bind the mock server

| Situation | `--host` | Clients use |
| --- | --- | --- |
| Local development (the normal case) | `127.0.0.1` | `http://127.0.0.1:5001` |
| Mock server inside a container | `0.0.0.0` inside the container, published with `-p 127.0.0.1:5001:5001` | `http://127.0.0.1:5001` |
| A phone, VM or network device on your LAN must reach it | Your machine's LAN IP, e.g. `192.168.1.50`, with a firewall rule for that one client | `http://192.168.1.50:5001` |
| Do not use | `0.0.0.0` on a laptop, a public IP, or anything reachable from the internet | |

Reasons for these choices:

- **Use `127.0.0.1`, not `localhost`.** With `--host localhost` the server
  listens on IPv4 `127.0.0.1` only. Clients that resolve `localhost` to IPv6
  `::1` first fail to connect or stall before falling back.
- **`127.0.0.1` also isolates cookies.** Browsers scope cookies by host name
  and share them across ports. Script on a page from `localhost:5001` can read
  the non-HttpOnly cookies your real app set on `localhost:3000`. A mock on
  `127.0.0.1:5001` cannot.
- **`0.0.0.0` listens on every interface,** including Wi-Fi at a café or
  conference. PostPy prints a warning whenever `--host` is not `localhost`,
  `127.0.0.1` or `::1`.
- **Publish container ports on loopback.** `-p 5001:5001` listens on every
  host interface, and on Linux Docker's iptables rules bypass `ufw`. Always
  include `127.0.0.1:` in `-p`.
- **The mock server is Werkzeug's development server.** It is for one
  developer or one CI job. Do not put it behind a public reverse proxy or use
  it as a shared staging service.

### Exposing the mock server to one LAN device

Bind to the LAN IP and allow only the device that needs it. On Linux with ufw
enabled and incoming traffic denied by default:

```bash
postpy mock run mock_config.yaml --host 192.168.1.50 --port 5001
sudo ufw allow from 192.168.1.73 to any port 5001 proto tcp
```

On macOS, if the application firewall is on, it asks whether to accept
incoming connections the first time. Allow it only when you mean to expose the
server.

Remove the firewall rule and stop the server when you are done.

### Choosing a port

- Use a port from 5001 to 5099 for mock servers. Give each mock a fixed port
  and record it in that project's env file (`mock_url=http://127.0.0.1:5001`).
- Avoid 5000 and 7000 on macOS, where AirPlay Receiver (ControlCenter) listens
  on all interfaces.
- Avoid ports below 1024. On Linux they need root by default.
- Avoid ports your other tools default to: 3000 (Node and React), 5173 (Vite),
  8000 (Django, `python -m http.server`), 8080 (proxies and app servers), 3306
  (MySQL), 5432 (PostgreSQL), 6379 (Redis), 27017 (MongoDB).
- Check that the port is free before starting:

  ```bash
  lsof -nP -iTCP:5001 -sTCP:LISTEN
  ```

  No output means the port is free.

### Proxies

PostPy sends requests for loopback addresses (`127.0.0.0/8`, `::1`,
`localhost` and `*.localhost`) directly, even when `HTTP_PROXY` or
`HTTPS_PROXY` is set, as browsers do. Requests to other hosts still go through
the proxy. To inspect local traffic with an intercepting proxy such as
mitmproxy, pass `proxies=` from Python or use your machine's LAN address.

Other tools do not all behave this way. Plain Python `requests`, for example,
sends `127.0.0.1` traffic through the proxy, which then sees your tokens and
mock traffic. Exclude local addresses for them:

```bash
export NO_PROXY=127.0.0.1,localhost
```

### `~/.netrc`

If `~/.netrc` has an entry for a host, requests sends those credentials to
that host. They replace any `Authorization` header set in your collection, so
the test runs as a different user, and a collection that targets that host
sends your `.netrc` password without ever mentioning it. Turn this off for test
runs:

```bash
export NETRC=/dev/null
```

---

## 3. Credentials and Environment Files

1. **Use one env file per environment, named `.env.<name>`**, e.g.
   `.env.staging` and `.env.prod`. The repository's `.gitignore` covers `.env`
   and `.env.*`, but not names like `staging.env`. Confirm a file is ignored
   before you put a secret in it:

   ```bash
   git check-ignore -v .env.staging
   ```

   It prints the matching `.gitignore` rule. No output means the file is not
   ignored.

2. **Restrict the file to your user:**

   ```bash
   chmod 600 .env.staging
   ```

3. **Let the env file choose the target.** Write `"base_url": "{{base_url}}"`
   in the collection and set `base_url` in each env file. The same collection
   then reaches production only when you pass `.env.prod`.

4. **Use test accounts with the least access that works.** Use a separate
   token per environment and a read-only token for production checks.

5. **Keep secrets out of collection files.** Reference them as `{{token}}`.
   Collections get shared and committed. PostPy also saves each request's
   `endpoint` text to its history, so a key hard-coded into an endpoint ends
   up on disk.

6. **Send tokens in headers, not query strings.** Query strings are written to
   server, proxy and CDN access logs.

7. **Expect credentials to stop at a redirect to another host or port.** PostPy then
   forwards only standard headers such as `Accept`, `Content-Type` and
   `User-Agent`. `Authorization`, `X-API-Key` and every other header the
   collection set stay with the original host, so a `401` right after such a
   redirect usually means the new host wanted credentials PostPy kept back.
   Redirects that stay on the same host and port, or move from `http` to
   `https` on the standard ports, keep all headers.

8. **Env file values are literal.** `${OTHER}` is not expanded, so an env file
   cannot pull in variables from your shell.

9. **Put only fake data in mock configs.** Anyone who can reach the port can
   read every response, and mock configs are usually committed.

---

## 4. Pre-flight Checklist (every run)

- [ ] Review the collection: `postpy show-collection api_tests.json`. Check the
      base URL and every endpoint. An endpoint that starts with `http://` or
      `https://` ignores `base_url` and goes to that host.
- [ ] Confirm the env file is the one you mean:
      `grep base_url .env.staging`.
- [ ] `POST`, `PUT`, `PATCH` and `DELETE` requests run only against the mock
      server or staging.
- [ ] Every target that receives credentials uses `https://`.
- [ ] If someone else wrote the collection, run it first against the mock
      server or with an env file of dummy values. A collection can send your
      variables to any host it names.
- [ ] If you are sharing your screen or recording, add `--quiet` so response
      bodies are not shown.

---

## 5. Running Tests

### Against the mock server

```bash
postpy mock run mock_config.yaml --host 127.0.0.1 --port 5001
```

In a second terminal:

```bash
curl -sf http://127.0.0.1:5001/api/v1/health
postpy run-collection api_tests.json --env-file .env.mock
```

`--debug` reloads the server when you save the config file. It is safe to use
locally because PostPy keeps Werkzeug's interactive debugger switched off.

### Against staging

```bash
postpy run-collection api_tests.json --env-file .env.staging --timeout 10
```

### Against production

Use a collection containing only read-only requests, with a read-only token:

```bash
postpy run-collection prod_smoke.json --env-file .env.prod --quiet --timeout 10
```

To send a single request, add `--request-name "Health"`.

### What to expect

- PostPy sends requests one at a time, in file order, with no retries.
- `run-collection` exits with `0` when every request completes and every
  assertion passes, and `1` when a request fails, an assertion fails or the
  collection is invalid. Command-line errors, such as an `--env-file` that does
  not exist, exit with `2`.
- TLS certificates are always verified. The CLI has no option to disable
  this. In Python, do not pass `verify=False` to `PostPy` methods.
- PostPy is not a load-testing tool. Do not wrap production runs in loops.

---

## 6. Running in CI

```yaml
- name: Contract tests against the mock server
  run: |
    postpy mock run examples/mock_config.yaml --host 127.0.0.1 --port 5001 &
    for _ in $(seq 1 50); do
      curl -sf http://127.0.0.1:5001/api/v1/health > /dev/null && break
      sleep 0.2
    done
    postpy run-collection examples/mock_api_tests.json \
      --env-file examples/mock.env --quiet

- name: Smoke tests against staging
  if: github.event_name == 'push' && github.ref == 'refs/heads/main'
  env:
    STAGING_TOKEN: ${{ secrets.STAGING_TOKEN }}
    POSTPY_HOME: ${{ runner.temp }}/postpy
  run: |
    umask 077
    printf 'base_url=%s\ntoken=%s\n' "https://staging.example.com" "$STAGING_TOKEN" \
      > "$RUNNER_TEMP/.env.staging"
    postpy run-collection api_tests.json \
      --env-file "$RUNNER_TEMP/.env.staging" --quiet --timeout 10
```

- Bind the mock to `127.0.0.1`, even on a CI runner.
- Always pass `--quiet` in CI. GitHub masks known secrets in logs, but not the
  personal data or tokens that can appear in response bodies.
- Write env files at run time from the CI secret store, under `umask 077`, in
  the runner's temp directory.
- Set `POSTPY_HOME` to a temp directory so request history stays in the job.
- Give jobs that run on pull requests no real credentials. Use the
  `pull_request` trigger, not `pull_request_target`, and run credentialed
  steps only after merge, as the `if:` above does.

---

## 7. After a Run

1. Stop the mock server with `Ctrl+C`. Check for leftovers:

   ```bash
   pgrep -fl "postpy mock run"
   ```

2. Remove any firewall rule you added for LAN access.

3. Delete temporary env files you created for the run.

4. Review or clear history if needed. `postpy show-history api_tests.json`
   lists recent requests. Files are in `~/.postpy/history/` (owner-only), and
   deleting them clears the history.

---

## 8. If a Credential Leaks

A token has leaked if it was committed, printed in a CI log, shown in a
recording, or sent to the wrong host.

1. **Revoke or rotate the token first.** Deleting the file, commit or log does
   not revoke a token someone has already copied.
2. Check the API provider's access logs for use of the old token.
3. Remove the leaked copy: delete the log or recording, or remove the file
   from the repository. If it was pushed to a shared remote, treat it as public
   even after you rewrite history.
4. Fix the cause using sections 3 and 6, e.g. rename `staging.env` to
   `.env.staging` or add `--quiet` to the CI step.

---

## Quick Reference

| Task | Command |
| --- | --- |
| Check a port is free | `lsof -nP -iTCP:5001 -sTCP:LISTEN` |
| Start the mock locally | `postpy mock run mock_config.yaml --host 127.0.0.1 --port 5001` |
| Write a starter mock config | `postpy mock init mock_config.yaml` |
| Review a collection | `postpy show-collection api_tests.json` |
| Run against staging | `postpy run-collection api_tests.json -e .env.staging --timeout 10` |
| Run one request | `postpy run-collection api_tests.json -e .env.staging -r "Health"` |
| Run without printing bodies | add `--quiet` |
| Show recent history | `postpy show-history api_tests.json -n 20` |
| Confirm an env file is git-ignored | `git check-ignore -v .env.staging` |
| Keep local traffic off the proxy | `export NO_PROXY=127.0.0.1,localhost` |
| Stop `~/.netrc` credentials being sent | `export NETRC=/dev/null` |
