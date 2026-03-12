# Add Cancun Weather Landscape Support

## Context
The system generates 296x128px weather landscape images for US ZIP codes, deployed as 5 Cloudflare Workers. The user wants to add Cancun, Mexico (Hotel Riu Dunamar, postal code 77400, ~21.26°N, -86.81°W) as a supported location. The entire system is hardcoded for 5-digit US ZIP codes — geocoding appends `,US`, validation enforces `isdigit() and len() == 5`, and temperature is always Fahrenheit. OpenWeatherMap already supports international postal codes (`zip=77400,MX`) and lat/lon weather endpoints work globally, so only the identifier/validation layer needs changing.

## Approach: `CC#####` Prefix Format (e.g. `MX77400`)

Keep the existing `zip_code` variable/field names throughout (renaming to `location_id` everywhere would be a massive refactor with no functional benefit). Allow identifiers to be either:
- `78729` — US ZIP (backward compatible, geocodes as `78729,US`)
- `MX77400` — International: 2-letter ISO country prefix + postal code (geocodes as `77400,MX`)

Detection is simple: starts with a letter → international, starts with a digit → US ZIP. Parsing: `code[:2]` = country, `code[2:]` = postal. No special characters, no delimiter ambiguity.

Flows cleanly through: KV keys (`geo:MX77400`), R2 paths (`MX77400/rgb_light.png`), URLs (`/MX77400`), queue messages.

## Deployment & Testing Notes
- **Cloudflare deployment**: Stays as-is via `deploy-all.sh` + wrangler CLI (git-based deployment is 1:1 repo-to-worker, doesn't scale for 5 workers)
- **Local testing**: No OWM API key available — verify code logic only, no live API calls
- **No formal test framework** — verification via local test scripts and code review

---

## File Changes (8 files)

### 1. `workers/web/src/web_utils.py` — Add shared validator + fix R2 scanning

Add `is_valid_location(loc_id)` near top of file:
```python
import re

def is_valid_location(loc_id):
    """Validate location identifier: US ZIP (5 digits) or international (CC + postal digits)"""
    if not loc_id or not isinstance(loc_id, str):
        return False
    # US ZIP: exactly 5 digits
    if re.match(r'^\d{5}$', loc_id):
        return True
    # International: 2 uppercase letters + 4-10 digits (e.g. MX77400)
    if re.match(r'^[A-Z]{2}\d{4,10}$', loc_id):
        return True
    return False
```

Replace validation at **line 223** in `get_all_zips_from_r2()`:
- `zip_code.isdigit() and len(zip_code) == 5` → `is_valid_location(zip_code)`

Replace validation at **line 253** in `get_formats_per_zip()`:
- `zip_code.isdigit() and len(zip_code) == 5` → `is_valid_location(zip_code)`

### 2. `workers/web/src/web.py` — Fix 6 validation sites

Add import at top: `from web_utils import is_valid_location`

**Line 82** (URL route matching):
- `part.isdigit() and len(part) == 5` → `is_valid_location(part)`

**Lines 515, 574, 610, 644, 681** (admin endpoints — activate, format add/remove/get, generate):
- Each `zip_code.isdigit() and len(zip_code) == 5` → `is_valid_location(zip_code)`
- Update error messages from "Must be 5 digits" to "Must be a US ZIP (78729) or international code (MX77400)"

### 3. `workers/web/src/assets/templates/admin.html` — Client-side updates

**Line 36**: Heading `"Add New ZIP Code"` → `"Add New Location"`
**Line 38-39**: Input attributes:
- `maxlength="5" pattern="[0-9]{5}"` → `maxlength="12" pattern="(\d{5}|[A-Z]{2}\d{4,10})"`
- `placeholder="12345"` → `placeholder="78729 or MX77400"`
**Line 40**: Button `"Add ZIP"` → `"Add"`
**Line 48**: Table header `"ZIP Code"` → `"Location"`
**Line 148**: JS validation regex:
- `/^\d{5}$$/.test(zip)` → `/^(\d{5}|[A-Z]{2}\d{4,10})$/.test(zip.toUpperCase())`
- Error message: `"Please enter a US ZIP (78729) or international code (MX77400)"`
**Line 185**: Reset button text `"Add ZIP"` → `"Add"`

### 4. `workers/fetcher/src/kv_utils.py` — International geocoding

**Line 43** in `geocode_zip()` — parse country code from prefix:
```python
# Parse location identifier for geocoding
if len(zip_code) > 2 and zip_code[:2].isalpha():
    # International format: CC + postal (e.g. MX77400 → 77400,MX)
    country = zip_code[:2].upper()
    postal = zip_code[2:]
    geo_param = f"{postal},{country}"
else:
    # US ZIP code (e.g. 78729 → 78729,US)
    geo_param = f"{zip_code},US"

url = f"http://api.openweathermap.org/geo/1.0/zip?zip={geo_param}&appid={api_key}"
```

### 5. `workers/landscape/src/landscape_utils.py` — Celsius for international locations

**Line 57** — add `location_id` parameter to `to_weather_config()`:
```python
def to_weather_config(self, lat, lon, format_name=None, location_id=None):
```

After `config = config_class()` (line 80), before setting lat/lon, add:
```python
# International locations use Celsius
if location_id and len(location_id) > 2 and location_id[:2].isalpha():
    from p_weather.configuration import WLBaseSettings
    config.TEMPUNITS_MODE = WLBaseSettings.TEMP_UNITS_CELSIUS
```

### 6. `workers/landscape/src/landscape_generator.py` — Pass location_id through

**Line 118** — pass `location_id`:
```python
weather_config = config.to_weather_config(lat=lat, lon=lon, format_name=format_name, location_id=zip_code)
```

### 7. `test_local_generation.py` — Local test support for international

**Line 28** — update `geocode_zip()` to parse prefix format:
```python
async def geocode_zip(zip_code, api_key):
    if len(zip_code) > 2 and zip_code[:2].isalpha():
        country = zip_code[:2].upper()
        postal = zip_code[2:]
        geo_param = f"{postal},{country}"
    else:
        geo_param = f"{zip_code},US"
    url = f"http://api.openweathermap.org/geo/1.0/zip?zip={geo_param}&appid={api_key}"
    ...
```

After config creation (~line 69), add Celsius override:
```python
if len(zip_code) > 2 and zip_code[:2].isalpha():
    from p_weather.configuration import WLBaseSettings
    config.TEMPUNITS_MODE = WLBaseSettings.TEMP_UNITS_CELSIUS
```

### 8. `secrets.py.example` — Document international format

Update comments:
```python
# Location identifier
# US ZIP codes: "78729" (Austin, TX)
# International: "MX77400" (Cancun, Mexico) — 2-letter country code prefix + postal code
ZIP_CODE = "78729"
```

---

## Files That Need NO Changes (data flows through as-is)
- `workers/scheduler/src/zip_scheduler.py` — reads active_zips list, enqueues; no validation
- `workers/scheduler/src/scheduler_utils.py` — returns list from KV; no format check
- `workers/fetcher/src/weather_fetcher.py` — passes zip_code string through; no validation
- `workers/fetcher/src/config.py` — default ZIP stays 78729
- `workers/dispatcher/src/dispatcher.py` — forwards zip_code; no validation
- `workers/landscape/src/configs.py` — config classes unchanged (temp override in landscape_utils)
- `workers/landscape/src/weather_landscape.py` — receives config, generates image; identifier-agnostic
- `workers/landscape/src/p_weather/openweathermap.py` — uses lat/lon only
- `workers/landscape/src/p_weather/configuration.py` — base settings unchanged
- `run_test.py` — uses config classes directly, no location identifier

---

## Verification

1. **Code review**: Confirm all 6+2 validation sites in web.py/web_utils.py accept both `78729` and `MX77400`
2. **Geocoding logic**: Trace that `MX77400` produces OWM URL `zip=77400,MX` and `78729` produces `zip=78729,US`
3. **Temperature units**: Trace that `MX77400` sets `TEMP_UNITS_CELSIUS` while `78729` keeps `TEMP_UNITS_FAHRENHEIT`
4. **Import check**: Run `python -c "import sys; sys.path.insert(0, 'workers/landscape/src'); from configs import *; print('OK')"` to verify no import errors
5. **Post-deploy** (manual, after wrangler deploy):
   - Add `MX77400` via admin UI at `/admin`
   - Verify image generates and serves at `/MX77400`
   - Verify existing US ZIPs still work at `/78729`
   - Wait for cron cycle, confirm `MX77400` regenerates automatically

## Known Limitations
- **Holidays**: The holiday system contains US holidays; Cancun images will show US holiday decorations. Can be addressed later with per-location holiday configs.
- **Geocoding precision**: Postal code 77400 covers the broader Cancun hotel zone. The OWM-returned coordinates will be close to Hotel Riu Dunamar but not exact. Good enough for weather data (which is regional anyway).
