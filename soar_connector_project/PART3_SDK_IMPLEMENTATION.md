# Part 3: SDK Implementation — urlscan.io Connector (Full Draft)

## 1. Implementation Summary

This directory (`urlscan_io/`) contains a complete draft SDK-style implementation of the urlscan.io connector, migrated from the legacy `BaseConnector` framework to the Splunk SOAR SDK v3.15.

### Files Created

```
urlscan_io/
├── pyproject.toml              # Project metadata, dependencies, app entry point
├── src/
│   ├── __init__.py
│   ├── app.py                  # App instance, asset config, test_connectivity, action registrations
│   ├── client.py               # UrlscanClient — typed HTTP client for urlscan.io API
│   ├── actions/
│   │   ├── __init__.py
│   │   ├── detonate_url.py     # Submit URL for scanning (most complex action)
│   │   ├── get_report.py       # Retrieve scan report with polling
│   │   ├── get_screenshot.py   # Download and vault screenshot
│   │   ├── hunt_domain.py      # Search by domain
│   │   └── hunt_ip.py          # Search by IP
│   └── models/
│       ├── __init__.py
│       ├── params.py           # Pydantic Params models for all actions
│       └── outputs.py          # Pydantic ActionOutput models for all actions
```

### All 6 Actions Implemented

| Action | File | Key SDK Features Used |
|---|---|---|
| **test_connectivity** | `app.py` | `@app.test_connectivity()`, `ActionFailure`, `logger.info()` |
| **hunt_domain** | `actions/hunt_domain.py` | `app.register_action()`, typed `Params`/`ActionOutput` |
| **hunt_ip** | `actions/hunt_ip.py` | Same pattern as hunt_domain |
| **get_report** | `actions/get_report.py` | `SOARClient[ReportSummary]` for typed summary, polling |
| **detonate_url** | `actions/detonate_url.py` | Polling, vault integration via `soar.vault`, summary |
| **get_screenshot** | `actions/get_screenshot.py` | `soar.vault.create_attachment()` |

---

## 2. Architecture Walkthrough

### 2.1 App Entry Point (`src/app.py`)

```python
from soar_sdk.app import App
from soar_sdk.asset import AssetField, BaseAsset

class Asset(BaseAsset):
    api_key: str | None = AssetField(default=None, sensitive=True, ...)
    timeout: int = AssetField(default=120, ...)

app = App(
    asset_cls=Asset,
    name="urlscan_io",
    appid="c46c00cd-7231-4dd3-8d8e-02b9fa0e14a2",
    app_type="sandbox",
    ...
)

@app.test_connectivity()
def test_connectivity(asset: Asset) -> None:
    client = UrlscanClient(api_key=asset.api_key, timeout=asset.timeout)
    client.test_connectivity()
    logger.info("Test Connectivity Passed")

# Actions registered from separate modules
app.register_action("actions.hunt_domain:hunt_domain", action_type="investigate", ...)
app.register_action("actions.detonate_url:detonate_url", action_type="generic", read_only=False, ...)
```

**Key differences from legacy:**
- No `UrlscanConnector` class — just an `app` instance
- No `initialize()` / `finalize()` — asset config handled automatically
- No `handle_action()` dispatcher — decorators and `register_action()` handle routing
- `test_connectivity()` returns `None` on success, raises `ActionFailure` on failure

### 2.2 HTTP Client (`src/client.py`)

The legacy connector embedded all HTTP logic in `_make_rest_call()` and `_process_response()` on the connector class. The SDK version extracts this into a standalone, testable client:

```python
class UrlscanClient:
    def __init__(self, api_key: str | None, timeout: int = 120): ...

    def test_connectivity(self) -> dict: ...
    def search_domain(self, domain: str) -> dict: ...
    def search_ip(self, ip: str) -> dict: ...
    def submit_scan(self, url, private, tags, custom_agent) -> dict: ...
    def get_result(self, uuid: str) -> dict: ...
    def poll_for_result(self, uuid: str) -> dict | None: ...
    def get_screenshot(self, uuid: str) -> bytes: ...
```

**Key design decisions:**
1. **`httpx` instead of `requests`** — modern, async-capable HTTP client
2. **Typed return values** — each method returns a specific type (dict, bytes, None)
3. **`ActionFailure` for errors** — the SDK catches these and maps to APP_ERROR
4. **Polling is a client method** — `poll_for_result()` encapsulates retry logic
5. **No response type routing** — `httpx` handles JSON/binary natively

### 2.3 Typed Parameters (`src/models/params.py`)

Each action has a dedicated Pydantic class:

```python
class DetonateUrlParams(Params):
    url: str = Param(primary=True, cef_types=["url"], ...)
    tags: str | None = Param(default=None, ...)
    private: bool = Param(default=True, ...)
    custom_agent: str | None = Param(default=None, ...)
    get_result: bool = Param(default=True, ...)
    addto_vault: bool = Param(default=False, ...)
```

**The SDK validates these BEFORE calling the handler**, so:
- Required fields (`url: str`) cause an automatic error if missing
- Types are enforced (`private: bool` rejects non-boolean values)
- CEF mappings feed into SOAR's data pipeline for correlation

### 2.4 Typed Outputs (`src/models/outputs.py`)

```python
class DetonateUrlOutput(ActionOutput):
    uuid: str = OutputField(example_values=["a1b2c3d4-..."])
    url: str = OutputField(cef_types=["url"], ...)
    visibility: str = OutputField(example_values=["public", "private"])
    api_url: str
    result_url: str
    scan_result: dict | None = None
```

The SDK uses the output model to:
- Generate datapaths for SOAR playbooks (e.g., `action_result.data.*.uuid`)
- Provide example values in the auto-generated manifest
- Feed CEF-typed fields into SOAR's artifact pipeline

### 2.5 Action Handlers — Deep Dive: `detonate_url`

This is the most complex action, demonstrating all SDK patterns:

```python
def detonate_url(
    params: DetonateUrlParams, asset, soar: SOARClient[DetonateUrlSummary]
) -> DetonateUrlOutput:
```

**Signature components:**
- `params: DetonateUrlParams` — validated input
- `asset` — auto-injected Asset instance with api_key and timeout
- `soar: SOARClient[DetonateUrlSummary]` — typed SOAR client for vault/summary access
- `-> DetonateUrlOutput` — typed output (framework validates return matches expected schema)

**Flow:**
1. Parse and deduplicate tags from comma-separated string
2. Submit scan via `client.submit_scan()`
3. Handle 400 (bad request) as a special non-error case
4. Extract UUID from response
5. If `get_result=True`: poll via `client.poll_for_result()`
6. If `addto_vault=True`: download screenshot, save via `soar.vault.create_attachment()`
7. Set summary and return typed output

---

## 3. How to Test Locally

```bash
cd urlscan_io/

# Set up environment
uv add splunk-soar-sdk httpx
uv sync
source .venv/bin/activate

# Test connectivity
python src/app.py action test_connectivity --api_key=YOUR_KEY

# Hunt a domain
python src/app.py action hunt_domain --domain=example.com --api_key=YOUR_KEY

# Detonate a URL
python src/app.py action detonate_url --url=https://example.com --api_key=YOUR_KEY --private=true

# Build package for deployment
soarapps package build
```

---

## 4. Legacy vs SDK — Side-by-Side Comparison

### test_connectivity

**Legacy (40 lines):**
```python
def _handle_test_connectivity(self, param):
    action_result = self.add_action_result(ActionResult(dict(param)))
    if self._api_key:
        self.save_progress("Validating API Key")
        headers = {"API-Key": self._api_key}
        ret_val, response = self._make_rest_call(
            URLSCAN_TEST_CONNECTIVITY_ENDPOINT, action_result, headers=headers)
    else:
        self.save_progress("No API key found, checking connectivity to urlscan.io")
        ret_val, response = self._make_rest_call(
            URLSCAN_TEST_CONNECTIVITY_ENDPOINT, action_result)
    if phantom.is_fail(ret_val):
        self.save_progress(URLSCAN_TEST_CONNECTIVITY_ERROR)
        return action_result.get_status()
    self.save_progress(URLSCAN_TEST_CONNECTIVITY_SUCCESS)
    return action_result.set_status(phantom.APP_SUCCESS)
```

**SDK (10 lines):**
```python
@app.test_connectivity()
def test_connectivity(asset: Asset) -> None:
    client = UrlscanClient(api_key=asset.api_key, timeout=asset.timeout)
    if asset.api_key:
        logger.info("Validating API Key")
    else:
        logger.info("No API key found, checking connectivity to urlscan.io")
    client.test_connectivity()
    logger.info("Test Connectivity Passed")
```

### hunt_domain

**Legacy (25 lines):**
```python
def _handle_hunt_domain(self, param):
    self.debug_print(f"In action handler for {self.get_action_identifier()}")
    action_result = self.add_action_result(ActionResult(dict(param)))
    headers = {"API-Key": self._api_key}
    domain = param["domain"]
    ret_val, response = self._make_rest_call(
        URLSCAN_HUNT_DOMAIN_ENDPOINT.format(domain), action_result,
        params=None, headers=headers)
    if phantom.is_fail(ret_val):
        if not action_result.get_message():
            error_msg = response.get("message") or URLSCAN_NO_DATA_ERROR
            self.debug_print(error_msg)
            return action_result.set_status(phantom.APP_ERROR, error_msg)
        return action_result.get_status()
    action_result.add_data(response)
    if response.get("results"):
        return action_result.set_status(phantom.APP_SUCCESS, URLSCAN_ACTION_SUCCESS)
    else:
        return action_result.set_status(phantom.APP_SUCCESS, URLSCAN_NO_DATA_ERROR)
```

**SDK (12 lines):**
```python
def hunt_domain(params: HuntDomainParams, asset) -> HuntOutput:
    """Search urlscan.io for scans associated with a domain."""
    client = UrlscanClient(api_key=asset.api_key, timeout=asset.timeout)
    response = client.search_domain(params.domain)
    results = response.get("results", [])
    total = response.get("total", 0)
    has_more = response.get("has_more", False)
    if results:
        logger.info("Successfully retrieved information")
    else:
        logger.info("No data found")
    return HuntOutput(results=results, total=total, has_more=has_more)
```

---

## 5. What the SDK Provides Automatically

| Feature | Legacy (manual) | SDK (automatic) |
|---|---|---|
| Parameter validation | Manual dict access + try/except | Pydantic validates before handler runs |
| JSON manifest generation | Hand-maintained `urlscan.json` (600+ lines) | Auto-generated from Python code |
| Action dispatch | `if/elif` chain in `handle_action()` | Decorator-based registration |
| Error → APP_ERROR mapping | `action_result.set_status(phantom.APP_ERROR, ...)` | `raise ActionFailure(...)` |
| State persistence | `load_state()` / `save_state()` in init/finalize | `asset.cache_state` (encrypted) |
| CLI testing | Manual JSON input + pudb | `python src/app.py action <name> --<params>` |
| Unit test framework | None | `soarapps test unit` |
| Package building | Manual tar + manifest | `soarapps package build` |
| Pre-commit hooks | None | `.pre-commit-config.yaml` |
| Dependency management | `requirements.txt` | `uv` managed `pyproject.toml` |
