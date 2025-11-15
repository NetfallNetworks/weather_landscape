"""
Cloudflare Worker for Weather Landscape Image Generation
Generates weather visualizations and serves them from R2 storage
Supports multiple ZIP codes with geocoding and KV caching
"""

from js import Response, Headers, fetch, Object
from workers import WorkerEntrypoint
from pyodide.ffi import to_js as _to_js
import json
from datetime import datetime


def to_js(obj):
    """Convert Python dict to JavaScript object for Response headers"""
    return _to_js(obj, dict_converter=Object.fromEntries)


# Format configuration mapping
FORMAT_CONFIGS = {
    'rgb_light': {
        'class_name': 'WLConfig_RGB_White',
        'extension': '.png',
        'mime_type': 'image/png',
        'title': 'RGB Light Theme'
    },
    'rgb_dark': {
        'class_name': 'WLConfig_RGB_Black',
        'extension': '.png',
        'mime_type': 'image/png',
        'title': 'RGB Dark Theme'
    },
    'bw': {
        'class_name': 'WLConfig_BW',
        'extension': '.bmp',
        'mime_type': 'image/bmp',
        'title': 'Black & White'
    },
    'eink': {
        'class_name': 'WLConfig_EINK',
        'extension': '.bmp',
        'mime_type': 'image/bmp',
        'title': 'E-Ink (Flipped)'
    },
    'bwi': {
        'class_name': 'WLConfig_BWI',
        'extension': '.bmp',
        'mime_type': 'image/bmp',
        'title': 'Black & White Inverted'
    }
}

# Default format (always generated)
DEFAULT_FORMAT = 'rgb_light'


def get_enabled_formats(env):
    """
    DEPRECATED: Use get_formats_for_zip() instead
    Get list of formats from environment variable (global, not per-ZIP)
    """
    # Always include the default format
    formats = [DEFAULT_FORMAT]

    # Check for additional formats in environment variable
    try:
        additional = getattr(env, 'ADDITIONAL_FORMATS', '')
        if additional:
            for fmt in additional.split(','):
                fmt = fmt.strip().lower()
                if fmt and fmt in FORMAT_CONFIGS and fmt not in formats:
                    formats.append(fmt)
    except:
        pass

    return formats


async def get_formats_for_zip(env, zip_code):
    """
    Get list of formats to generate for a specific ZIP code from KV

    Args:
        env: Worker environment
        zip_code: ZIP code

    Returns:
        list: Format names (always includes DEFAULT_FORMAT)
    """
    try:
        kv_key = f"formats:{zip_code}"
        formats_json = await env.CONFIG.get(kv_key)
        if formats_json:
            formats = json.loads(formats_json)
            # Ensure default format is always included
            if DEFAULT_FORMAT not in formats:
                formats.insert(0, DEFAULT_FORMAT)
            return formats
        else:
            # No config for this ZIP, use default only
            return [DEFAULT_FORMAT]
    except Exception as e:
        print(f"Warning: Failed to get formats for {zip_code}: {e}")
        return [DEFAULT_FORMAT]


async def add_format_to_zip(env, zip_code, format_name):
    """
    Add a format to be generated for a specific ZIP code

    Args:
        env: Worker environment
        zip_code: ZIP code
        format_name: Format to add (e.g., 'rgb_dark', 'bw')

    Returns:
        list: Updated list of formats for this ZIP
    """
    if format_name not in FORMAT_CONFIGS:
        raise ValueError(f"Unknown format: {format_name}")

    formats = await get_formats_for_zip(env, zip_code)
    if format_name not in formats:
        formats.append(format_name)
        kv_key = f"formats:{zip_code}"
        await env.CONFIG.put(kv_key, json.dumps(formats))
        print(f"✅ Added format {format_name} to {zip_code}")
    return formats


async def remove_format_from_zip(env, zip_code, format_name):
    """
    Remove a format from being generated for a specific ZIP code

    Args:
        env: Worker environment
        zip_code: ZIP code
        format_name: Format to remove

    Returns:
        list: Updated list of formats for this ZIP
    """
    if format_name == DEFAULT_FORMAT:
        raise ValueError(f"Cannot remove default format {DEFAULT_FORMAT}")

    formats = await get_formats_for_zip(env, zip_code)
    if format_name in formats:
        formats.remove(format_name)
        kv_key = f"formats:{zip_code}"
        await env.CONFIG.put(kv_key, json.dumps(formats))
        print(f"✅ Removed format {format_name} from {zip_code}")
    return formats


class WorkerConfig:
    """Configuration loaded from KV and environment"""
    def __init__(self, env):
        # Access environment variables directly from env object
        # Secrets (like OWM_API_KEY) are set via: wrangler secret put OWM_API_KEY
        # Vars (like DEFAULT_ZIP) are set in wrangler.toml [vars] section
        try:
            self.OWM_KEY = getattr(env, 'OWM_API_KEY', None)
        except Exception as e:
            self.OWM_KEY = None

        try:
            self.ZIP_CODE = str(getattr(env, 'DEFAULT_ZIP', '78729'))
        except:
            self.ZIP_CODE = '78729'

        self.WORK_DIR = "/tmp"

    def to_weather_config(self, lat, lon, format_name=None):
        """
        Convert to WeatherLandscape config format

        Args:
            lat: Latitude (required)
            lon: Longitude (required)
            format_name: Format name (e.g., 'rgb_white', 'bw', 'eink')
        """
        # Import at runtime to allow Pillow to load first
        import configs

        # Default to RGB_White if no format specified
        if format_name is None:
            format_name = DEFAULT_FORMAT

        # Get config class for this format
        format_info = FORMAT_CONFIGS.get(format_name)
        if not format_info:
            raise ValueError(f"Unknown format: {format_name}")

        # Get the config class dynamically
        config_class = getattr(configs, format_info['class_name'])
        config = config_class()

        config.OWM_KEY = self.OWM_KEY
        config.OWM_LAT = lat
        config.OWM_LON = lon
        config.WORK_DIR = self.WORK_DIR
        return config


async def geocode_zip(env, zip_code, api_key):
    """
    Geocode a ZIP code to lat/lon coordinates with KV caching

    Args:
        env: Worker environment (for KV access)
        zip_code: US ZIP code as string
        api_key: OpenWeatherMap API key

    Returns:
        dict: {'lat': float, 'lon': float, 'zip': str, 'cached_at': str}

    Raises:
        ValueError: If geocoding fails
    """
    kv_key = f"geo:{zip_code}"

    # Check KV cache first
    try:
        cached = await env.CONFIG.get(kv_key)
        if cached:
            geo_data = json.loads(cached)
            print(f"📍 Using cached geocoding for {zip_code}: {geo_data['lat']}, {geo_data['lon']}")
            return geo_data
    except Exception as e:
        print(f"Warning: Failed to read geocoding cache for {zip_code}: {e}")

    # Not in cache, call OWM Geocoding API
    print(f"🌐 Geocoding ZIP {zip_code} via OWM API...")
    try:
        url = f"http://api.openweathermap.org/geo/1.0/zip?zip={zip_code},US&appid={api_key}"
        response = await fetch(url)

        if response.status != 200:
            raise ValueError(f"Geocoding API returned status {response.status}")

        data = await response.json()

        # Extract lat/lon from response
        geo_data = {
            'lat': float(data.lat),
            'lon': float(data.lon),
            'zip': zip_code,
            'cached_at': datetime.utcnow().isoformat() + 'Z'
        }

        # Store in KV cache (cache forever)
        try:
            await env.CONFIG.put(kv_key, json.dumps(geo_data))
            print(f"✅ Cached geocoding for {zip_code}: {geo_data['lat']}, {geo_data['lon']}")
        except Exception as e:
            print(f"Warning: Failed to cache geocoding for {zip_code}: {e}")

        return geo_data

    except Exception as e:
        raise ValueError(f"Failed to geocode ZIP {zip_code}: {e}")


async def get_active_zips(env):
    """
    Get list of active ZIP codes from KV

    Returns:
        list: List of ZIP code strings
    """
    try:
        active_zips_json = await env.CONFIG.get('active_zips')
        if active_zips_json:
            return json.loads(active_zips_json)
        else:
            # Initialize with default ZIP if not set
            default_zips = ['78729']
            await env.CONFIG.put('active_zips', json.dumps(default_zips))
            print(f"📝 Initialized active_zips with default: {default_zips}")
            return default_zips
    except Exception as e:
        print(f"Warning: Failed to get active_zips from KV: {e}")
        return ['78729']  # Fallback to default


async def get_all_zips_from_r2(env):
    """
    Scan R2 bucket to find all ZIP codes that have images

    Returns:
        list: List of ZIP code strings found in R2
    """
    try:
        zip_codes = set()

        # List all objects in the R2 bucket
        # R2 list() returns objects with keys like "78729/rgb_light.png"
        listed = await env.WEATHER_IMAGES.list()

        # Extract ZIP codes from object keys
        if hasattr(listed, 'objects'):
            for obj in listed.objects:
                # Object key format: "78729/rgb_light.png"
                key = obj.key
                if '/' in key:
                    zip_code = key.split('/')[0]
                    # Validate it looks like a ZIP code (5 digits)
                    if zip_code.isdigit() and len(zip_code) == 5:
                        zip_codes.add(zip_code)

        return sorted(list(zip_codes))
    except Exception as e:
        print(f"Warning: Failed to list R2 objects: {e}")
        return []


async def get_formats_per_zip(env):
    """
    Scan R2 bucket to find which formats are available for each ZIP

    Returns:
        dict: {zip_code: [format_names]}
    """
    try:
        zip_formats = {}

        # List all objects in the R2 bucket
        listed = await env.WEATHER_IMAGES.list()

        # Extract ZIP codes and formats from object keys
        if hasattr(listed, 'objects'):
            for obj in listed.objects:
                # Object key format: "78729/rgb_light.png" or "78729/bw.bmp"
                key = obj.key
                if '/' in key:
                    parts = key.split('/')
                    zip_code = parts[0]
                    if zip_code.isdigit() and len(zip_code) == 5 and len(parts) > 1:
                        # Extract format from filename (remove extension)
                        filename = parts[1]
                        format_name = filename.rsplit('.', 1)[0] if '.' in filename else filename

                        # Check if it's a valid format
                        if format_name in FORMAT_CONFIGS:
                            if zip_code not in zip_formats:
                                zip_formats[zip_code] = []
                            if format_name not in zip_formats[zip_code]:
                                zip_formats[zip_code].append(format_name)

        # Sort formats for each ZIP (default first, then alphabetical)
        for zip_code in zip_formats:
            formats = zip_formats[zip_code]
            # Sort with default format first
            sorted_formats = []
            if DEFAULT_FORMAT in formats:
                sorted_formats.append(DEFAULT_FORMAT)
            for fmt in sorted(formats):
                if fmt != DEFAULT_FORMAT:
                    sorted_formats.append(fmt)
            zip_formats[zip_code] = sorted_formats

        return zip_formats
    except Exception as e:
        print(f"Warning: Failed to get formats per zip: {e}")
        return {}


async def add_zip_to_active(env, zip_code):
    """
    Add a ZIP code to the active_zips list

    Args:
        env: Worker environment
        zip_code: ZIP code to add

    Returns:
        list: Updated list of active ZIP codes
    """
    try:
        active_zips = await get_active_zips(env)
        if zip_code not in active_zips:
            active_zips.append(zip_code)
            await env.CONFIG.put('active_zips', json.dumps(active_zips))
            print(f"✅ Added {zip_code} to active_zips")
        return active_zips
    except Exception as e:
        print(f"Error adding {zip_code} to active_zips: {e}")
        raise


async def generate_weather_image(env, zip_code, lat, lon, format_name=None):
    """
    Generate a weather landscape image using current weather data

    Args:
        env: Worker environment
        zip_code: ZIP code for this generation
        lat: Latitude for weather lookup
        lon: Longitude for weather lookup
        format_name: Format to generate (e.g., 'rgb_white', 'bw', 'eink')

    Returns:
        tuple: (image_bytes, metadata_dict, format_name)
    """
    try:
        # Import at runtime (Pillow loaded from cf-requirements.txt)
        from weather_landscape import WeatherLandscape
        from asset_loader import set_global_loader
        import io

        # Initialize the global asset loader
        set_global_loader()

        # Load configuration from environment
        config = WorkerConfig(env)

        # Check for API key
        if not config.OWM_KEY:
            raise ValueError("OWM_API_KEY not set in environment")

        # Default to DEFAULT_FORMAT if not specified
        if format_name is None:
            format_name = DEFAULT_FORMAT

        # Get format info
        format_info = FORMAT_CONFIGS.get(format_name)
        if not format_info:
            raise ValueError(f"Unknown format: {format_name}")

        # Generate the image with provided lat/lon and format
        wl = WeatherLandscape(config.to_weather_config(lat=lat, lon=lon, format_name=format_name))
        img = await wl.MakeImage()

        # Convert PIL Image to bytes
        buffer = io.BytesIO()
        # Determine save format based on extension
        save_format = 'PNG' if format_info['extension'] == '.png' else 'BMP'
        img.save(buffer, format=save_format)
        image_bytes = buffer.getvalue()

        # Create metadata
        metadata = {
            'generatedAt': datetime.utcnow().isoformat() + 'Z',
            'latitude': lat,
            'longitude': lon,
            'zipCode': zip_code,
            'fileSize': len(image_bytes),
            'format': save_format,
            'variant': format_name
        }

        return image_bytes, metadata, format_name

    except Exception as e:
        print(f"Error generating {format_name} image for {zip_code}: {e}")
        raise


async def upload_to_r2(env, image_bytes, metadata, zip_code, format_name=None):
    """
    Upload generated image to R2 bucket

    Args:
        env: Worker environment
        image_bytes: Image bytes (PNG or BMP)
        metadata: Image metadata dict
        zip_code: ZIP code for folder organization
        format_name: Format name (e.g., 'rgb_white', 'bw')

    Returns:
        bool: True if successful
    """
    try:
        # Default to DEFAULT_FORMAT if not specified
        if format_name is None:
            format_name = DEFAULT_FORMAT

        # Get format info
        format_info = FORMAT_CONFIGS.get(format_name)
        if not format_info:
            raise ValueError(f"Unknown format: {format_name}")

        # Store ONE file per format: {zip}/{format}{ext}
        extension = format_info['extension']
        key = f"{zip_code}/{format_name}{extension}"

        # Prepare R2 metadata
        custom_metadata = {
            'generated-at': metadata['generatedAt'],
            'latitude': str(metadata['latitude']),
            'longitude': str(metadata['longitude']),
            'zip-code': zip_code,
            'file-size': str(metadata['fileSize']),
            'variant': format_name
        }

        # Convert Python bytes to JavaScript Uint8Array for R2
        from js import Uint8Array
        js_array = Uint8Array.new(len(image_bytes))
        for i, byte in enumerate(image_bytes):
            js_array[i] = byte

        # Upload to R2
        await env.WEATHER_IMAGES.put(
            key,
            js_array,
            {
                'httpMetadata': {
                    'contentType': format_info['mime_type'],
                },
                'customMetadata': custom_metadata
            }
        )

        print(f"✅ Uploaded {key} to R2 ({len(image_bytes)} bytes)")

        # Save metadata to KV (per-ZIP-format)
        await env.CONFIG.put(
            f'metadata:{zip_code}:{format_name}',
            json.dumps(metadata)
        )

        return True

    except Exception as e:
        print(f"Error uploading {zip_code}/{format_name} to R2: {e}")
        raise


class Default(WorkerEntrypoint):
    """
    Main Worker Entrypoint for Weather Landscape
    Handles both scheduled (cron) and fetch (HTTP) requests
    """

    async def scheduled(self, event, env, ctx):
        """
        Scheduled handler - runs on cron trigger (every 15 minutes)
        Generates weather landscape images for all active ZIP codes
        """
        print(f"🕐 Scheduled run started at {datetime.utcnow().isoformat()}")

        # Get configuration
        config = WorkerConfig(self.env)
        if not config.OWM_KEY:
            print("❌ OWM_API_KEY not set")
            return

        # Get active ZIP codes
        active_zips = await get_active_zips(self.env)
        print(f"📋 Processing {len(active_zips)} ZIP code(s): {', '.join(active_zips)}")

        success_count = 0
        error_count = 0
        errors = []

        # Process each ZIP code
        for zip_code in active_zips:
            try:
                print(f"\n🔄 Processing ZIP {zip_code}...")

                # Get formats configured for this ZIP from KV
                enabled_formats = await get_formats_for_zip(self.env, zip_code)
                print(f"🎨 Generating {len(enabled_formats)} format(s) for {zip_code}: {', '.join(enabled_formats)}")

                # Geocode the ZIP (uses cache if available)
                geo_data = await geocode_zip(self.env, zip_code, config.OWM_KEY)

                # Generate images for all enabled formats
                zip_success = True
                for format_name in enabled_formats:
                    try:
                        print(f"🎨 Generating {format_name} for {zip_code}...")
                        image_bytes, metadata, _ = await generate_weather_image(
                            self.env,
                            zip_code,
                            geo_data['lat'],
                            geo_data['lon'],
                            format_name
                        )

                        # Upload to R2
                        print(f"☁️  Uploading {format_name} for {zip_code} to R2...")
                        await upload_to_r2(self.env, image_bytes, metadata, zip_code, format_name)

                        print(f"✅ Completed {format_name} for {zip_code}")

                    except Exception as e:
                        zip_success = False
                        error_msg = f"ZIP {zip_code} ({format_name}): {str(e)}"
                        errors.append(error_msg)
                        print(f"❌ Failed {format_name} for {zip_code}: {e}")

                # Count as success if at least one format succeeded
                if zip_success:
                    success_count += 1
                else:
                    error_count += 1

            except Exception as e:
                error_count += 1
                error_msg = f"ZIP {zip_code}: {str(e)}"
                errors.append(error_msg)
                print(f"❌ Failed {zip_code}: {e}")

        # Update overall status in KV
        try:
            status = {
                'lastRun': datetime.utcnow().isoformat() + 'Z',
                'totalZips': len(active_zips),
                'successCount': success_count,
                'errorCount': error_count,
                'errors': errors if errors else None
            }
            await self.env.CONFIG.put('status', json.dumps(status))
        except Exception as e:
            print(f"Warning: Failed to update status in KV: {e}")

        print(f"\n✅ Scheduled run completed: {success_count} success, {error_count} errors")

    async def on_fetch(self, request, env, ctx):
        """
        HTTP request handler - serves images from R2

        Routes:
        - GET / - Returns HTML info page with links to all ZIPs in R2
        - GET /{zip} - Returns latest weather image for ZIP (default format)
        - GET /{zip}?{format} - Returns image in specified format
        - GET /status - Returns generation status and metadata for all ZIPs
        - GET /formats?zip={zip} - Get configured formats for a ZIP
        - POST /activate?zip={zip} - Add ZIP to active regeneration list
        - POST /deactivate?zip={zip} - Remove ZIP from active regeneration list
        - POST /formats/add?zip={zip}&format={format} - Add format to a ZIP
        - POST /formats/remove?zip={zip}&format={format} - Remove format from a ZIP
        - POST /generate?zip={zip} - Manually trigger generation for a ZIP
        """
        url = request.url
        method = request.method
        path_parts = url.split('?')[0].split('/')
        path = path_parts[-1] if len(path_parts) > 0 else ''

        # Extract query parameters
        query_params = {}
        if '?' in url:
            query_string = url.split('?')[1]
            for param in query_string.split('&'):
                if '=' in param:
                    key, value = param.split('=', 1)
                    query_params[key] = value

        # Extract ZIP from path - matches /78729, /78729/, /78729/anything
        # Path parts: ['', '78729', 'latest.png'] or ['', '78729', ''] etc.
        zip_from_path = None
        for part in path_parts:
            # Check if this part looks like a 5-digit ZIP code
            if part and part.isdigit() and len(part) == 5:
                zip_from_path = part
                break

        # Route: Info page (root) - only if no ZIP in path
        if path == '' and not zip_from_path:
            try:
                # Get all ZIPs from R2 and active ZIPs from KV
                all_zips = await get_all_zips_from_r2(self.env)
                active_zips = await get_active_zips(self.env)
                zip_formats = await get_formats_per_zip(self.env)

                # Build ZIP links with active/inactive status dots and format links
                zip_items = []
                for zip_code in all_zips:
                    is_active = zip_code in active_zips
                    dot_class = 'dot active' if is_active else 'dot inactive'

                    # Build format links for this ZIP
                    formats = zip_formats.get(zip_code, [])
                    if formats:
                        format_links = []
                        for fmt in formats:
                            # Get friendly title for this format
                            fmt_title = FORMAT_CONFIGS.get(fmt, {}).get('title', fmt)
                            # Default format gets no query param, others use ?format
                            if fmt == DEFAULT_FORMAT:
                                format_links.append(f'<a href="/{zip_code}" class="format-link">{fmt_title}</a>')
                            else:
                                format_links.append(f'<a href="/{zip_code}?{fmt}" class="format-link">{fmt_title}</a>')
                        formats_html = '<span class="formats">' + ' '.join(format_links) + '</span>'
                    else:
                        formats_html = '<span class="formats"><em>no formats</em></span>'

                    zip_items.append(
                        f'<li><span class="{dot_class}"></span><span class="zip-label">ZIP {zip_code}</span>{formats_html}</li>'
                    )

                zip_links = '\n'.join(zip_items) if zip_items else '<li><em>No ZIP codes found in R2</em></li>'

                html = f"""
                <!DOCTYPE html>
                <html>
                <head>
                    <title>Weather Landscape</title>
                    <style>
                        body {{
                            font-family: system-ui, -apple-system, sans-serif;
                            max-width: 800px;
                            margin: 2rem auto;
                            padding: 2rem;
                            background: #f5f5f5;
                        }}
                        h1 {{ color: #333; }}
                        h2 {{ color: #555; margin-top: 2rem; }}
                        ul {{ list-style: none; padding: 0; }}
                        li {{
                            margin: 0.75rem 0;
                            display: flex;
                            align-items: center;
                            gap: 0.75rem;
                            flex-wrap: wrap;
                        }}
                        .zip-label {{
                            font-weight: 600;
                            min-width: 90px;
                        }}
                        .formats {{
                            display: flex;
                            gap: 0.5rem;
                            flex-wrap: wrap;
                        }}
                        .format-link {{
                            color: #0066cc;
                            text-decoration: none;
                            padding: 0.25rem 0.5rem;
                            background: white;
                            border-radius: 3px;
                            font-size: 0.85rem;
                            border: 1px solid #ddd;
                        }}
                        .format-link:hover {{
                            background: #e6f2ff;
                            border-color: #0066cc;
                        }}
                        .dot {{
                            width: 8px;
                            height: 8px;
                            border-radius: 50%;
                            flex-shrink: 0;
                        }}
                        .dot.active {{
                            background: #22c55e;
                        }}
                        .dot.inactive {{
                            background: #e5e7eb;
                        }}
                        .key {{
                            margin-top: 2rem;
                            padding-top: 1rem;
                            border-top: 1px solid #ddd;
                            font-size: 0.85rem;
                            color: #666;
                            display: flex;
                            gap: 1.5rem;
                        }}
                        .key-item {{
                            display: flex;
                            align-items: center;
                            gap: 0.5rem;
                        }}
                    </style>
                </head>
                <body>
                    <h1>🌤️ Weather Landscape</h1>
                    <h2>Available ZIP Codes ({len(all_zips)})</h2>
                    <ul>{zip_links}</ul>
                    <div class="key">
                        <div class="key-item">
                            <span class="dot active"></span>
                            <span>Up to date</span>
                        </div>
                        <div class="key-item">
                            <span class="dot inactive"></span>
                            <span>Not updating</span>
                        </div>
                    </div>
                </body>
                </html>
                """
                return Response.new(html, headers=to_js({"content-type": "text/html;charset=UTF-8"}))
            except Exception as e:
                return Response.new(
                    json.dumps({'error': f'Failed to load page: {str(e)}'}),
                    {
                        'status': 500,
                        'headers': {'Content-Type': 'application/json'}
                    }
                )

        # Route: Serve latest image - any path with a ZIP code (except status)
        elif zip_from_path and path != 'status':
            try:
                zip_code = zip_from_path
                requested_format = DEFAULT_FORMAT

                # Check query parameters for format name (e.g., ?bw, ?eink, ?rgb_black)
                for param in query_params.keys():
                    # Normalize: convert kebab-case to snake_case
                    normalized = param.lower().replace('-', '_')
                    if normalized in FORMAT_CONFIGS:
                        requested_format = normalized
                        break

                # Check path for format name (e.g., /78729/bw, /78729/rgb_black)
                # Path parts after ZIP: could be "bw", "rgb_black", etc.
                for part in path_parts:
                    if part and part != zip_code:
                        # Remove extension if present
                        path_part = part.replace('.png', '').replace('.bmp', '')
                        # Normalize: convert kebab-case to snake_case
                        normalized = path_part.lower().replace('-', '_')
                        if normalized in FORMAT_CONFIGS:
                            requested_format = normalized
                            break

                # Validate format - if invalid or not in FORMAT_CONFIGS, use default
                if requested_format not in FORMAT_CONFIGS:
                    print(f"⚠️  Invalid format '{requested_format}' requested, using default")
                    requested_format = DEFAULT_FORMAT

                # Get format info
                format_info = FORMAT_CONFIGS.get(requested_format)
                extension = format_info['extension']
                mime_type = format_info['mime_type']

                # Try to fetch: {zip}/{format}{ext}
                key = f"{zip_code}/{requested_format}{extension}"
                r2_object = await self.env.WEATHER_IMAGES.get(key)

                # If not found and not default format, fallback to default
                if r2_object is None and requested_format != DEFAULT_FORMAT:
                    print(f"⚠️  Format '{requested_format}' not found for {zip_code}, using default")
                    requested_format = DEFAULT_FORMAT
                    format_info = FORMAT_CONFIGS.get(DEFAULT_FORMAT)
                    extension = format_info['extension']
                    mime_type = format_info['mime_type']
                    key = f"{zip_code}/{requested_format}{extension}"
                    r2_object = await self.env.WEATHER_IMAGES.get(key)

                if r2_object is None:
                    return Response.new(
                        json.dumps({'error': 'Image not found. Waiting for first generation.'}),
                        {
                            'status': 404,
                            'headers': {'Content-Type': 'application/json'}
                        }
                    )

                # Get metadata (handle JavaScript object) for headers
                try:
                    generated_at = r2_object.customMetadata['generated-at'] if r2_object.customMetadata else 'unknown'
                    variant = r2_object.customMetadata.get('variant', 'unknown') if r2_object.customMetadata else 'unknown'
                except:
                    generated_at = 'unknown'
                    variant = 'unknown'

                # Return the image - get body as arrayBuffer
                image_data = await r2_object.arrayBuffer()
                return Response.new(image_data, headers=to_js({
                    "content-type": mime_type,
                    "cache-control": "public, max-age=900",
                    "x-generated-at": generated_at,
                    "x-zip-code": zip_code,
                    "x-format": requested_format,
                    "x-variant": variant
                }))

            except Exception as e:
                return Response.new(
                    json.dumps({'error': f'Failed to fetch image: {str(e)}'}),
                    {
                        'status': 500,
                        'headers': {'Content-Type': 'application/json'}
                    }
                )

        # Route: Status endpoint
        elif path == 'status':
            try:
                # Get overall status from KV
                status_json = await self.env.CONFIG.get('status')
                status = json.loads(status_json) if status_json else {}

                # Get active ZIPs
                active_zips = await get_active_zips(self.env)

                # Get metadata for each ZIP
                zip_metadata = {}
                for zip_code in active_zips:
                    try:
                        metadata_json = await self.env.CONFIG.get(f'metadata:{zip_code}')
                        if metadata_json:
                            zip_metadata[zip_code] = json.loads(metadata_json)
                    except:
                        pass

                response_data = {
                    'status': status,
                    'activeZips': active_zips,
                    'zipMetadata': zip_metadata,
                    'workerTime': datetime.utcnow().isoformat() + 'Z'
                }

                return Response.new(
                    json.dumps(response_data, indent=2),
                    headers=to_js({"content-type": "application/json"})
                )
            except Exception as e:
                return Response.new(
                    json.dumps({'error': f'Failed to fetch status: {str(e)}'}),
                    {
                        'status': 500,
                        'headers': {'Content-Type': 'application/json'}
                    }
                )

        # Route: POST /activate - Add ZIP to active regeneration list
        elif method == 'POST' and path == 'activate':
            try:
                zip_code = query_params.get('zip')
                if not zip_code or not (zip_code.isdigit() and len(zip_code) == 5):
                    return Response.new(
                        json.dumps({'error': 'Invalid ZIP code. Must be 5 digits.'}),
                        {
                            'status': 400,
                            'headers': {'Content-Type': 'application/json'}
                        }
                    )

                active_zips = await add_zip_to_active(self.env, zip_code)

                return Response.new(
                    json.dumps({
                        'success': True,
                        'zip': zip_code,
                        'message': f'ZIP {zip_code} added to active regeneration list',
                        'activeZips': active_zips
                    }),
                    headers=to_js({'Content-Type': 'application/json'})
                )
            except Exception as e:
                return Response.new(
                    json.dumps({'error': f'Failed to activate ZIP: {str(e)}'}),
                    {
                        'status': 500,
                        'headers': {'Content-Type': 'application/json'}
                    }
                )

        # Route: POST /deactivate - Remove ZIP from active regeneration list
        elif method == 'POST' and path == 'deactivate':
            try:
                zip_code = query_params.get('zip')
                if not zip_code:
                    return Response.new(
                        json.dumps({'error': 'Missing ZIP code parameter'}),
                        {
                            'status': 400,
                            'headers': {'Content-Type': 'application/json'}
                        }
                    )

                active_zips = await get_active_zips(self.env)
                if zip_code in active_zips:
                    active_zips.remove(zip_code)
                    await self.env.CONFIG.put('active_zips', json.dumps(active_zips))
                    print(f"✅ Removed {zip_code} from active_zips")

                return Response.new(
                    json.dumps({
                        'success': True,
                        'zip': zip_code,
                        'message': f'ZIP {zip_code} removed from active regeneration list',
                        'activeZips': active_zips
                    }),
                    headers=to_js({'Content-Type': 'application/json'})
                )
            except Exception as e:
                return Response.new(
                    json.dumps({'error': f'Failed to deactivate ZIP: {str(e)}'}),
                    {
                        'status': 500,
                        'headers': {'Content-Type': 'application/json'}
                    }
                )

        # Route: POST /formats/add - Add a format to a ZIP
        elif method == 'POST' and path == 'add' and 'formats' in path_parts:
            try:
                zip_code = query_params.get('zip')
                format_name = query_params.get('format', '').lower().replace('-', '_')

                if not zip_code or not (zip_code.isdigit() and len(zip_code) == 5):
                    return Response.new(
                        json.dumps({'error': 'Invalid ZIP code. Must be 5 digits.'}),
                        {
                            'status': 400,
                            'headers': {'Content-Type': 'application/json'}
                        }
                    )

                if not format_name or format_name not in FORMAT_CONFIGS:
                    return Response.new(
                        json.dumps({
                            'error': f'Invalid format. Available formats: {", ".join(FORMAT_CONFIGS.keys())}'
                        }),
                        {
                            'status': 400,
                            'headers': {'Content-Type': 'application/json'}
                        }
                    )

                formats = await add_format_to_zip(self.env, zip_code, format_name)

                return Response.new(
                    json.dumps({
                        'success': True,
                        'zip': zip_code,
                        'format': format_name,
                        'formats': formats,
                        'message': f'Added {format_name} to {zip_code}'
                    }),
                    headers=to_js({'Content-Type': 'application/json'})
                )
            except Exception as e:
                return Response.new(
                    json.dumps({'error': f'Failed to add format: {str(e)}'}),
                    {
                        'status': 500,
                        'headers': {'Content-Type': 'application/json'}
                    }
                )

        # Route: POST /formats/remove - Remove a format from a ZIP
        elif method == 'POST' and path == 'remove' and 'formats' in path_parts:
            try:
                zip_code = query_params.get('zip')
                format_name = query_params.get('format', '').lower().replace('-', '_')

                if not zip_code or not (zip_code.isdigit() and len(zip_code) == 5):
                    return Response.new(
                        json.dumps({'error': 'Invalid ZIP code. Must be 5 digits.'}),
                        {
                            'status': 400,
                            'headers': {'Content-Type': 'application/json'}
                        }
                    )

                if not format_name:
                    return Response.new(
                        json.dumps({'error': 'Missing format parameter'}),
                        {
                            'status': 400,
                            'headers': {'Content-Type': 'application/json'}
                        }
                    )

                formats = await remove_format_from_zip(self.env, zip_code, format_name)

                return Response.new(
                    json.dumps({
                        'success': True,
                        'zip': zip_code,
                        'format': format_name,
                        'formats': formats,
                        'message': f'Removed {format_name} from {zip_code}'
                    }),
                    headers=to_js({'Content-Type': 'application/json'})
                )
            except Exception as e:
                return Response.new(
                    json.dumps({'error': f'Failed to remove format: {str(e)}'}),
                    {
                        'status': 500,
                        'headers': {'Content-Type': 'application/json'}
                    }
                )

        # Route: GET /formats - Get formats for a ZIP
        elif method == 'GET' and path == 'formats':
            try:
                zip_code = query_params.get('zip')
                if not zip_code or not (zip_code.isdigit() and len(zip_code) == 5):
                    return Response.new(
                        json.dumps({'error': 'Invalid ZIP code. Must be 5 digits.'}),
                        {
                            'status': 400,
                            'headers': {'Content-Type': 'application/json'}
                        }
                    )

                formats = await get_formats_for_zip(self.env, zip_code)

                return Response.new(
                    json.dumps({
                        'zip': zip_code,
                        'formats': formats,
                        'available': list(FORMAT_CONFIGS.keys())
                    }),
                    headers=to_js({'Content-Type': 'application/json'})
                )
            except Exception as e:
                return Response.new(
                    json.dumps({'error': f'Failed to get formats: {str(e)}'}),
                    {
                        'status': 500,
                        'headers': {'Content-Type': 'application/json'}
                    }
                )

        # Route: POST /generate - Manually trigger generation for a ZIP
        elif method == 'POST' and path == 'generate':
            try:
                zip_code = query_params.get('zip')
                if not zip_code or not (zip_code.isdigit() and len(zip_code) == 5):
                    return Response.new(
                        json.dumps({'error': 'Invalid ZIP code. Must be 5 digits.'}),
                        {
                            'status': 400,
                            'headers': {'Content-Type': 'application/json'}
                        }
                    )

                # Get configuration
                config = WorkerConfig(self.env)
                if not config.OWM_KEY:
                    return Response.new(
                        json.dumps({'error': 'OWM_API_KEY not configured'}),
                        {
                            'status': 500,
                            'headers': {'Content-Type': 'application/json'}
                        }
                    )

                # Geocode the ZIP (uses cache if available)
                geo_data = await geocode_zip(self.env, zip_code, config.OWM_KEY)

                # Get formats configured for this ZIP from KV
                enabled_formats = await get_formats_for_zip(self.env, zip_code)

                # Generate images for all configured formats
                generated_formats = []
                all_metadata = {}
                for format_name in enabled_formats:
                    try:
                        # Generate the weather image for this format
                        image_bytes, metadata, _ = await generate_weather_image(
                            self.env,
                            zip_code,
                            geo_data['lat'],
                            geo_data['lon'],
                            format_name
                        )

                        # Upload to R2
                        await upload_to_r2(self.env, image_bytes, metadata, zip_code, format_name)

                        generated_formats.append(format_name)
                        all_metadata[format_name] = metadata
                    except Exception as e:
                        print(f"Failed to generate {format_name} for {zip_code}: {e}")
                        all_metadata[format_name] = {'error': str(e)}

                return Response.new(
                    json.dumps({
                        'success': True,
                        'zip': zip_code,
                        'formats': generated_formats,
                        'metadata': all_metadata,
                        'message': f'Generated {len(generated_formats)} format(s) for ZIP {zip_code}'
                    }),
                    headers=to_js({'Content-Type': 'application/json'})
                )
            except Exception as e:
                return Response.new(
                    json.dumps({'error': f'Failed to generate image: {str(e)}'}),
                    {
                        'status': 500,
                        'headers': {'Content-Type': 'application/json'}
                    }
                )

        # Default: 404
        else:
            return Response.new(
                json.dumps({'error': 'Not found'}),
                {
                    'status': 404,
                    'headers': {'Content-Type': 'application/json'}
                }
            )
