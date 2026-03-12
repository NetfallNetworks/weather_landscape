# Cancun Weather Landscape — Detailed Implementation Plan

**Feature:** Add international location support, starting with Cancun, Mexico (MX77400)
**Status:** Not Started
**Branch:** `claude/add-cancun-weather-landscapes-9o5y9`
**Architecture Decision:** [plans/add-cancun-weather-landscapes.md](../plans/add-cancun-weather-landscapes.md)

---

## Overview

Extend the location identifier system from US-only 5-digit ZIP codes to support
international postal codes using a `CC#####` prefix format (e.g. `MX77400`).
First location: Cancun, Mexico — Hotel Riu Dunamar, postal code 77400.

**Identifier convention:**
- US ZIP: `78729` (unchanged, backward compatible)
- International: `MX77400` — 2-letter ISO 3166-1 alpha-2 country prefix + postal digits
- Detection: `code[0].isalpha()` → international; `code[0].isdigit()` → US ZIP
- Parsing: `code[:2]` = country, `code[2:]` = postal

---

## Phases

### Phase 1: Shared Validation Function + Web Layer

**Objective:** Create `is_valid_location()` and update all validation sites in the
web worker so the admin UI and URL routing accept `MX77400`.

**Agent:** Builder (Sonnet 4.6)

#### Task 1.1 — Add `is_valid_location()` to `workers/web/src/web_utils.py`

**File:** `workers/web/src/web_utils.py`
**Location:** After imports (line 9), before `to_js()` (line 12)

```python
import re

def is_valid_location(loc_id):
    """Validate location identifier.

    Accepts:
        - US ZIP code: exactly 5 digits (e.g. '78729')
        - International: 2 uppercase letters + 4-10 digits (e.g. 'MX77400')

    Args:
        loc_id: Location identifier string.

    Returns:
        bool: True if valid.
    """
    if not loc_id or not isinstance(loc_id, str):
        return False
    if re.match(r'^\d{5}$', loc_id):
        return True
    if re.match(r'^[A-Z]{2}\d{4,10}$', loc_id):
        return True
    return False
```

**Security notes:**
- Allowlist-based validation (reject by default)
- No regex backtracking risk (simple alternation of fixed patterns)
- Bounds checking: postal code limited to 4-10 digits

#### Task 1.2 — Update R2 scanning validation

**File:** `workers/web/src/web_utils.py`

| Line | Current | New |
|------|---------|-----|
| 223 | `if zip_code.isdigit() and len(zip_code) == 5:` | `if is_valid_location(zip_code):` |
| 253 | `if zip_code.isdigit() and len(zip_code) == 5 and len(parts) > 1:` | `if is_valid_location(zip_code) and len(parts) > 1:` |

#### Task 1.3 — Update URL route matching

**File:** `workers/web/src/web.py`
**Add import** at top (after existing web_utils imports):
```python
from web_utils import is_valid_location
```

| Line | Current | New |
|------|---------|-----|
| 82 | `if part and part.isdigit() and len(part) == 5:` | `if part and is_valid_location(part):` |

#### Task 1.4 — Update admin endpoint validation (5 endpoints)

**File:** `workers/web/src/web.py`

All changes follow the same pattern — replace inline validation with `is_valid_location()`:

| Endpoint | Line | Current check | Error message update |
|----------|------|--------------|---------------------|
| `_handle_activate` | 515 | `zip_code.isdigit() and len(zip_code) == 5` | `"Invalid location. Use US ZIP (78729) or international code (MX77400)."` |
| `_handle_format_add` | 574 | `zip_code.isdigit() and len(zip_code) == 5` | same |
| `_handle_format_remove` | 610 | `zip_code.isdigit() and len(zip_code) == 5` | same |
| `_handle_format_get` | 644 | `zip_code.isdigit() and len(zip_code) == 5` | same |
| `_handle_generate` | 673 | `zip_code.isdigit() and len(zip_code) == 5` | same |

**Pre-existing bug found:** `_handle_deactivate` (line 542) only checks `if not zip_code`
— no format validation at all. Add `is_valid_location()` check here too for consistency.

| Endpoint | Line | Current check | New check |
|----------|------|--------------|-----------|
| `_handle_deactivate` | 542 | `if not zip_code:` | `if not zip_code or not is_valid_location(zip_code):` |

That makes **7 total validation sites** in web.py (6 existing + 1 bug fix).

#### Task 1.5 — Update admin.html client-side validation

**File:** `workers/web/src/assets/templates/admin.html`

| Line | Element | Current | New |
|------|---------|---------|-----|
| 36 | `<h2>` | `Add New ZIP Code` | `Add New Location` |
| 38-39 | `<input>` attributes | `maxlength="5" pattern="[0-9]{5}"` | `maxlength="12" pattern="(\d{5}\|[A-Z]{2}\d{4,10})"` |
| 38-39 | `<input>` placeholder | `placeholder="12345"` | `placeholder="78729 or MX77400"` |
| 40 | `<button>` text | `Add ZIP` | `Add` |
| 48 | `<th>` | `ZIP Code` | `Location` |
| 148 | JS regex | `/^\d{5}$$/.test(zip)` | `/^(\d{5}\|[A-Z]{2}\d{4,10})$/.test(zip.toUpperCase())` |
| 149 | JS error | `'Please enter a valid 5-digit ZIP code'` | `'Enter a US ZIP (78729) or international code (MX77400)'` |
| 185 | Button reset text | `'Add ZIP'` | `'Add'` |

**Note:** The `.toUpperCase()` in the JS validation ensures users can type `mx77400`
and have it accepted. The server-side `is_valid_location()` requires uppercase, so
the `addNewZip()` function should also send `zip.toUpperCase()` in the fetch calls.

Add to `addNewZip()` after validation passes (around line 152):
```javascript
const normalizedZip = zip.toUpperCase();
```
Then use `normalizedZip` in all subsequent fetch URLs and toast messages.

#### Phase 1 — Tests

1. **Unit validation:** Inline test at bottom of web_utils.py (or separate script):
   - `is_valid_location('78729')` → True
   - `is_valid_location('MX77400')` → True
   - `is_valid_location('mx77400')` → False (must be uppercase — server enforces)
   - `is_valid_location('7872')` → False (too short)
   - `is_valid_location('787299')` → False (too long for US)
   - `is_valid_location('M77400')` → False (1 letter)
   - `is_valid_location('MXX7400')` → False (3 letters)
   - `is_valid_location('')` → False
   - `is_valid_location(None)` → False
   - `is_valid_location('../../etc')` → False (path traversal)

2. **`run_test.py`** — must still pass (backward compat, no location identifier changes needed)

#### Phase 1 — Definition of Done

- [ ] `is_valid_location()` exists in web_utils.py with docstring
- [ ] All 7 validation sites in web.py use `is_valid_location()`
- [ ] admin.html accepts both `78729` and `MX77400` input
- [ ] admin.html normalizes to uppercase before sending to server
- [ ] Error messages are descriptive and mention both formats
- [ ] `python run_test.py` passes
- [ ] Unit validation assertions pass for all 10 test cases above
- [ ] No hardcoded 5-digit assumptions remain in web worker

#### Phase 1 — QA Review Gate

Run 4-agent QA review on changed files:
- `workers/web/src/web_utils.py`
- `workers/web/src/web.py`
- `workers/web/src/assets/templates/admin.html`

---

### Phase 2: Geocoding — International Postal Code Support

**Objective:** Make the weather-fetcher worker resolve `MX77400` to lat/lon via
OpenWeatherMap's international geocoding endpoint.

**Agent:** Integrator (Sonnet 4.6)

#### Task 2.1 — Update fetcher geocoding

**File:** `workers/fetcher/src/kv_utils.py`
**Function:** `geocode_zip()` (line 13)
**Change at line 43:**

Current:
```python
url = f"http://api.openweathermap.org/geo/1.0/zip?zip={zip_code},US&appid={api_key}"
```

New:
```python
# Parse location identifier for geocoding
if len(zip_code) > 2 and zip_code[:2].isalpha():
    # International: CC prefix + postal (e.g. MX77400 → 77400,MX)
    country = zip_code[:2].upper()
    postal = zip_code[2:]
    geo_param = f"{postal},{country}"
else:
    # US ZIP (e.g. 78729 → 78729,US)
    geo_param = f"{zip_code},US"

url = f"http://api.openweathermap.org/geo/1.0/zip?zip={geo_param}&appid={api_key}"
```

Also update the docstring (line 18) from `"US ZIP code as string"` to
`"Location identifier (US ZIP or CC+postal format)"`.

Also update the print/log message at line 41 from `"Geocoding ZIP"` to `"Geocoding location"`.

**Security notes:**
- The `geo_param` value is interpolated into a URL. The postal code is digits-only
  (validated upstream by `is_valid_location`), and country code is 2 uppercase letters.
  No injection risk.
- The upstream OWM API will return 404 for invalid country codes, which is handled
  by the existing `response.status != 200` check at line 46.

#### Task 2.2 — Update local test geocoding

**File:** `test_local_generation.py`
**Function:** `geocode_zip()` (line 17)

Apply identical country-code parsing logic. Current line 28:
```python
url = f"http://api.openweathermap.org/geo/1.0/zip?zip={zip_code},US&appid={api_key}"
```

New:
```python
if len(zip_code) > 2 and zip_code[:2].isalpha():
    country = zip_code[:2].upper()
    postal = zip_code[2:]
    geo_param = f"{postal},{country}"
else:
    geo_param = f"{zip_code},US"
url = f"http://api.openweathermap.org/geo/1.0/zip?zip={geo_param}&appid={api_key}"
```

#### Task 2.3 — Update secrets.py.example

**File:** `secrets.py.example`

Current:
```python
# Your ZIP code (US only)
# The test script will geocode this to lat/lon using OpenWeatherMap API
ZIP_CODE = "78729"  # Austin, TX
```

New:
```python
# Location identifier
# US ZIP codes: "78729" (Austin, TX)
# International: "MX77400" (Cancun, Mexico) — 2-letter country prefix + postal code
ZIP_CODE = "78729"  # Austin, TX
```

#### Phase 2 — Tests

1. **URL construction verification** (no live API call needed):
   - Parse `MX77400` → assert `geo_param == "77400,MX"`
   - Parse `78729` → assert `geo_param == "78729,US"`
   - Parse `BR01310100` → assert `geo_param == "01310100,BR"` (future-proofing)

2. **`run_test.py`** — must still pass

#### Phase 2 — Definition of Done

- [ ] `geocode_zip()` in kv_utils.py parses CC prefix correctly
- [ ] `geocode_zip()` in test_local_generation.py matches
- [ ] `MX77400` produces OWM URL `zip=77400,MX`
- [ ] `78729` still produces OWM URL `zip=78729,US`
- [ ] secrets.py.example documents international format
- [ ] `python run_test.py` passes
- [ ] URL construction assertions pass

#### Phase 2 — QA Review Gate

Run 4-agent QA review on changed files:
- `workers/fetcher/src/kv_utils.py`
- `test_local_generation.py`
- `secrets.py.example`

---

### Phase 3: Temperature Units — Celsius for International Locations

**Objective:** International locations display temperature in Celsius;
US locations remain Fahrenheit.

**Agent:** Builder (Sonnet 4.6)

#### Task 3.1 — Add `location_id` to `to_weather_config()`

**File:** `workers/landscape/src/landscape_utils.py`
**Function:** `to_weather_config()` (line 57)

Change signature from:
```python
def to_weather_config(self, lat, lon, format_name=None):
```
To:
```python
def to_weather_config(self, lat, lon, format_name=None, location_id=None):
```

Update docstring to include:
```
    location_id: Location identifier (e.g. '78729', 'MX77400').
                 International locations (CC prefix) use Celsius.
```

After `config = config_class()` (line 80), before `config.OWM_KEY` (line 82), add:
```python
# International locations use Celsius
if location_id and len(location_id) > 2 and location_id[:2].isalpha():
    from p_weather.configuration import WLBaseSettings
    config.TEMPUNITS_MODE = WLBaseSettings.TEMP_UNITS_CELSIUS
```

#### Task 3.2 — Pass `location_id` from landscape generator

**File:** `workers/landscape/src/landscape_generator.py`
**Line 118:**

Current:
```python
weather_config = config.to_weather_config(lat=lat, lon=lon, format_name=format_name)
```

New:
```python
weather_config = config.to_weather_config(
    lat=lat, lon=lon, format_name=format_name, location_id=zip_code
)
```

#### Task 3.3 — Update local test for Celsius

**File:** `test_local_generation.py`

After config creation (after line 72 `config.OWM_LON = lon`), add:
```python
# International locations use Celsius
if len(zip_code) > 2 and zip_code[:2].isalpha():
    from p_weather.configuration import WLBaseSettings
    config.TEMPUNITS_MODE = WLBaseSettings.TEMP_UNITS_CELSIUS
```

Update the print output (line 88) to show temperature unit:
```python
unit = "Celsius" if len(zip_code) > 2 and zip_code[:2].isalpha() else "Fahrenheit"
print(f"   Temperature: {unit}")
```

#### Phase 3 — Tests

1. **Config construction verification:**
   - Create config with `location_id='MX77400'` → assert `config.TEMPUNITS_MODE == TEMP_UNITS_CELSIUS`
   - Create config with `location_id='78729'` → assert `config.TEMPUNITS_MODE == TEMP_UNITS_FAHRENHEIT`
   - Create config with `location_id=None` → assert `config.TEMPUNITS_MODE == TEMP_UNITS_FAHRENHEIT`

2. **`python run_test.py`** — must still pass (uses config classes directly, no location_id)

#### Phase 3 — Definition of Done

- [ ] `to_weather_config()` accepts `location_id` parameter
- [ ] `MX77400` produces config with `TEMP_UNITS_CELSIUS`
- [ ] `78729` produces config with `TEMP_UNITS_FAHRENHEIT`
- [ ] `None` location_id defaults to Fahrenheit (backward compat)
- [ ] `test_local_generation.py` applies Celsius for international locations
- [ ] `python run_test.py` passes
- [ ] Config construction assertions pass

#### Phase 3 — QA Review Gate

Run 4-agent QA review on changed files:
- `workers/landscape/src/landscape_utils.py`
- `workers/landscape/src/landscape_generator.py`
- `test_local_generation.py`

---

### Phase 4: Integration Testing + Final Verification

**Objective:** End-to-end validation that the full pipeline works for both
`78729` and `MX77400`.

**Agent:** Tester (Sonnet 4.6)

#### Task 4.1 — Run all local tests

```bash
python run_test.py                    # Image generation (no API key needed)
```

Verify: all 5 formats generate without errors.

#### Task 4.2 — Trace the full data flow (code review)

Walk through the pipeline with identifier `MX77400`:

1. **Scheduler** reads `active_zips` from KV → list contains `"MX77400"` → enqueues `{zip_code: "MX77400"}` to fetch-jobs queue. **No code changes needed** — string passes through.

2. **Fetcher** receives `{zip_code: "MX77400"}`:
   - `geocode_zip(env, "MX77400", api_key)` → parses prefix → calls `zip=77400,MX` → returns `{lat: 21.26, lon: -86.81}` → caches as `geo:MX77400`
   - `fetch_weather_from_owm(api_key, 21.26, -86.81)` → standard lat/lon call, works globally
   - `store_weather_data(env, "MX77400", data)` → stores as `weather:MX77400` with TTL
   - Enqueues `{zip_code: "MX77400", lat: 21.26, lon: -86.81}` to weather-ready queue

3. **Dispatcher** receives weather-ready event → reads `formats:MX77400` from KV → creates one landscape-job per format → enqueues to landscape-jobs queue. **No code changes needed.**

4. **Landscape Generator** receives job:
   - `get_weather_data(env, "MX77400")` → reads `weather:MX77400` from KV
   - `config.to_weather_config(lat=21.26, lon=-86.81, format_name="rgb_light", location_id="MX77400")` → detects CC prefix → sets Celsius
   - Generates image with Celsius temperatures
   - `upload_to_r2(env, bytes, metadata, "MX77400", "rgb_light")` → uploads to `MX77400/rgb_light.png`

5. **Web Worker** serves request for `/MX77400`:
   - URL matching: `is_valid_location("MX77400")` → True → serves image from R2 key `MX77400/rgb_light.png`

6. **Admin** at `/admin`:
   - `get_all_zips_from_r2()` → scans R2 → `is_valid_location("MX77400")` → included in list
   - Activate `MX77400` → `is_valid_location("MX77400")` → passes → added to `active_zips`

#### Task 4.3 — Verify backward compatibility with `78729`

Walk through the same pipeline with `78729` and confirm nothing changed:
- All existing validation still passes
- Geocoding still appends `,US`
- Temperature stays Fahrenheit
- R2 paths unchanged

#### Task 4.4 — Security review

Verify against the Security Level DoD from CONTRIBUTING.md:

- [ ] **Input validation**: `is_valid_location()` is allowlist-based, rejects by default
- [ ] **Path traversal**: R2 key `MX77400/rgb_light.png` — no user-controlled path components beyond the validated identifier
- [ ] **Secrets**: No new secrets introduced; OWM API key handling unchanged
- [ ] **Error messages**: Updated error messages don't leak internals — they show format examples only
- [ ] **HTTPS**: OWM geocoding URL uses HTTP (pre-existing — not introduced by this change). Document as known debt.

**Pre-existing security note:** The OWM API calls in `kv_utils.py` (line 43) and
`openweathermap.py` (line 120) use `http://` not `https://`. This violates the
"Secure Communication" DoD item. Not in scope for this feature but should be filed
as a separate issue.

#### Phase 4 — Definition of Done

- [ ] `python run_test.py` passes
- [ ] Full pipeline trace verified for `MX77400`
- [ ] Full pipeline trace verified for `78729` (backward compat)
- [ ] Security DoD checklist completed
- [ ] Pre-existing HTTP issue documented

#### Phase 4 — QA Review Gate

Final 4-agent QA review on ALL changed files across all phases:
- `workers/web/src/web_utils.py`
- `workers/web/src/web.py`
- `workers/web/src/assets/templates/admin.html`
- `workers/fetcher/src/kv_utils.py`
- `workers/landscape/src/landscape_utils.py`
- `workers/landscape/src/landscape_generator.py`
- `test_local_generation.py`
- `secrets.py.example`

---

## Summary of All Changes

| # | File | Worker | Change Summary |
|---|------|--------|---------------|
| 1 | `workers/web/src/web_utils.py` | web | Add `is_valid_location()`, fix R2 scan validation (2 sites) |
| 2 | `workers/web/src/web.py` | web | Import validator, fix 7 validation sites (6 existing + 1 bug fix) |
| 3 | `workers/web/src/assets/templates/admin.html` | web | Client-side validation, labels, input attributes, JS normalization |
| 4 | `workers/fetcher/src/kv_utils.py` | fetcher | Parse CC prefix in `geocode_zip()`, construct international OWM URL |
| 5 | `workers/landscape/src/landscape_utils.py` | landscape | Add `location_id` param, Celsius override for international |
| 6 | `workers/landscape/src/landscape_generator.py` | landscape | Pass `zip_code` as `location_id` to config factory |
| 7 | `test_local_generation.py` | (local) | International geocoding + Celsius in local test script |
| 8 | `secrets.py.example` | (local) | Document international format in comments |

**Files unchanged:** scheduler worker, dispatcher worker, fetcher worker entry point,
all landscape rendering code, config classes, OpenWeatherMap API client, run_test.py.

---

## Known Limitations & Future Work

1. **Holidays** — US holiday sprites will appear on Cancun images. Future: per-location holiday configs.
2. **Geocoding precision** — Postal code 77400 covers the broader Cancun hotel zone, not the exact hotel. Adequate for weather (regional data).
3. **HTTP→HTTPS** — OWM API calls use HTTP (pre-existing). File as separate issue.
4. **Admin auth** — Admin endpoints have no authentication (pre-existing). Not in scope but noted.

---

## Post-Deploy Runbook

After `./deploy-all.sh` succeeds:

1. Navigate to `/admin`
2. Enter `MX77400` in the "Add New Location" input
3. Click "Add" — this activates + triggers initial generation
4. Wait ~2 minutes for pipeline to complete (fetch → dispatch → generate → upload)
5. Navigate to `/MX77400` — verify landscape image loads with Celsius temperatures
6. Navigate to `/78729` — verify US location still works with Fahrenheit
7. Wait for next cron cycle (15 min) — verify `MX77400` regenerates automatically
8. Check Cloudflare dashboard for any worker errors
