"""
Landscape Generator Worker

Queue consumer worker that:
1. Receives job messages from Cloudflare Queue
2. Reads weather data from KV
3. Generates one image in the specified format
4. Uploads to R2
"""

import json
from datetime import datetime
from workers import WorkerEntrypoint
from js import JSON


from shared import (
    WorkerConfig,
    FORMAT_CONFIGS,
    get_weather_data,
    upload_to_r2
)


class Default(WorkerEntrypoint):
    """
    Landscape Generator Worker
    Consumes queue messages and generates weather landscape images
    """

    async def queue(self, batch, env, ctx):
        """
        Queue consumer handler - processes batches of generation jobs

        Args:
            batch: Batch of messages from the queue
            env: Worker environment
            ctx: Execution context
        """
        env = self.env

        print(f"Landscape Generator received {len(batch.messages)} job(s)")

        success_count = 0
        error_count = 0

        for message in batch.messages:
            try:
                # Parse job data (convert JsProxy via JSON round-trip)
                job = json.loads(JSON.stringify(message.body))

                zip_code = job['zip_code']
                format_name = job['format_name']
                lat = job['lat']
                lon = job['lon']

                print(f"Processing: {zip_code}/{format_name}")

                # Get weather data from KV
                weather_data = await get_weather_data(env, zip_code)
                if not weather_data:
                    raise ValueError(f"No weather data found for {zip_code}")

                # Generate the image
                image_bytes, metadata, _ = await self._generate_image(
                    env, zip_code, lat, lon, format_name, weather_data
                )

                # Upload to R2
                await upload_to_r2(env, image_bytes, metadata, zip_code, format_name)

                print(f"Completed: {zip_code}/{format_name} ({len(image_bytes)} bytes)")

                # Acknowledge the message
                message.ack()
                success_count += 1

            except Exception as e:
                error_count += 1
                import traceback; traceback.print_exc(); print(f"ERROR processing job: {e}")

                # Retry the message (will be re-delivered)
                message.retry()

        print(f"Batch completed: {success_count} success, {error_count} errors")

    async def _generate_image(self, env, zip_code, lat, lon, format_name, weather_data):
        """
        Generate a weather landscape image from pre-fetched data

        Args:
            env: Worker environment
            zip_code: ZIP code
            lat: Latitude
            lon: Longitude
            format_name: Format to generate
            weather_data: Pre-fetched weather data

        Returns:
            tuple: (image_bytes, metadata_dict, format_name)
        """
        # Import at runtime (Pillow loaded from cf-requirements.txt)
        from shared.weather_landscape import WeatherLandscape
        from shared.asset_loader import set_global_loader
        import io

        # Initialize the global asset loader
        set_global_loader()

        # Load configuration (no API key needed - we use pre-fetched data)
        config = WorkerConfig(env)

        # Get format info
        format_info = FORMAT_CONFIGS.get(format_name)
        if not format_info:
            raise ValueError(f"Unknown format: {format_name}")

        # Create weather config for this format
        weather_config = config.to_weather_config(lat=lat, lon=lon, format_name=format_name)

        # Debug logging
        print(f"  Config: {weather_config.__class__.__name__}")
        print(f"  Template: {weather_config.TEMPLATE_FILENAME}")

        # Generate image using pre-fetched weather data (no API key required)
        wl = WeatherLandscape(weather_config)
        img = await wl.MakeImageFromData(weather_data)

        # Convert PIL Image to bytes
        buffer = io.BytesIO()
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


# Export the worker class
