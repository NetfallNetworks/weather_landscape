"""
Cloudflare Worker for Weather Landscape Image Generation
Generates weather visualizations and serves them from R2 storage
Supports multiple ZIP codes with geocoding and KV caching
"""

from js import Response, Headers, fetch
from workers import WorkerEntrypoint
import json
from datetime import datetime


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

    def to_weather_config(self, lat, lon):
        """
        Convert to WeatherLandscape config format

        Args:
            lat: Latitude (required)
            lon: Longitude (required)
        """
        # Import at runtime to allow Pillow to load first
        from configs import WLConfig_RGB_White

        config = WLConfig_RGB_White()
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


async def generate_weather_image(env, zip_code, lat, lon):
    """
    Generate a weather landscape image using current weather data

    Args:
        env: Worker environment
        zip_code: ZIP code for this generation
        lat: Latitude for weather lookup
        lon: Longitude for weather lookup

    Returns:
        tuple: (image_bytes, metadata_dict, zip_code)
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

        # Generate the image with provided lat/lon
        wl = WeatherLandscape(config.to_weather_config(lat=lat, lon=lon))
        img = await wl.MakeImage()

        # Convert PIL Image to bytes
        buffer = io.BytesIO()
        img.save(buffer, format='PNG')
        image_bytes = buffer.getvalue()

        # Create metadata
        metadata = {
            'generatedAt': datetime.utcnow().isoformat() + 'Z',
            'latitude': lat,
            'longitude': lon,
            'zipCode': zip_code,
            'fileSize': len(image_bytes),
            'format': 'PNG',
            'variant': 'rgb_white'
        }

        return image_bytes, metadata, zip_code

    except Exception as e:
        print(f"Error generating image for {zip_code}: {e}")
        raise


async def upload_to_r2(env, image_bytes, metadata, zip_code):
    """
    Upload generated image to R2 bucket

    Args:
        env: Worker environment
        image_bytes: PNG image as bytes
        metadata: Image metadata dict
        zip_code: ZIP code for folder organization

    Returns:
        bool: True if successful
    """
    try:
        # Create the key for the latest image with zip code folder
        key = f"{zip_code}/latest.png"

        # Prepare R2 metadata
        custom_metadata = {
            'generated-at': metadata['generatedAt'],
            'latitude': str(metadata['latitude']),
            'longitude': str(metadata['longitude']),
            'zip-code': zip_code,
            'file-size': str(metadata['fileSize'])
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
                    'contentType': 'image/png',
                },
                'customMetadata': custom_metadata
            }
        )

        print(f"✅ Uploaded {key} to R2 ({len(image_bytes)} bytes)")

        # Also save metadata to KV (per-ZIP)
        await env.CONFIG.put(
            f'metadata:{zip_code}',
            json.dumps(metadata)
        )

        return True

    except Exception as e:
        print(f"Error uploading {zip_code} to R2: {e}")
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

                # Geocode the ZIP (uses cache if available)
                geo_data = await geocode_zip(self.env, zip_code, config.OWM_KEY)

                # Generate the weather image
                print(f"🎨 Generating weather landscape for {zip_code}...")
                image_bytes, metadata, _ = await generate_weather_image(
                    self.env,
                    zip_code,
                    geo_data['lat'],
                    geo_data['lon']
                )

                # Upload to R2
                print(f"☁️  Uploading {zip_code} to R2...")
                await upload_to_r2(self.env, image_bytes, metadata, zip_code)

                success_count += 1
                print(f"✅ Completed {zip_code}")

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
        - GET / - Returns HTML info page with links to all active ZIPs
        - GET /{zip} - Returns latest weather image for ZIP
        - GET /{zip}/ - Returns latest weather image for ZIP
        - GET /{zip}/latest.png - Returns latest weather image for ZIP
        - GET /{zip}/* - Returns latest weather image for ZIP (any path with ZIP)
        - GET /status - Returns generation status and metadata for all ZIPs
        """
        url = request.url
        path_parts = url.split('?')[0].split('/')
        path = path_parts[-1] if len(path_parts) > 0 else ''

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
                # Get active ZIPs to show links
                active_zips = await get_active_zips(self.env)

                zip_links = '\n'.join([
                    f'<li><a href="/{zip}">ZIP {zip}</a></li>'
                    for zip in active_zips
                ])

                html = f"""
                <!DOCTYPE html>
                <html>
                <head>
                    <title>Weather Landscape</title>
                    <style>
                        body {{
                            font-family: system-ui, -apple-system, sans-serif;
                            max-width: 600px;
                            margin: 2rem auto;
                            padding: 2rem;
                            background: #f5f5f5;
                        }}
                        h1 {{ color: #333; }}
                        ul {{ list-style: none; padding: 0; }}
                        li {{ margin: 0.5rem 0; }}
                        a {{
                            color: #0066cc;
                            text-decoration: none;
                            padding: 0.5rem 1rem;
                            background: white;
                            border-radius: 4px;
                            display: inline-block;
                        }}
                        a:hover {{ background: #e6f2ff; }}
                    </style>
                </head>
                <body>
                    <h1>🌤️ Weather Landscape</h1>
                    <h2>Active ZIP Codes</h2>
                    <ul>{zip_links}</ul>
                </body>
                </html>
                """
                return Response.new(html, {
                    'status': 200,
                    'headers': {'Content-Type': 'text/html; charset=utf-8'}
                })
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

                # Fetch image from R2 using zip code folder
                r2_object = await self.env.WEATHER_IMAGES.get(f'{zip_code}/latest.png')

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
                except:
                    generated_at = 'unknown'

                # Return the image - get body as arrayBuffer
                image_data = await r2_object.arrayBuffer()
                return Response.new(image_data, {
                    'status': 200,
                    'headers': {
                        'Content-Type': 'image/png',
                        'Cache-Control': 'public, max-age=900',
                        'X-Generated-At': generated_at,
                        'X-Zip-Code': zip_code
                    }
                })

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
                    {
                        'status': 200,
                        'headers': {'Content-Type': 'application/json'}
                    }
                )
            except Exception as e:
                return Response.new(
                    json.dumps({'error': f'Failed to fetch status: {str(e)}'}),
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
