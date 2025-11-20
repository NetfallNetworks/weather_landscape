"""
R2 Storage utilities for Weather Landscape workers
"""

import json
from .config import FORMAT_CONFIGS, DEFAULT_FORMAT


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

        print(f"Uploaded {key} to R2 ({len(image_bytes)} bytes)")

        # Save metadata to KV (per-ZIP-format)
        await env.CONFIG.put(
            f'metadata:{zip_code}:{format_name}',
            json.dumps(metadata)
        )

        return True

    except Exception as e:
        print(f"Error uploading {zip_code}/{format_name} to R2: {e}")
        raise
