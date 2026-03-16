# SOAR Connector Analysis & SDK Migration — urlscan.io

**Author:** Chandra  
**Date:** March 16, 2026  
**Subject:** Legacy SOAR Connector Analysis, SDK Migration Design, and Partial Implementation

---

## Table of Contents

1. [Part 1 — Legacy Connector Analysis](#part-1--legacy-connector-analysis)
   - 1.1 Overall Architecture
   - 1.2 App Lifecycle
   - 1.3 Action Definition & Dispatching
   - 1.4 Parameter Access & Validation
   - 1.5 REST Call Implementation
   - 1.6 Result Data Structure
   - 1.7 Error Handling & Logging
2. [Part 2 — Migration Design (Legacy → SDK)](#part-2--migration-design-legacy--sdk)
   - 2.1 Migration Summary Table
   - 2.2 Target Project Structure
   - 2.3 How Actions Would Be Implemented in SDK
   - 2.4 Key Structural Changes
   - 2.5 Improvements SDK Provides Over Legacy
3. [Part 3 — Partial Implementation (hunt_domain)](#part-3--partial-implementation-hunt_domain)
   - 3.1 Action Definition
   - 3.2 Handler Implementation
   - 3.3 REST Call Logic
   - 3.4 Error Handling
   - 3.5 Result Formatting
   - 3.6 Side-by-Side Comparison

---

# Part 1 — Legacy Connector Analysis

## 1.1 Overall Architecture

The **urlscan.io** connector (v2.6.3) is a legacy Splunk SOAR app built on the `BaseConnector` framework. It integrates with the urlscan.io REST API to provide URL scanning, threat intelligence lookups, and screenshot capture within SOAR playbooks.

### Source Files

| File | Purpose |
|------|---------|
| `urlscan_connector.py` | Main connector class — all action handlers and REST logic (~500 lines) |
| `urlscan_consts.py` | Constants — URLs, endpoints, error messages, action identifiers |
| `urlscan.json` | App manifest — metadata, actions, parameters, output schemas (600+ lines) |

### Class Hierarchy

```
phantom.base_connector.BaseConnector
    └── UrlscanConnector
```

`UrlscanConnector` inherits from `BaseConnector`, which provides:
- The SOAR runtime lifecycle (`_handle_action` entry point)
- Configuration access (`get_config()`)
- State persistence (`load_state()` / `save_state()`)
- Action result management (`add_action_result()`)
- Progress reporting (`save_progress()`, `send_progress()`)
- Debug/error logging (`debug_print()`, `error_print()`)

### Role of the Main Connector Class

The `UrlscanConnector` class is the **single entry point** for the entire app. It serves multiple roles:

1. **Lifecycle manager** — Implements `initialize()`, `handle_action()`, `finalize()`
2. **Action dispatcher** — Routes action identifiers to handler methods via `if/elif`
3. **HTTP client** — Contains `_make_rest_call()` and response processing methods
4. **Result formatter** — Manages `ActionResult` objects, summaries, and vault operations
5. **Error handler** — Centralizes error extraction, formatting, and status propagation

This monolithic design means all logic (6 actions, HTTP calls, polling, file handling) lives in a single file.

---

## 1.2 App Lifecycle

The SOAR platform calls the connector in this sequence:

```
┌─────────────────────────────────────────────────┐
│  SOAR Platform calls _handle_action(json_input) │
└─────────────────────┬───────────────────────────┘
                      │
                      ▼
              ┌───────────────┐
              │  initialize() │  ← Load state, read config, set API key
              └───────┬───────┘
                      │
          ┌───────────┴───────────┐
          │  For each param set:  │  ← Platform may batch multiple param sets
          │                       │
          │   ┌─────────────────┐ │
          │   │ handle_action() │ │  ← Dispatch to correct handler
          │   └─────────────────┘ │
          └───────────┬───────────┘
                      │
              ┌───────────────┐
              │   finalize()  │  ← Save state
              └───────────────┘
```

**`initialize()`** — Called once before any action runs:
1. Loads persisted state from previous runs via `load_state()`
2. Reads asset configuration (API key, timeout) via `get_config()`
3. Registers a custom IPv6 validator
4. Defaults API key to empty string (some actions work without it)

**`handle_action(param)`** — Called for each parameter set within the action run. This is the dispatch method that routes to the correct handler.

**`finalize()`** — Called after all param sets are processed. Persists `self._state` via `save_state()` so state survives across action runs and app upgrades.

---

## 1.3 Action Definition & Dispatching

### How Actions Are Defined

Actions are defined in the `urlscan.json` manifest file. Each action specifies:
- **Identifier** — e.g., `"hunt_domain"`
- **Type** — `test`, `investigate`, or `generic`
- **Input parameters** — names, types, required/optional, defaults
- **Output datapaths** — e.g., `action_result.data.*.results`
- **Description and verbose text**

### How Actions Are Dispatched

The `handle_action()` method uses a manual `if/elif` chain to map string identifiers to handler methods:

```python
def handle_action(self, param):
    action_id = self.get_action_identifier()

    if action_id == "test_connectivity":
        ret_val = self._handle_test_connectivity(param)
    elif action_id == "get_report":
        ret_val = self._handle_get_report(param)
    elif action_id == "hunt_domain":
        ret_val = self._handle_hunt_domain(param)
    elif action_id == "hunt_ip":
        ret_val = self._handle_hunt_ip(param)
    elif action_id == "detonate_url":
        ret_val = self._handle_detonate_url(param)
    elif action_id == "get_screenshot":
        ret_val = self._handle_get_screenshot(param)
    return ret_val
```

**Registered Actions:**

| Action Identifier | Type | Handler Method | API Endpoint |
|---|---|---|---|
| `test_connectivity` | test | `_handle_test_connectivity` | `GET /user/quotas/` |
| `get_report` | investigate | `_handle_get_report` | `GET /api/v1/result/{uuid}` |
| `hunt_domain` | investigate | `_handle_hunt_domain` | `GET /api/v1/search/?q=domain:{domain}` |
| `hunt_ip` | investigate | `_handle_hunt_ip` | `GET /api/v1/search/?q=ip:"{ip}"` |
| `detonate_url` | generic | `_handle_detonate_url` | `POST /api/v1/scan/` |
| `get_screenshot` | investigate | `_handle_get_screenshot` | `GET /screenshots/{uuid}.png` |

---

## 1.4 Parameter Access & Validation

Parameters come from **two sources**:

### Asset Configuration (from `get_config()`)

Read once in `initialize()`, stored as instance variables:

```python
self._api_key = config.get("api_key", "")     # Optional API key (password field)
self.timeout = config.get("timeout", 120)       # Request timeout (default 120s)
```

### Action Parameters (from `param` dict)

Each handler receives an untyped `param` dictionary. Parameters are accessed directly:

```python
# Required parameter — direct access (KeyError if missing)
url_to_scan = param["url"]

# Optional parameters — .get() with defaults
private = param.get("private", False)
custom_agent = param.get("custom_agent")
get_result = param.get("get_result", True)
tags = param.get("tags", "")
```

### Validation Approach

Validation is manual and happens inside each handler:

- **Integer validation:** `_validate_integer()` checks type, zero, and negative values
- **IP validation:** `_is_ip()` using Python's `ipaddress.ip_address()` for IPv4/IPv6
- **Tags validation:** Max 10 tags enforced with explicit count check
- **API key presence:** Checked at the action level (e.g., `detonate_url` requires it)

There is **no framework-level validation** — if a required parameter is missing, a raw `KeyError` is raised. Type mismatches are not caught until runtime.

---

## 1.5 REST Call Implementation

### Centralized REST Client (`_make_rest_call`)

All HTTP calls go through a single method:

```python
def _make_rest_call(self, endpoint, action_result, headers=None,
                    params=None, data=None, method="get"):
    request_func = getattr(requests, method)    # Dynamic method dispatch
    url = f"{self._base_url}{endpoint}"         # URL = base + endpoint

    r = request_func(
        url, json=data, headers=headers,
        verify=config.get("verify_server_cert", False),
        params=params, timeout=self.timeout
    )
    return self._process_response(r, action_result)
```

**Key design choices:**
- Uses the `requests` library directly (synchronous only)
- Dynamic method selection via `getattr(requests, method)`
- SSL verification is configurable from asset config
- Always sends JSON payloads via `json=data`
- Returns a `RetVal` tuple: `(status, data)`

### Response Processing Pipeline

Responses are routed by `Content-Type` header through separate processors:

```
_process_response(r, action_result)
    │
    ├── "json" in Content-Type  ──→ Parse JSON, check status (200-399 = success)
    │                                Special case: 404 with status field → APP_SUCCESS
    │
    ├── "html" in Content-Type  ──→ Parse with BeautifulSoup, strip scripts/style
    │                                Return sanitized error text
    │
    ├── "image" or "octet-stream" → Return raw response object (for screenshots)
    │
    ├── empty body              ──→ 200 = success with {}, else error
    │
    └── anything else           ──→ Error with status code and body text
```

### RetVal Pattern

Every REST call returns a 2-tuple:

```python
class RetVal(tuple):
    def __new__(cls, val1, val2):
        return tuple.__new__(RetVal, (val1, val2))
```

- First element: `phantom.APP_SUCCESS` or `phantom.APP_ERROR`
- Second element: parsed response (dict, response object, or None)

Handlers consume this pattern consistently:
```python
ret_val, response = self._make_rest_call(endpoint, action_result, ...)
if phantom.is_fail(ret_val):
    return action_result.get_status()
```

---

## 1.6 Result Data Structure

### ActionResult Objects

Each handler creates an `ActionResult` and adds it to the connector:

```python
action_result = self.add_action_result(ActionResult(dict(param)))
```

Results are populated in three parts:

1. **Data** — Full API response added via `action_result.add_data(response)`
2. **Summary** — Key values for UI display via `action_result.update_summary({"key": value})`
3. **Status** — Final success/failure via `action_result.set_status(phantom.APP_SUCCESS, msg)`

### Null Value Replacement

A utility method handles null bytes in API responses:

```python
def replace_null_values(self, data):
    return json.loads(json.dumps(data).replace("\\u0000", "\\\\u0000"))
```

This prevents downstream JSON parsing failures in the SOAR platform.

### Vault Integration (Screenshots)

Binary file storage follows a multi-step process:
1. Detect MIME type with `python-magic`
2. Write to temp file in vault tmp directory
3. Add to vault via `ph_rules.vault_add()`
4. Retrieve metadata via `ph_rules.vault_info()`
5. Store vault ID, file name, type, size in action summary

---

## 1.7 Error Handling & Logging

### How API Errors Are Handled

Errors are handled at three layers:

```
Layer 1: Network/Connection errors
    → _make_rest_call catches requests.Exception
    → Sets APP_ERROR with formatted connectivity error message

Layer 2: HTTP/Response errors
    → _process_*_response methods check status codes
    → JSON: 200-399 = success, 404 with status field = success (scan pending)
    → HTML: Parsed and sanitized for error text
    → Sets APP_ERROR with detailed error message

Layer 3: Business logic errors
    → Each handler checks response data for expected fields
    → Sets APP_ERROR with specific business error messages
```

### Error Message Extraction

```python
def _get_error_message_from_exception(self, e):
    error_code = "Error code unavailable"
    error_message = "Error message unavailable..."
    if e.args:
        if len(e.args) > 1:
            error_code = e.args[0]
            error_message = e.args[1]
        elif len(e.args) == 1:
            error_message = e.args[0]
    return f"Error Code: {error_code}. Error Message: {error_message}"
```

### How Exceptions Are Surfaced to the Platform

All errors flow through `action_result`:

```python
action_result.set_status(phantom.APP_ERROR, "Error message here")
return action_result.get_status()
```

The platform reads the `ActionResult` status and message to display errors in the SOAR UI. Error messages are centralized in `urlscan_consts.py` as string constants.

### XSS Prevention

HTML error responses escape curly braces to prevent format string injection:
```python
message = message.replace("{", "{{").replace("}", "}}")
```

### Logging Methods

| Method | Purpose | Visibility |
|--------|---------|------------|
| `self.debug_print(msg)` | Debug-level logs | spawn.log only |
| `self.error_print(msg)` | Error-level logs | spawn.log only |
| `self.save_progress(msg)` | Persistent progress | Visible in SOAR UI |
| `self.send_progress(msg)` | Transient progress | Overwritten by next call |

---

# Part 2 — Migration Design (Legacy → SDK)

## 2.1 Migration Summary Table

| Aspect | Legacy (BaseConnector) | SDK (soar_sdk.app.App) |
|--------|----------------------|----------------------|
| **Framework** | `phantom.base_connector.BaseConnector` | `soar_sdk.app.App` |
| **Entry point** | `urlscan_connector.py` → `UrlscanConnector` class | `src/app.py` → `app` instance |
| **Action registration** | `if/elif` chain in `handle_action()` | `@app.action()` decorator or `app.register_action()` |
| **Parameters** | Untyped `param` dict | Pydantic `Params` models with type validation |
| **Outputs** | `ActionResult.add_data(dict)` | Typed `ActionOutput` Pydantic models |
| **Asset config** | JSON in `urlscan.json` → `get_config()` dict | Pydantic `BaseAsset` subclass with `AssetField` |
| **Error handling** | `phantom.APP_ERROR` + `set_status()` | `raise ActionFailure(message)` |
| **Logging** | `self.debug_print()`, `self.save_progress()` | Standard Python logging via `soar_sdk.logging.getLogger()` |
| **HTTP client** | `requests` (synchronous) | `httpx` (sync + async available) |
| **Manifest** | Hand-maintained `urlscan.json` (600+ lines) | Auto-generated from Python code |
| **Vault** | `phantom.vault.Vault`, `phantom.rules.vault_add` | `soar.vault.create_attachment()` |
| **State** | `self.load_state()` / `self.save_state()` | `asset.cache_state` dict (encrypted at rest) |
| **Testing** | `pudb` debugger, manual JSON input | `soarapps test unit`, `soarapps test integration` |
| **Packaging** | Manual tar file with JSON manifest | `soarapps package build` |
| **Dependencies** | Manual `requirements.txt` | `uv` managed `pyproject.toml` |

## 2.2 Target Project Structure

```
urlscan_io/
├── pyproject.toml              # Project metadata, dependencies, app entry point
├── src/
│   ├── __init__.py
│   ├── app.py                  # App instance, asset config, test_connectivity, action registrations
│   ├── client.py               # UrlscanClient — typed HTTP client (replaces _make_rest_call)
│   ├── actions/
│   │   ├── __init__.py
│   │   ├── detonate_url.py     # Detonate URL action handler
│   │   ├── get_report.py       # Get Report action handler
│   │   ├── get_screenshot.py   # Get Screenshot action handler
│   │   ├── hunt_domain.py      # Hunt Domain action handler
│   │   └── hunt_ip.py          # Hunt IP action handler
│   └── models/
│       ├── __init__.py
│       ├── params.py           # Pydantic Params classes for all actions
│       └── outputs.py          # Pydantic ActionOutput classes for all actions
└── tests/
    ├── __init__.py
    ├── test_detonate_url.py
    └── test_hunt_domain.py
```

### Why Split Into Modules?

| Legacy (monolithic) | SDK (modular) | Benefit |
|---------------------|---------------|---------|
| All handlers in one 500-line class | Each action in its own module | Independent development & testing |
| Constants file with all strings | Typed Params/Output models | IDE autocompletion, type checking |
| `_make_rest_call` method on connector | Dedicated `UrlscanClient` class | Reusable, testable, mockable HTTP layer |
| Hand-maintained `urlscan.json` | Auto-generated from Python code | Single source of truth |

---

## 2.3 How Actions Would Be Implemented in SDK

### Asset Configuration

**Legacy** — Asset config is defined in JSON and read at runtime:
```python
# urlscan.json defines api_key and timeout
# initialize() reads them manually:
config = self.get_config()
self._api_key = config.get("api_key", "")
self.timeout = config.get("timeout", 120)
```

**SDK** — Asset config is a Pydantic model with type safety and built-in encryption:
```python
class Asset(BaseAsset):
    api_key: str | None = AssetField(
        default=None,
        sensitive=True,  # Automatically encrypted and masked in logs/UI
        description="API key for urlscan.io"
    )
    timeout: int = AssetField(
        default=120,
        description="HTTP request timeout in seconds"
    )
```

### Action Registration

**Legacy** — Manual `if/elif` dispatch:
```python
def handle_action(self, param):
    action_id = self.get_action_identifier()
    if action_id == "hunt_domain":
        return self._handle_hunt_domain(param)
    elif action_id == "hunt_ip":
        return self._handle_hunt_ip(param)
    # ... more elif branches
```

**SDK** — Decorator-based or `register_action()` from separate modules:
```python
# Simple actions — decorator directly in app.py
@app.test_connectivity()
def test_connectivity(asset: Asset) -> None:
    ...

# Complex actions — defined in separate modules, registered in app.py
app.register_action(
    "actions.hunt_domain:hunt_domain",
    action_type="investigate",
    identifier="hunt_domain",
    read_only=True,
)
```

### Typed Parameters

**Legacy** — Untyped dict, validated manually at runtime:
```python
url_to_scan = param["url"]           # KeyError if missing
private = param.get("private", False) # Could be any type
```

**SDK** — Pydantic model, validated before handler runs:
```python
class DetonateUrlParams(Params):
    url: str = Param(primary=True, cef_types=["url"])
    private: bool = Param(default=True)
    tags: str | None = Param(default=None)
```

The SDK validates parameters **before** calling the handler — required fields that are missing automatically produce an error, and type mismatches are caught at the framework level.

### Typed Outputs

**Legacy** — Arbitrary dict:
```python
action_result.add_data(response)  # Whatever the API returns
action_result.update_summary({"added_tags_num": len(tags)})
```

**SDK** — Pydantic output model:
```python
class HuntOutput(ActionOutput):
    results: list[dict] = OutputField(example_values=[])
    total: int = OutputField(example_values=[0, 10, 100])
    has_more: bool = OutputField(example_values=[True, False])
```

The output model auto-generates datapaths for playbooks, provides example values in documentation, and feeds CEF-typed fields into SOAR's artifact pipeline.

### Error Handling

**Legacy** — Status codes + set_status:
```python
if phantom.is_fail(ret_val):
    return action_result.set_status(phantom.APP_ERROR, error_msg)
```

**SDK** — Pythonic exceptions:
```python
if not response.is_success:
    raise ActionFailure(f"API error: {response.status_code} - {response.text}")
# SDK catches ActionFailure and translates to APP_ERROR automatically
```

### HTTP Client

**Legacy** — `requests` embedded in connector class:
```python
def _make_rest_call(self, endpoint, action_result, ...):
    request_func = getattr(requests, method)
    r = request_func(url, json=data, ...)
    return self._process_response(r, action_result)
```

**SDK** — Dedicated `UrlscanClient` class using `httpx`:
```python
class UrlscanClient:
    def search_domain(self, domain: str) -> dict:
        response = self._request("GET", f"/api/v1/search/?q=domain:{domain}")
        if not response.is_success:
            raise ActionFailure(f"Domain search failed: {response.status_code}")
        return response.json()
```

### Vault Integration

**Legacy** — Multi-step manual process (detect MIME, write temp file, vault_add, vault_info):
```python
file_type = magic.Magic(mime=True).from_buffer(response.content)
file_path = tempfile.NamedTemporaryFile(dir=temp_dir, suffix=extension, ...).name
with open(file_path, "wb") as f:
    f.write(response.content)
success, msg, vault_id = ph_rules.vault_add(container=container_id, file_location=file_path, ...)
```

**SDK** — Single API call:
```python
vault_id = soar.vault.create_attachment(
    container_id=soar.get_executing_container_id(),
    file_content=screenshot_bytes,
    file_name=f"{report_uuid}.png",
)
```

### Logging

**Legacy** — Custom framework methods:
```python
self.debug_print("message")
self.save_progress("message")
self.error_print("message")
```

**SDK** — Standard Python logging interface:
```python
from soar_sdk.logging import getLogger
logger = getLogger()
logger.debug("message")       # spawn.log only
logger.info("message")        # Persistent UI message
logger.progress("message")    # Transient UI message
```

---

## 2.4 Key Structural Changes

| Change | Detail |
|--------|--------|
| **No monolithic class** | The SDK replaces the single `UrlscanConnector` class with: an `app` instance, separate action modules, a typed client, and Pydantic models |
| **No `initialize()`/`finalize()`** | Asset configuration is handled automatically by the `BaseAsset` Pydantic model. State persistence uses `asset.cache_state` |
| **No `handle_action()` dispatcher** | Actions are registered via decorators or `register_action()` — the SDK handles routing |
| **No `urlscan.json` manifest** | The app manifest is auto-generated from Python code (parameters, outputs, metadata) |
| **No `RetVal` pattern** | Errors are raised as `ActionFailure` exceptions — no manual status code checking |
| **No `ActionResult` management** | Return typed `ActionOutput` objects — the SDK wraps them in `ActionResult` automatically |

---

## 2.5 Improvements SDK Provides Over Legacy

### Developer Experience
- **Type safety** — Pydantic models catch parameter and output type errors at development time, not runtime
- **IDE support** — `params.domain` provides autocompletion, `param["domain"]` does not
- **Auto-generated manifest** — Python code is the single source of truth; no hand-editing 600+ line JSON files
- **Built-in testing** — `soarapps test unit` and `soarapps test integration` replace manual pudb debugging
- **Modern tooling** — `uv` for dependency management, `pyproject.toml` for project metadata

### Code Quality
- **Modularity** — Each action in its own file; HTTP client separated from business logic
- **Pythonic error handling** — `raise ActionFailure()` instead of manual `set_status(APP_ERROR, ...)`
- **Standard logging** — Python `logging` module instead of custom framework methods
- **Smaller codebase** — `hunt_domain`: 25 lines (legacy) → 12 lines (SDK)
- **Mockable client** — Inject/mock `UrlscanClient` for unit tests instead of monkey-patching `requests`

### Security & Reliability
- **Encrypted sensitive fields** — `sensitive=True` on `AssetField` automatically encrypts API keys at rest
- **Framework-level validation** — Required parameters, type enforcement, and CEF mappings handled before handler runs
- **Modern HTTP** — `httpx` supports async, connection pooling, and better timeout handling than `requests`

---

# Part 3 — Partial Implementation (hunt_domain)

Below is the complete SDK-style implementation of the **hunt_domain** action, demonstrating all key SDK patterns: action definition, handler, REST call logic, error handling, and result formatting.

## 3.1 Action Definition

The action is registered in `app.py` using `register_action()`:

```python
# src/app.py
app.register_action(
    "actions.hunt_domain:hunt_domain",    # Module path : function name
    action_type="investigate",             # Action type for SOAR UI
    identifier="hunt_domain",              # Unique action identifier
    name="hunt domain",                    # Display name
    description="Search for a domain on urlscan.io",
    verbose="Search urlscan.io for scans associated with a domain.",
    read_only=True,                        # Does not modify any data
)
```

**What this replaces from legacy:**
- The `urlscan.json` action definition (20+ lines of JSON)
- The `elif action_id == "hunt_domain":` branch in `handle_action()`

---

## 3.2 Handler Implementation

```python
# src/actions/hunt_domain.py

from soar_sdk.logging import getLogger
from ..client import UrlscanClient
from ..models.outputs import HuntOutput
from ..models.params import HuntDomainParams

logger = getLogger()


def hunt_domain(params: HuntDomainParams, asset) -> HuntOutput:
    """Search urlscan.io for scans associated with a domain."""
    logger.debug(f"Searching urlscan.io for domain: {params.domain}")

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

### Function Signature Explained

| Parameter | Type | Injected By | Purpose |
|-----------|------|-------------|---------|
| `params` | `HuntDomainParams` | SDK (validated) | Contains `domain: str` — the search target |
| `asset` | `Asset` | SDK (auto-injected) | Contains `api_key` and `timeout` from asset config |
| Return | `HuntOutput` | SDK (auto-wrapped) | Typed output with `results`, `total`, `has_more` |

---

## 3.3 REST Call Logic

The HTTP call is handled by the `UrlscanClient` — a standalone, typed client class:

```python
# src/client.py

import httpx
from soar_sdk.exceptions import ActionFailure
from soar_sdk.logging import getLogger

logger = getLogger()
BASE_URL = "https://urlscan.io"


class UrlscanClient:
    """Typed HTTP client for urlscan.io API."""

    def __init__(self, api_key: str | None = None, timeout: int = 120):
        self._api_key = api_key
        self._timeout = timeout

    def _build_headers(self) -> dict[str, str]:
        headers: dict[str, str] = {}
        if self._api_key:
            headers["API-Key"] = self._api_key
        return headers

    def _request(self, method: str, endpoint: str, **kwargs) -> httpx.Response:
        url = f"{BASE_URL}{endpoint}"
        headers = self._build_headers()
        with httpx.Client(timeout=self._timeout) as client:
            response = client.request(method, url, headers=headers, **kwargs)
        return response

    def search_domain(self, domain: str) -> dict:
        """Search urlscan.io for a domain."""
        response = self._request("GET", f"/api/v1/search/?q=domain:{domain}")
        if not response.is_success:
            raise ActionFailure(
                f"Domain search failed: {response.status_code} - {response.text}"
            )
        return response.json()
```

### What Changed From Legacy

| Legacy `_make_rest_call` | SDK `UrlscanClient` |
|--------------------------|---------------------|
| Lives on the connector class | Standalone, injectable class |
| Uses `requests` | Uses `httpx` (async-ready) |
| Dynamic method via `getattr(requests, method)` | Explicit typed methods per endpoint |
| Returns `RetVal(status, data)` | Returns typed dict or raises `ActionFailure` |
| Processes response in 5 separate methods | `httpx` handles JSON/binary natively |
| Coupled to `action_result` | Independent of SOAR framework |

---

## 3.4 Error Handling

### At the Client Level

```python
def search_domain(self, domain: str) -> dict:
    response = self._request("GET", f"/api/v1/search/?q=domain:{domain}")
    if not response.is_success:
        raise ActionFailure(
            f"Domain search failed: {response.status_code} - {response.text}"
        )
    return response.json()
```

- **Non-2xx responses** → `ActionFailure` is raised with status code and response body
- **Network errors** → `httpx` raises `httpx.ConnectError`, `httpx.TimeoutException`, etc.
- **JSON parse errors** → `httpx` raises `json.JSONDecodeError`

### At the SDK Framework Level

The SDK catches exceptions and maps them:

| Exception | SOAR Result |
|-----------|-------------|
| `ActionFailure("message")` | `APP_ERROR` with the provided message |
| Any other unhandled exception | `APP_ERROR` with "Unexpected error" + stack trace |
| No exception + return `HuntOutput(...)` | `APP_SUCCESS` with typed output data |

**Comparison with legacy:**

```python
# Legacy — manual status checking at every step
ret_val, response = self._make_rest_call(endpoint, action_result, ...)
if phantom.is_fail(ret_val):
    if not action_result.get_message():
        error_msg = response.get("message") or URLSCAN_NO_DATA_ERROR
        return action_result.set_status(phantom.APP_ERROR, error_msg)
    return action_result.get_status()

# SDK — Pythonic exception flow
response = client.search_domain(params.domain)  # Raises ActionFailure on error
# If we reach here, it succeeded
```

---

## 3.5 Result Formatting

### Typed Parameters (Input)

```python
# src/models/params.py
from soar_sdk.params import Param, Params

class HuntDomainParams(Params):
    domain: str = Param(
        description="Domain to search for in urlscan.io",
        primary=True,          # Primary input field in SOAR UI
        cef_types=["domain"],  # Maps to CEF domain field for correlation
    )
```

- **`primary=True`** marks this as the main input visible in playbook design
- **`cef_types=["domain"]`** enables SOAR to auto-populate from container artifacts
- **Type `str`** is enforced by Pydantic before the handler runs

### Typed Output

```python
# src/models/outputs.py
from soar_sdk.action_results import ActionOutput, OutputField

class HuntOutput(ActionOutput):
    results: list[dict] = OutputField(example_values=[])
    total: int = OutputField(example_values=[0, 10, 100])
    has_more: bool = OutputField(example_values=[True, False])
```

The SDK uses this output model to:
1. **Generate datapaths** for playbooks: `action_result.data.*.results`, `action_result.data.*.total`
2. **Provide example values** in auto-generated documentation
3. **Type-check** the return value at runtime
4. **Auto-generate** the `urlscan.json` manifest output section

---

## 3.6 Side-by-Side Comparison

### Legacy hunt_domain (25 lines)

```python
def _handle_hunt_domain(self, param):
    self.debug_print(f"In action handler for {self.get_action_identifier()}")
    action_result = self.add_action_result(ActionResult(dict(param)))
    headers = {"API-Key": self._api_key}
    domain = param["domain"]

    ret_val, response = self._make_rest_call(
        URLSCAN_HUNT_DOMAIN_ENDPOINT.format(domain),
        action_result, params=None, headers=headers)

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

### SDK hunt_domain (12 lines)

```python
def hunt_domain(params: HuntDomainParams, asset) -> HuntOutput:
    """Search urlscan.io for scans associated with a domain."""
    logger.debug(f"Searching urlscan.io for domain: {params.domain}")

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

### What the SDK Eliminates

| Boilerplate (Legacy) | Handled by SDK |
|----------------------|----------------|
| `self.add_action_result(ActionResult(dict(param)))` | Automatic ActionResult creation |
| `self.get_action_identifier()` | Decorator-based routing |
| `if phantom.is_fail(ret_val):` error checking | `ActionFailure` exception flow |
| `action_result.set_status(phantom.APP_SUCCESS, ...)` | Return typed output = success |
| `action_result.add_data(response)` | Return typed output = auto-wrapped |
| Manual header construction | Client class handles headers |
| Manual `_make_rest_call` invocation | Typed client methods |

---

## Appendix — Full Implementation File Listing

The complete SDK implementation is in the `urlscan_io/` directory. All 6 actions are implemented:

| Action | Implementation File | Key Features |
|--------|-------------------|--------------|
| **test_connectivity** | `src/app.py` | `@app.test_connectivity()` decorator |
| **hunt_domain** | `src/actions/hunt_domain.py` | Typed params/output, search client |
| **hunt_ip** | `src/actions/hunt_ip.py` | Same pattern as hunt_domain |
| **get_report** | `src/actions/get_report.py` | Polling via client, `SOARClient[ReportSummary]` |
| **detonate_url** | `src/actions/detonate_url.py` | Polling, vault integration, tag parsing |
| **get_screenshot** | `src/actions/get_screenshot.py` | `soar.vault.create_attachment()` |

Supporting files:
- `src/client.py` — `UrlscanClient` with all API methods + polling logic
- `src/models/params.py` — Pydantic `Params` classes for all actions
- `src/models/outputs.py` — Pydantic `ActionOutput` classes for all actions
- `pyproject.toml` — Project metadata, dependencies, app entry point
