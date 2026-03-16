# Part 1: Legacy urlscan.io SOAR Connector — Architecture Analysis

## 1. Overview

The **urlscan.io connector** (v2.6.3) is a legacy Splunk SOAR app built on the `BaseConnector` framework. It integrates with the urlscan.io REST API to provide URL scanning, threat intelligence lookups, and screenshot capture within SOAR playbooks and manual investigations.

**Source Files:**
| File | Purpose |
|---|---|
| `urlscan_connector.py` | Main connector class — all action handlers and REST logic |
| `urlscan_consts.py` | Constants — URLs, endpoints, error messages, action identifiers |
| `urlscan.json` | App manifest — metadata, actions, parameters, output schemas |

**App Identity:**
- App ID: `c46c00cd-7231-4dd3-8d8e-02b9fa0e14a2`
- Type: `sandbox`
- Python: 3.9, 3.13
- Min SOAR version: `6.2.1`
- FIPS compliant: Yes

---

## 2. Architecture — BaseConnector Framework

### 2.1 Class Hierarchy

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

### 2.2 App Lifecycle

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

### 2.3 Initialization (`initialize()`)

```python
def initialize(self):
    self._state = self.load_state()
    if not isinstance(self._state, dict):
        self._state = {"app_version": self.get_app_json().get("app_version")}
    config = self.get_config()
    self._api_key = config.get("api_key", "")
    self.timeout = config.get("timeout", 120)
    self.set_validator("ipv6", self._is_ip)
    return phantom.APP_SUCCESS
```

Key operations:
1. **State loading** — `load_state()` retrieves persisted dict from previous runs
2. **Config extraction** — `get_config()` reads asset configuration (API key, timeout)
3. **Validator registration** — Custom IPv6 validator for the `_is_ip` method
4. **Graceful degradation** — API key defaults to empty string (some actions work without it)

### 2.4 Finalization (`finalize()`)

```python
def finalize(self):
    self.save_state(self._state)
    return phantom.APP_SUCCESS
```

Persists `self._state` across action runs and app upgrades.

---

## 3. Action Dispatching

### 3.1 The `handle_action()` Dispatcher

```python
def handle_action(self, param):
    ret_val = phantom.APP_SUCCESS
    action_id = self.get_action_identifier()

    if action_id == URLSCAN_TEST_CONNECTIVITY_ACTION:     # "test_connectivity"
        ret_val = self._handle_test_connectivity(param)
    elif action_id == URLSCAN_GET_REPORT_ACTION:           # "get_report"
        ret_val = self._handle_get_report(param)
    elif action_id == URLSCAN_HUNT_DOMAIN_ACTION:          # "hunt_domain"
        ret_val = self._handle_hunt_domain(param)
    elif action_id == URLSCAN_HUNT_IP_ACTION:              # "hunt_ip"
        ret_val = self._handle_hunt_ip(param)
    elif action_id == URLSCAN_DETONATE_URL_ACTION:         # "detonate_url"
        ret_val = self._handle_detonate_url(param)
    elif action_id == URLSCAN_GET_SCREENSHOT_ACTION:       # "get_screenshot"
        ret_val = self._handle_get_screenshot(param)
    return ret_val
```

**Pattern:** Manual `if/elif` chain mapping string identifiers → handler methods.

**Actions registered in `urlscan.json`:**

| Action Identifier | Type | Handler Method | API Endpoint |
|---|---|---|---|
| `test_connectivity` | test | `_handle_test_connectivity` | `GET /user/quotas/` |
| `get_report` | investigate | `_handle_get_report` | `GET /api/v1/result/{uuid}` |
| `hunt_domain` | investigate | `_handle_hunt_domain` | `GET /api/v1/search/?q=domain:{domain}` |
| `hunt_ip` | investigate | `_handle_hunt_ip` | `GET /api/v1/search/?q=ip:"{ip}"` |
| `detonate_url` | generic | `_handle_detonate_url` | `POST /api/v1/scan/` |
| `get_screenshot` | investigate | `_handle_get_screenshot` | `GET /screenshots/{uuid}.png` |

---

## 4. Parameter Handling

Parameters come from two sources:

### 4.1 Asset Configuration (from `get_config()`)
Read once in `initialize()`, stored as instance variables:
```python
self._api_key = config.get("api_key", "")     # Optional API key (password field)
self.timeout = config.get("timeout", 120)       # Request timeout (numeric, default 120)
```

### 4.2 Action Parameters (from `param` dict)
Each handler receives a `param` dictionary. Example from `_handle_detonate_url`:
```python
url_to_scan = param["url"]                      # Required
private = param.get("private", False)           # Optional, default False
custom_agent = param.get("custom_agent")        # Optional
get_result = param.get("get_result", True)      # Optional, default True
addto_vault = param.get("addto_vault", False)   # Optional, default False
tags = param.get("tags", "")                    # Optional comma-separated string
```

### 4.3 Parameter Validation
- **Integer validation**: `_validate_integer()` checks type, zero, and negative values
- **IP validation**: `_is_ip()` using `ipaddress.ip_address()` for IPv4/IPv6
- **Tags validation**: Max 10 tags enforced (`URLSCAN_MAX_TAGS_NUM`)
- **API key presence**: Checked at action level (e.g., detonate requires it)

---

## 5. REST Call Architecture

### 5.1 Centralized REST Client (`_make_rest_call`)

```python
def _make_rest_call(self, endpoint, action_result, headers=None,
                    params=None, data=None, method="get"):
    config = self.get_config()
    request_func = getattr(requests, method)    # Dynamic method dispatch
    url = f"{self._base_url}{endpoint}"         # URL = base + endpoint

    try:
        r = request_func(
            url, json=data, headers=headers,
            verify=config.get("verify_server_cert", False),
            params=params, timeout=self.timeout
        )
    except Exception as e:
        return RetVal(action_result.set_status(
            phantom.APP_ERROR, URLSCAN_SERVER_CONNECTIVITY_ERROR.format(...)
        ), None)

    return self._process_response(r, action_result)
```

**Design choices:**
- Uses `requests` library directly (not `httpx`)
- Dynamic method selection via `getattr(requests, method)`
- URL construction: `URLSCAN_BASE_URL` + endpoint with `.format()` interpolation
- SSL verification from config (`verify_server_cert`)
- Configurable timeout (default 120s)
- `json=data` — always sends JSON payloads

### 5.2 Response Processing Pipeline (`_process_response`)

Response is routed by `Content-Type` header:

```
_process_response(r, action_result)
    │
    ├── "json" in Content-Type  ──→ _process_json_response()
    │       Parse JSON, check status (200-399 = success)
    │       Special case: 404 with status field → still APP_SUCCESS (scan not ready)
    │
    ├── "html" in Content-Type  ──→ _process_html_response()
    │       Parse with BeautifulSoup, strip scripts/style/footer/nav
    │       Return sanitized error text
    │
    ├── "image" or "octet-stream" ──→ _process_file_response()
    │       Return raw response object (for screenshots)
    │
    ├── empty body ──→ _process_empty_response()
    │       200 = success with {}, else error
    │
    └── anything else ──→ error with status code and body text
```

### 5.3 RetVal Pattern

```python
class RetVal(tuple):
    def __new__(cls, val1, val2):
        return tuple.__new__(RetVal, (val1, val2))
```

Every REST call returns a 2-tuple: `(status, data)` where:
- `status` = `phantom.APP_SUCCESS` or `phantom.APP_ERROR`
- `data` = parsed response (dict, response object, or None)

Usage pattern in handlers:
```python
ret_val, response = self._make_rest_call(endpoint, action_result, ...)
if phantom.is_fail(ret_val):
    return action_result.get_status()
```

---

## 6. Result Formatting

### 6.1 ActionResult Objects

Each handler creates an `ActionResult` and adds it to the connector:
```python
action_result = self.add_action_result(ActionResult(dict(param)))
```

Results are populated with:
```python
action_result.add_data(response)                    # Full API response data
action_result.update_summary({"key": value})        # Summary for UI display
action_result.set_status(phantom.APP_SUCCESS, msg)  # Final status + message
```

### 6.2 Null Value Replacement
```python
def replace_null_values(self, data):
    return json.loads(json.dumps(data).replace("\\u0000", "\\\\u0000"))
```
Handles null bytes in API responses that would break JSON handling downstream.

### 6.3 Vault Integration (Screenshots)

`_add_file_to_vault()` handles binary file storage:
1. Detect MIME type with `python-magic`
2. Write to temp file in vault tmp directory
3. Add to vault via `ph_rules.vault_add()`
4. Retrieve metadata via `ph_rules.vault_info()`
5. Store vault ID, file name, type, size in action summary

---

## 7. Error Handling Strategy

### 7.1 Exception Extraction
```python
def _get_error_message_from_exception(self, e):
    error_code = URLSCAN_ERROR_CODE_UNAVAILABLE       # "Error code unavailable"
    error_message = URLSCAN_ERROR_MESSAGE_UNAVAILABLE  # "Error message unavailable..."
    try:
        if e.args:
            if len(e.args) > 1:
                error_code = e.args[0]
                error_message = e.args[1]
            elif len(e.args) == 1:
                error_message = e.args[0]
    except Exception:
        pass  # Fallback to default messages
    return f"Error Code: {error_code}. Error Message: {error_message}"
```

### 7.2 Error Propagation Layers

```
Exception in requests  →  _make_rest_call catches, sets APP_ERROR
      ↓
Bad HTTP status        →  _process_*_response sets APP_ERROR with details
      ↓
Business logic error   →  Handler checks response, sets APP_ERROR with message
      ↓
All flow through       →  action_result.get_status() returns to handle_action
```

### 7.3 Error Constants

All error messages are centralized in `urlscan_consts.py`:
- **Connection errors**: `URLSCAN_SERVER_CONNECTIVITY_ERROR`
- **Parse errors**: `URLSCAN_JSON_RESPONSE_PARSE_ERROR`
- **Server errors**: `URLSCAN_JSON_RESPONSE_SERVER_ERROR`
- **Business errors**: `URLSCAN_API_KEY_MISSING_ERROR`, `URLSCAN_REPORT_UUID_MISSING_ERROR`, `URLSCAN_BAD_REQUEST_ERROR`
- **Data errors**: `URLSCAN_NO_DATA_ERROR`, `URLSCAN_REPORT_NOT_FOUND_ERROR`

### 7.4 XSS Prevention in HTML Error Responses
```python
message = message.replace("{", "{{").replace("}", "}}")
```
Curly braces are escaped to prevent format string injection in error messages from HTML responses.

---

## 8. Polling Mechanism (`_poll_submission`)

The "detonate url" and "get report" actions use a polling loop to wait for scan completion:

```python
def _poll_submission(self, report_uuid, action_result, get_result=True):
    polling_attempt = 0
    while polling_attempt < URLSCAN_MAX_POLLING_ATTEMPTS:  # Max 10
        polling_attempt += 1
        self.send_progress(f"Polling attempt {polling_attempt} of {URLSCAN_MAX_POLLING_ATTEMPTS}")

        ret_val, resp_json = self._make_rest_call(
            URLSCAN_POLL_SUBMISSION_ENDPOINT.format(report_uuid), ...)

        if phantom.is_fail(ret_val):
            # 400 = bad request (real error), return immediately
            if resp_json and resp_json.get("status", 0) == URLSCAN_BAD_REQUEST_CODE:
                return action_result.set_status(phantom.APP_ERROR, ...)
            return action_result.get_status()

        # 404 or "notdone" = scan still pending
        if resp_json.get("status", 0) == URLSCAN_NOT_FOUND_CODE or \
           resp_json.get("message") == "notdone":
            time.sleep(URLSCAN_POLLING_INTERVAL)  # 15 seconds
            continue

        # Scan complete
        action_result.add_data(resp_json)
        return action_result.set_status(phantom.APP_SUCCESS, ...)

    # Exhausted attempts
    return action_result.set_status(phantom.APP_SUCCESS, URLSCAN_REPORT_NOT_FOUND_ERROR)
```

**Configuration:**
- `URLSCAN_MAX_POLLING_ATTEMPTS = 10`
- `URLSCAN_POLLING_INTERVAL = 15` seconds
- Maximum wait: 10 × 15 = **150 seconds**

---

## 9. Logging

The connector uses `BaseConnector`'s built-in logging:
- `self.debug_print(msg)` — Debug-level logs
- `self.error_print(msg)` — Error-level logs
- `self.save_progress(msg)` — Persistent progress messages (visible in UI)
- `self.send_progress(msg)` — Transient progress messages (overwritten by next)
- `self._dump_error_log(error, message)` — Formatted error dumps

---

## 10. Key Architectural Observations

### Strengths
1. **Centralized REST logic** — Single `_make_rest_call` with consistent error handling
2. **Content-type routing** — Clean separation of JSON/HTML/file/empty response processing
3. **Polling abstraction** — Reusable `_poll_submission` for async scan results
4. **Configuration flexibility** — Works with or without API key for different action subsets
5. **Null-byte safety** — `replace_null_values` prevents downstream JSON parsing failures

### Weaknesses
1. **No type safety** — All parameters are untyped dicts; no validation at the framework level
2. **Manual dispatch** — `if/elif` chain in `handle_action()` is error-prone and hard to extend
3. **Monolithic class** — All actions, REST logic, file handling, and polling live in one file
4. **`requests` library** — Synchronous-only HTTP, no connection pooling or async support
5. **Magic access to internals** — `action_result._ActionResult__data` (name-mangled private attribute)
6. **No testing infrastructure** — Debug entry point (`if __name__ == "__main__"`) uses `pudb` but no unit test framework
7. **Error message construction** — Complex string formatting with `replace("{", "{{")` is fragile
8. **Blocking sleep** — `time.sleep(15)` blocks the entire process during polling
