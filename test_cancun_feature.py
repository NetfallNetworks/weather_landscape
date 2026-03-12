#!/usr/bin/env python
"""
Tests for international location support (Cancun weather feature).
Validates location validation, geocoding URL construction, and temperature unit selection.
"""

import sys
import os

# Import from worker src directories
sys.path.insert(0, 'workers/web/src')
sys.path.insert(0, 'workers/landscape/src')

# ============================================================
# Phase 1: is_valid_location() tests
# ============================================================

# We can't import web_utils directly (depends on pyodide/js),
# so we replicate the function for testing
import re

def is_valid_location(loc_id):
    if not loc_id or not isinstance(loc_id, str):
        return False
    if re.match(r'^\d{5}$', loc_id):
        return True
    if re.match(r'^[A-Z]{2}\d{4,10}$', loc_id):
        return True
    return False


def test_is_valid_location():
    """Test all 10 validation cases from the plan"""
    print("Phase 1: Testing is_valid_location()...")

    assert is_valid_location('78729') == True, "US ZIP should be valid"
    assert is_valid_location('MX77400') == True, "International code should be valid"
    assert is_valid_location('mx77400') == False, "Lowercase should be rejected (server enforces uppercase)"
    assert is_valid_location('7872') == False, "4-digit ZIP should be rejected"
    assert is_valid_location('787299') == False, "6-digit ZIP should be rejected"
    assert is_valid_location('M77400') == False, "1-letter prefix should be rejected"
    assert is_valid_location('MXX7400') == False, "3-letter prefix should be rejected"
    assert is_valid_location('') == False, "Empty string should be rejected"
    assert is_valid_location(None) == False, "None should be rejected"
    assert is_valid_location('../../etc') == False, "Path traversal should be rejected"

    # Extra edge cases
    assert is_valid_location('BR01310100') == True, "Long postal code should be valid"
    assert is_valid_location('AB1234') == True, "Minimum 4-digit postal should be valid"
    assert is_valid_location('AB123') == False, "3-digit postal should be rejected"
    assert is_valid_location('AB12345678901') == False, "11-digit postal should be rejected (max 10)"

    print("  All 14 validation tests passed!")


# ============================================================
# Phase 2: Geocoding URL construction tests
# ============================================================

def parse_geo_param(zip_code):
    """Replicate the geocoding parsing logic from kv_utils.py"""
    if len(zip_code) > 2 and zip_code[:2].isalpha():
        country = zip_code[:2].upper()
        postal = zip_code[2:]
        return f"{postal},{country}"
    else:
        return f"{zip_code},US"


def test_geocoding_url_construction():
    """Test URL parameter construction for geocoding"""
    print("Phase 2: Testing geocoding URL construction...")

    assert parse_geo_param('MX77400') == '77400,MX', "MX77400 should produce 77400,MX"
    assert parse_geo_param('78729') == '78729,US', "US ZIP should produce 78729,US"
    assert parse_geo_param('BR01310100') == '01310100,BR', "Brazilian code should produce 01310100,BR"
    assert parse_geo_param('GB12345') == '12345,GB', "UK code should produce 12345,GB"

    print("  All 4 geocoding tests passed!")


# ============================================================
# Phase 3: Temperature unit selection tests
# ============================================================

def test_temperature_units():
    """Test that international locations get Celsius"""
    print("Phase 3: Testing temperature unit selection...")

    from p_weather.configuration import WLBaseSettings
    from landscape_utils import WorkerConfig

    class FakeEnv:
        OWM_API_KEY = "test_key"

    config = WorkerConfig(FakeEnv())

    # US location should get Fahrenheit
    us_config = config.to_weather_config(lat=30.0, lon=-97.0, format_name='rgb_light', location_id='78729')
    assert us_config.TEMPUNITS_MODE == WLBaseSettings.TEMP_UNITS_FAHRENHEIT, \
        f"US location should use Fahrenheit, got {us_config.TEMPUNITS_MODE}"

    # International location should get Celsius
    mx_config = config.to_weather_config(lat=21.26, lon=-86.81, format_name='rgb_light', location_id='MX77400')
    assert mx_config.TEMPUNITS_MODE == WLBaseSettings.TEMP_UNITS_CELSIUS, \
        f"International location should use Celsius, got {mx_config.TEMPUNITS_MODE}"

    # None location_id should default to Fahrenheit (backward compat)
    none_config = config.to_weather_config(lat=30.0, lon=-97.0, format_name='rgb_light', location_id=None)
    assert none_config.TEMPUNITS_MODE == WLBaseSettings.TEMP_UNITS_FAHRENHEIT, \
        f"None location_id should default to Fahrenheit, got {none_config.TEMPUNITS_MODE}"

    # No location_id arg should default to Fahrenheit (backward compat)
    default_config = config.to_weather_config(lat=30.0, lon=-97.0, format_name='rgb_light')
    assert default_config.TEMPUNITS_MODE == WLBaseSettings.TEMP_UNITS_FAHRENHEIT, \
        f"Missing location_id should default to Fahrenheit, got {default_config.TEMPUNITS_MODE}"

    print("  All 4 temperature unit tests passed!")


# ============================================================
# Phase 4: Verify source files contain expected patterns
# ============================================================

def test_source_files_updated():
    """Verify that source files contain the expected updated patterns"""
    print("Phase 4: Verifying source file updates...")

    # Check web_utils.py has is_valid_location
    with open('workers/web/src/web_utils.py', 'r') as f:
        web_utils_src = f.read()
    assert 'def is_valid_location(' in web_utils_src, "web_utils.py should define is_valid_location"
    assert 'import re' in web_utils_src, "web_utils.py should import re"
    # Should NOT have old 5-digit-only validation in R2 scanning
    assert 'zip_code.isdigit() and len(zip_code) == 5' not in web_utils_src, \
        "web_utils.py should not have old 5-digit validation"

    # Check web.py imports is_valid_location
    with open('workers/web/src/web.py', 'r') as f:
        web_src = f.read()
    assert 'is_valid_location' in web_src, "web.py should import is_valid_location"
    assert 'zip_code.isdigit()' not in web_src, "web.py should not have old validation"
    assert 'part.isdigit()' not in web_src, "web.py URL routing should use is_valid_location"

    # Check kv_utils.py has international geocoding
    with open('workers/fetcher/src/kv_utils.py', 'r') as f:
        kv_src = f.read()
    assert 'zip_code[:2].isalpha()' in kv_src, "kv_utils.py should detect CC prefix"
    assert 'geo_param' in kv_src, "kv_utils.py should use geo_param variable"
    assert '{postal},{country}' in kv_src, "kv_utils.py should construct international geo_param"

    # Check landscape_utils.py has location_id parameter
    with open('workers/landscape/src/landscape_utils.py', 'r') as f:
        landscape_src = f.read()
    assert 'location_id=None' in landscape_src, "landscape_utils.py should accept location_id"
    assert 'TEMP_UNITS_CELSIUS' in landscape_src, "landscape_utils.py should reference Celsius"

    # Check landscape_generator.py passes location_id
    with open('workers/landscape/src/landscape_generator.py', 'r') as f:
        gen_src = f.read()
    assert 'location_id=zip_code' in gen_src, "landscape_generator.py should pass location_id"

    # Check admin.html updated
    with open('workers/web/src/assets/templates/admin.html', 'r') as f:
        admin_src = f.read()
    assert 'Add New Location' in admin_src, "admin.html should say 'Add New Location'"
    assert 'MX77400' in admin_src, "admin.html should mention MX77400"
    assert 'toUpperCase()' in admin_src, "admin.html should normalize to uppercase"

    print("  All source file verification checks passed!")


if __name__ == '__main__':
    test_is_valid_location()
    test_geocoding_url_construction()
    test_temperature_units()
    test_source_files_updated()
    print()
    print("All tests passed!")
