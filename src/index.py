"""
Cloudflare Worker for Weather Landscape Image Generation
Generates weather visualizations and serves them from R2 storage
"""

from js import Response, Headers
from workers import WorkerEntrypoint
import json
from datetime import datetime


class WorkerConfig:
    """Configuration loaded from KV and environment"""
    def __init__(self, env):
        # Access environment variables directly from env object
        # Secrets (like OWM_API_KEY) are set via: wrangler secret put OWM_API_KEY
        # Vars (like DEFAULT_LAT) are set in wrangler.toml [vars] section
        try:
            self.OWM_KEY = getattr(env, 'OWM_API_KEY', None)
        except Exception as e:
            self.OWM_KEY = None

        try:
            self.OWM_LAT = float(getattr(env, 'DEFAULT_LAT', 30.4515))
        except:
            self.OWM_LAT = 30.4515

        try:
            self.OWM_LON = float(getattr(env, 'DEFAULT_LON', -97.7676))
        except:
            self.OWM_LON = -97.7676

        try:
            self.ZIP_CODE = str(getattr(env, 'DEFAULT_ZIP', '78729'))
        except:
            self.ZIP_CODE = '78729'

        self.WORK_DIR = "/tmp"

    def to_weather_config(self):
        """Convert to WeatherLandscape config format"""
        # Import at runtime to allow Pillow to load first
        from configs import WLConfig_RGB_White

        config = WLConfig_RGB_White()
        config.OWM_KEY = self.OWM_KEY
        config.OWM_LAT = self.OWM_LAT
        config.OWM_LON = self.OWM_LON
        config.WORK_DIR = self.WORK_DIR
        return config


async def generate_weather_image(env):
    """
    Generate a weather landscape image using current weather data
    Returns: (image_bytes, metadata_dict, zip_code)
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

        # Generate the image
        wl = WeatherLandscape(config.to_weather_config())
        img = await wl.MakeImage()

        # Convert PIL Image to bytes
        buffer = io.BytesIO()
        img.save(buffer, format='PNG')
        image_bytes = buffer.getvalue()

        # Create metadata
        metadata = {
            'generatedAt': datetime.utcnow().isoformat() + 'Z',
            'latitude': config.OWM_LAT,
            'longitude': config.OWM_LON,
            'zipCode': config.ZIP_CODE,
            'fileSize': len(image_bytes),
            'format': 'PNG',
            'variant': 'rgb_white'
        }

        return image_bytes, metadata, config.ZIP_CODE

    except Exception as e:
        print(f"Error generating image: {e}")
        raise


async def upload_to_r2(env, image_bytes, metadata, zip_code):
    """Upload generated image to R2 bucket"""
    try:
        # Create the key for the current image with zip code folder
        key = f"{zip_code}/current.png"

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

        # Also save metadata to KV
        await env.CONFIG.put(
            'latest-metadata',
            json.dumps(metadata)
        )

        return True

    except Exception as e:
        print(f"Error uploading to R2: {e}")
        raise


class Default(WorkerEntrypoint):
    """
    Main Worker Entrypoint for Weather Landscape
    Handles both scheduled (cron) and fetch (HTTP) requests
    """

    async def scheduled(self, event, env, ctx):
        """
        Scheduled handler - runs on cron trigger (every 15 minutes)
        Generates new weather landscape image and uploads to R2
        """
        print(f"🕐 Scheduled run started at {datetime.utcnow().isoformat()}")

        try:
            # Generate the weather image
            print("Generating weather landscape image...")
            image_bytes, metadata, zip_code = await generate_weather_image(self.env)

            # Upload to R2
            print("Uploading to R2...")
            await upload_to_r2(self.env, image_bytes, metadata, zip_code)

            # Update status in KV
            status = {
                'lastSuccess': datetime.utcnow().isoformat() + 'Z',
                'lastError': None,
                'errorCount': 0
            }
            await self.env.CONFIG.put('status', json.dumps(status))

            print("✅ Scheduled run completed successfully")

        except Exception as e:
            error_msg = str(e)
            print(f"❌ Scheduled run failed: {error_msg}")

            # Update error status in KV
            try:
                status = {
                    'lastSuccess': None,
                    'lastError': error_msg,
                    'errorTimestamp': datetime.utcnow().isoformat() + 'Z'
                }
                await self.env.CONFIG.put('status', json.dumps(status))
            except:
                pass

    async def on_fetch(self, request, env, ctx):
        """
        HTTP request handler - serves images from R2

        Routes:
        - GET / - Returns HTML page with current image
        - GET /current.png - Returns the current weather image from R2
        - GET /status - Returns generation status and metadata
        - POST /generate - Manually trigger image generation (for testing)
        """
        url = request.url
        path = url.split('/')[-1] if '/' in url else ''

        # Route: Serve current image
        if path == 'current.png' or path == '':
            try:
                # Get zip code from config
                config = WorkerConfig(self.env)
                zip_code = config.ZIP_CODE

                # Fetch image from R2 using zip code folder
                r2_object = await self.env.WEATHER_IMAGES.get(f'{zip_code}/current.png')

                if r2_object is None:
                    return Response.new(
                        json.dumps({'error': 'Image not found. Waiting for first generation.'}),
                        {
                            'status': 404,
                            'headers': {'Content-Type': 'application/json'}
                        }
                    )

                # Return image with appropriate headers
                headers = Headers.new()
                headers.set('Content-Type', 'image/png')
                headers.set('Cache-Control', 'public, max-age=900')  # 15 minutes
                headers.set('X-Generated-At', r2_object.customMetadata.get('generated-at', 'unknown'))

                if path == '':
                    # Return HTML page with image
                    html = f"""
                    <!DOCTYPE html>
                    <html>
                    <head>
                        <title>Weather Landscape</title>
                        <style>
                            body {{
                                font-family: system-ui, -apple-system, sans-serif;
                                display: flex;
                                flex-direction: column;
                                align-items: center;
                                padding: 2rem;
                                background: #f5f5f5;
                            }}
                            img {{
                                max-width: 100%;
                                border: 1px solid #ddd;
                                box-shadow: 0 2px 8px rgba(0,0,0,0.1);
                            }}
                            .info {{
                                margin-top: 1rem;
                                text-align: center;
                                color: #666;
                            }}
                        </style>
                    </head>
                    <body>
                        <h1>Weather Landscape 🌤️</h1>
                        <img src="/current.png" alt="Weather Landscape">
                        <div class="info">
                            <p>Generated: {r2_object.customMetadata.get('generated-at', 'unknown')}</p>
                            <p>Location: {r2_object.customMetadata.get('latitude', '?')}, {r2_object.customMetadata.get('longitude', '?')}</p>
                            <p><a href="/status">View Status</a></p>
                        </div>
                    </body>
                    </html>
                    """
                    return Response.new(html, {
                        'headers': {'Content-Type': 'text/html; charset=utf-8'}
                    })

                # Return just the image
                return Response.new(r2_object.body, {'headers': headers})

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
                # Get status from KV
                status_json = await self.env.CONFIG.get('status')
                metadata_json = await self.env.CONFIG.get('latest-metadata')

                status = json.loads(status_json) if status_json else {}
                metadata = json.loads(metadata_json) if metadata_json else {}

                response_data = {
                    'status': status,
                    'metadata': metadata,
                    'workerTime': datetime.utcnow().isoformat() + 'Z'
                }

                return Response.new(
                    json.dumps(response_data, indent=2),
                    {
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

        # Route: Manual generation trigger (for testing)
        elif path == 'generate' and request.method == 'POST':
            try:
                print("Manual generation triggered")
                image_bytes, metadata, zip_code = await generate_weather_image(self.env)
                await upload_to_r2(self.env, image_bytes, metadata, zip_code)

                return Response.new(
                    json.dumps({'success': True, 'metadata': metadata}),
                    {
                        'headers': {'Content-Type': 'application/json'}
                    }
                )
            except Exception as e:
                return Response.new(
                    json.dumps({'error': f'Generation failed: {str(e)}'}),
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
