# Part 2: Migration Design — Legacy BaseConnector → Splunk SOAR SDK

## 1. Migration Overview

### 1.1 What Changes

| Aspect | Legacy (BaseConnector) | SDK (soar_sdk.app.App) |
|---|---|---|
| **Framework** | `phantom.base_connector.BaseConnector` | `soar_sdk.app.App` |
| **Entry point** | `urlscan_connector.py` → `UrlscanConnector` class | `src/app.py` → `app` instance |
| **Action registration** | `if/elif` chain in `handle_action()` | `@app.action()` decorator or `app.register_action()` |
| **Parameters** | Untyped `param` dict | Pydantic `Params` models with type validation |
| **Outputs** | `ActionResult.add_data(dict)` | Typed `ActionOutput` Pydantic models |
| **Asset config** | JSON in `urlscan.json` → `get_config()` dict | Pydantic `BaseAsset` subclass |
| **Error handling** | `phantom.APP_ERROR` + `set_status()` | `raise ActionFailure(message)` |
| **Logging** | `self.debug_print()`, `self.save_progress()` | `soar_sdk.logging.getLogger()` → standard Python logging |
| **HTTP client** | `requests` (synchronous) | `httpx` (sync + async available) |
| **Manifest** | Hand-maintained `urlscan.json` | Auto-generated from Python code |
| **Vault** | `phantom.vault.Vault`, `phantom.rules.vault_add` | `soar.vault.create_attachment()` |
| **State** | `self.load_state()` / `self.save_state()` | `asset.cache_state` dict (encrypted at rest) |
| **Testing** | `pudb` debugger, manual JSON input | `soarapps test unit`, `soarapps test integration` |
| **Packaging** | Tar file with JSON manifest | `soarapps package build` |
| **Dependencies** | Manual `requirements.txt` | `uv` managed `pyproject.toml` |
| **Min SOAR** | `6.2.1` | `7.0.0` |

### 1.2 Migration Strategy

The SDK provides `soarapps convert` to automate the scaffolding:

```bash
soarapps convert --source-dir /path/to/urlscan/
```

**What `soarapps convert` migrates automatically:**
- App metadata (name, version, appid, vendor, publisher)
- Dependencies to `pyproject.toml`
- Configuration parameters → Asset class fields
- Action names, descriptions, input/output type hints

**What `soarapps convert` does NOT migrate:**
- Handler logic (creates empty function stubs)
- Custom views / templates
- Custom REST handlers
- Polling logic
- Vault integration code

Therefore the migration has two phases:
1. **Scaffold** — Run `soarapps convert` to generate the project structure
2. **Implement** — Port each action handler, REST logic, polling, and vault integration manually

---

## 2. Target Project Structure

```
urlscan_io/
├── src/
│   ├── __init__.py
│   ├── app.py                  # App instance, asset, test_connectivity, action registrations
│   ├── actions/
│   │   ├── __init__.py
│   │   ├── detonate_url.py     # Detonate URL action handler
│   │   ├── get_report.py       # Get Report action handler
│   │   ├── hunt_domain.py      # Hunt Domain action handler
│   │   ├── hunt_ip.py          # Hunt IP action handler
│   │   └── get_screenshot.py   # Get Screenshot action handler
│   ├── models/
│   │   ├── __init__.py
│   │   ├── params.py           # All Params classes for each action
│   │   └── outputs.py          # All ActionOutput classes for each action
│   └── client.py               # urlscan.io API client (replaces _make_rest_call)
├── logo.svg
├── logo_dark.svg
├── pyproject.toml
├── .pre-commit-config.yaml
└── tests/
    ├── __init__.py
    ├── test_detonate_url.py
    └── test_hunt_domain.py
```

### Why split into modules?

| Legacy (monolithic) | SDK (modular) | Benefit |
|---|---|---|
| All handlers in one 500-line class | Each action in its own module | Independent development & testing |
| Constants file with all strings | Typed Params/Output models | IDE autocompletion, type checking |
| `_make_rest_call` method | Dedicated `UrlscanClient` class | Reusable, mockable HTTP layer |
| `urlscan.json` manifest | Auto-generated from code | Single source of truth |

---

## 3. Component Migration Details

### 3.1 Asset Configuration

**Legacy** (`urlscan.json` + `initialize()`):
```json
{
    "configuration": {
        "api_key": {"data_type": "password", "order": 0},
        "timeout": {"data_type": "numeric", "default": 120, "order": 1}
    }
}
```
```python
def initialize(self):
    config = self.get_config()
    self._api_key = config.get("api_key", "")
    self.timeout = config.get("timeout", 120)
```

**SDK** (`src/app.py`):
```python
from soar_sdk.asset import AssetField, BaseAsset

class Asset(BaseAsset):
    api_key: str | None = AssetField(
        default=None,
        sensitive=True,
        description="API key for urlscan.io (required for scan/search actions)"
    )
    timeout: int = AssetField(
        default=120,
        description="HTTP request timeout in seconds"
    )
```

**Improvements:**
- Type-safe: `api_key` is `str | None`, `timeout` is `int`
- `sensitive=True` automatically encrypts and masks API key in logs/UI
- Descriptions embedded in code, auto-generated into manifest
- No manual JSON editing required
- Pydantic validation catches misconfigured values before action runs

### 3.2 Action Registration

**Legacy** (manual dispatch):
```python
def handle_action(self, param):
    action_id = self.get_action_identifier()
    if action_id == "test_connectivity":
        ret_val = self._handle_test_connectivity(param)
    elif action_id == "hunt_domain":
        ret_val = self._handle_hunt_domain(param)
    # ... 4 more elif branches
```

**SDK** (decorator-based):
```python
# In src/app.py — direct decorator for simple actions
@app.test_connectivity()
def test_connectivity(asset: Asset) -> None:
    ...

@app.action(action_type="investigate")
def hunt_domain(params: HuntDomainParams, asset: Asset) -> HuntDomainOutput:
    ...

# In src/app.py — register_action for actions in separate modules
app.register_action(
    "actions.detonate_url:detonate_url",
    action_type="generic",
    read_only=False,
    verbose="Submit a URL for scanning on urlscan.io and optionally poll for results.",
)
```

**Improvements:**
- No manual `if/elif` — decorators handle registration
- Action metadata (type, read_only) is declared alongside the function
- `register_action` with import strings allows splitting into modules
- Adding/removing actions doesn't touch a dispatcher method

### 3.3 Parameter Definitions

**Legacy** (untyped dict, validated at runtime):
```python
url_to_scan = param["url"]                   # KeyError if missing
private = param.get("private", False)        # Could be any type
tags = param.get("tags", "")                 # Manual comma parsing
```

**SDK** (Pydantic model, validated before handler runs):
```python
from soar_sdk.params import Params, Param

class DetonateUrlParams(Params):
    url: str = Param(
        description="URL to scan",
        primary=True,
        cef_types=["url"]
    )
    tags: str | None = Param(
        default=None,
        description="Comma-separated tags (max 10)"
    )
    private: bool = Param(
        default=True,
        description="Whether to make the scan private"
    )
    custom_agent: str | None = Param(
        default=None,
        description="Custom user-agent string for the scan"
    )
    get_result: bool = Param(
        default=True,
        description="Whether to poll for and return scan results"
    )
    addto_vault: bool = Param(
        default=False,
        description="Whether to save screenshot to vault"
    )
```

**Improvements:**
- Type enforcement at framework level (bool, str, int validated before handler runs)
- Required/optional clearly expressed via type hints (`str` vs `str | None`)
- Defaults are explicit
- CEF types, descriptions, primary flag all in one place
- IDE provides autocompletion: `params.url` instead of `param["url"]`

### 3.4 Action Output Definitions

**Legacy** (arbitrary dict):
```python
action_result.add_data(response)  # Whatever the API returns
action_result.update_summary({"added_tags_num": len(tags)})
```

**SDK** (typed models):
```python
from soar_sdk.action_results import ActionOutput, OutputField

class DetonateUrlOutput(ActionOutput):
    uuid: str = OutputField(example_values=["a1b2c3d4-..."])
    url: str = OutputField(cef_types=["url"], example_values=["https://example.com"])
    visibility: str = OutputField(example_values=["public", "private"])
    report_url: str | None = OutputField(example_values=["https://urlscan.io/result/..."])
    # Full scan result when get_result=True
    scan_result: dict | None = None

class DetonateUrlSummary(ActionOutput):
    added_tags_num: int
```

**Improvements:**
- Output schema is documented and discoverable
- CEF mappings declared on output fields
- Example values auto-populate documentation
- Type checking catches schema drift

### 3.5 Error Handling

**Legacy** (status codes + messages):
```python
if phantom.is_fail(ret_val):
    if not action_result.get_message():
        error_msg = response.get("message") or URLSCAN_NO_DATA_ERROR
        return action_result.set_status(phantom.APP_ERROR, error_msg)
    return action_result.get_status()
```

**SDK** (exceptions):
```python
from soar_sdk.exceptions import ActionFailure

# In action handler:
if not response.is_success:
    raise ActionFailure(f"urlscan.io API error: {response.status_code} - {response.text}")

# The SDK catches ActionFailure and translates it to APP_ERROR automatically
```

**Improvements:**
- Pythonic exception flow instead of status code checking
- `ActionFailure` maps directly to `APP_ERROR`
- Other exceptions are caught as unexpected errors (with stack trace)
- No need for `RetVal` tuple pattern

### 3.6 HTTP Client

**Legacy** (`requests` in `_make_rest_call`):
```python
def _make_rest_call(self, endpoint, action_result, headers=None,
                    params=None, data=None, method="get"):
    request_func = getattr(requests, method)
    url = f"{self._base_url}{endpoint}"
    r = request_func(url, json=data, headers=headers,
                     verify=config.get("verify_server_cert", False),
                     params=params, timeout=self.timeout)
    return self._process_response(r, action_result)
```

**SDK** (dedicated client class using `httpx`):
```python
import httpx
from soar_sdk.exceptions import ActionFailure
from soar_sdk.logging import getLogger

logger = getLogger()

class UrlscanClient:
    BASE_URL = "https://urlscan.io"

    def __init__(self, api_key: str | None = None, timeout: int = 120):
        self._headers = {}
        if api_key:
            self._headers["API-Key"] = api_key
        self._timeout = timeout

    def _request(self, method: str, endpoint: str, **kwargs) -> httpx.Response:
        url = f"{self.BASE_URL}{endpoint}"
        with httpx.Client(timeout=self._timeout) as client:
            response = client.request(method, url, headers=self._headers, **kwargs)
        if not response.is_success and response.status_code != 404:
            raise ActionFailure(
                f"API error {response.status_code}: {response.text}"
            )
        return response

    def get_quotas(self) -> dict:
        return self._request("GET", "/user/quotas/").json()

    def search(self, query: str) -> dict:
        return self._request("GET", f"/api/v1/search/?q={query}").json()

    def submit_scan(self, url: str, private: bool, tags: list[str],
                    custom_agent: str | None = None) -> dict:
        data = {"url": url, "public": "off" if private else "on", "tags": tags}
        if custom_agent:
            data["customagent"] = custom_agent
        return self._request("POST", "/api/v1/scan/",
                            json=data,
                            headers={"Content-Type": "application/json"}).json()

    def get_result(self, uuid: str) -> dict:
        return self._request("GET", f"/api/v1/result/{uuid}").json()

    def get_screenshot(self, uuid: str) -> bytes:
        response = self._request("GET", f"/screenshots/{uuid}.png")
        return response.content
```

**Improvements:**
- Dedicated typed methods for each API endpoint
- `httpx` supports async if needed later
- No `getattr(requests, method)` dynamic dispatch
- Mockable for unit tests (inject/mock `UrlscanClient`)
- Error handling at the client level with `ActionFailure`

### 3.7 Logging

**Legacy:**
```python
self.debug_print(f"In action handler for {self.get_action_identifier()}")
self.save_progress("Validating API Key")
self.error_print(message, dump_object=error)
```

**SDK:**
```python
from soar_sdk.logging import getLogger
logger = getLogger()

logger.debug("Entering hunt_domain action")
logger.info("Validating API Key")        # Persistent UI message
logger.progress("Polling attempt 3/10")  # Transient UI message
logger.error("Failed to parse response")
```

**Improvements:**
- Standard Python `logging` interface
- `info()` = persistent messages visible in SOAR UI
- `progress()` = transient messages (overwritten by next)
- `debug()` / `warning()` go to spawn.log
- Works with standard logging infrastructure (handlers, formatters)

### 3.8 Vault Integration

**Legacy:**
```python
# Complex manual process
temp_dir = Vault.get_vault_tmp_dir()
file_type = magic.Magic(mime=True).from_buffer(response.content)
extension = mimetypes.guess_extension(file_type)
file_path = tempfile.NamedTemporaryFile(dir=temp_dir, suffix=extension, ...).name
with open(file_path, "wb") as f:
    f.write(response.content)
success, msg, vault_id = ph_rules.vault_add(container=container_id, file_location=file_path, ...)
```

**SDK:**
```python
# Single API call
vault_id = soar.vault.create_attachment(
    container_id=soar.get_executing_container_id(),
    file_content=screenshot_bytes,
    file_name=f"{report_uuid}.png",
    metadata={"source": "urlscan.io"}
)
```

**Improvements:**
- One method call vs 10+ lines of boilerplate
- No manual temp file management
- No `python-magic` / `mimetypes` dependencies needed
- Metadata support built-in

### 3.9 State Management

**Legacy:**
```python
def initialize(self):
    self._state = self.load_state()
    # ...
def finalize(self):
    self.save_state(self._state)
```

**SDK:**
```python
# Read/write state directly on asset
asset.cache_state["last_poll"] = datetime.now().isoformat()
value = asset.cache_state.get("last_poll")
```

**Improvements:**
- No initialize/finalize boilerplate
- Encrypted at rest automatically
- Three scoped state stores: `auth_state`, `cache_state`, `ingest_state`

---

## 4. Step-by-Step Migration Plan

### Phase 1: Scaffold

```bash
# 1. Install SDK
uv tool install splunk-soar-sdk

# 2. Convert legacy app
soarapps convert --source-dir /path/to/urlscan/

# 3. Add dependencies
cd urlscan_io/
uv add httpx
uv add splunk-soar-sdk
uv sync

# 4. Initialize dev environment
git init
pre-commit install
source .venv/bin/activate
```

### Phase 2: Define Types

1. Create `src/models/params.py` with Pydantic Params for each action
2. Create `src/models/outputs.py` with ActionOutput for each action
3. Define `Asset` class with `api_key` and `timeout`

### Phase 3: Build HTTP Client

1. Create `src/client.py` with `UrlscanClient`
2. Typed methods for each urlscan.io API endpoint
3. Centralized error handling with `ActionFailure`

### Phase 4: Port Actions (in order of complexity)

1. **test_connectivity** — Simplest; validate API key via `/user/quotas/`
2. **hunt_domain** — Simple GET + response parsing
3. **hunt_ip** — Nearly identical to hunt_domain
4. **get_report** — Introduces polling logic
5. **get_screenshot** — Introduces vault integration
6. **detonate_url** — Most complex; combines scan submission, polling, vault

### Phase 5: Testing

```bash
# Unit tests
soarapps test unit

# Local CLI test
python src/app.py action test_connectivity --api_key=<key>
python src/app.py action hunt_domain --domain=example.com --api_key=<key>

# Build package
soarapps package build
```

---

## 5. Risk Assessment

| Risk | Impact | Mitigation |
|---|---|---|
| Polling behavior differences | Scan results may time out differently | Match legacy constants: 10 attempts × 15s |
| Vault API differences | Screenshots may not save correctly | Test vault integration with real SOAR instance |
| Error message format changes | Playbooks may parse error strings | Keep error message patterns similar |
| `soarapps convert` limitations | Empty stubs need manual implementation | Phase 4 covers all handler logic |
| Min SOAR version bump (6.2.1 → 7.0.0) | Older SOAR instances incompatible | Document version requirement clearly |
| `requests` → `httpx` behavior | Subtle differences in SSL/timeout handling | Test against urlscan.io API directly |
