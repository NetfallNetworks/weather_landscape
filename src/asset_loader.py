"""
Asset loader for Cloudflare Workers
Handles loading static files using the ASSETS binding
"""

import io
import asyncio


class AssetLoader:
    """Loads static assets in Cloudflare Workers using ASSETS binding"""

    def __init__(self, env=None):
        """
        Initialize the asset loader

        Args:
            env: Cloudflare Worker environment object with ASSETS binding
        """
        self.env = env
        self._cache = {}
        self._preloaded = False

    async def preload_assets(self):
        """Preload common assets into cache"""
        if self._preloaded:
            return

        print("DEBUG: Preloading assets...")

        # List of assets to preload
        assets_to_load = [
            'p_weather/template_rgb.bmp',
            'p_weather/template_wb.bmp',
        ]

        # Add sprite files
        sprite_dirs = ['p_weather/sprite_rgb', 'p_weather/sprite']
        sprite_names = ['cloud', 'digit', 'house', 'pine', 'east', 'palm', 'tree']

        for sprite_dir in sprite_dirs:
            for name in sprite_names:
                for i in range(100):  # Load up to 100 variants
                    path = f"{sprite_dir}/{name}_{i:02d}.png"
                    assets_to_load.append(path)

        # Load all assets
        for path in assets_to_load:
            try:
                await self.load_asset(path)
            except:
                # Ignore missing assets (not all sprites exist)
                pass

        self._preloaded = True
        print(f"DEBUG: Preloaded {len(self._cache)} assets")

    async def load_asset(self, path: str) -> bytes:
        """
        Load an asset file as bytes

        Args:
            path: Path to the asset file (relative to src/)

        Returns:
            bytes: The file contents
        """
        # Check cache first
        if path in self._cache:
            return self._cache[path]

        # Try Workers ASSETS binding first
        if self.env and hasattr(self.env, 'ASSETS'):
            try:
                # Create a fake request for the asset
                from js import Request
                # ASSETS expects an absolute URL, construct one
                request = Request.new(f"http://fake-host/{path}")

                # Fetch using ASSETS binding
                response = await self.env.ASSETS.fetch(request.js_object)

                # Check if successful
                if response.ok:
                    # Read the response as bytes
                    array_buffer = await response.arrayBuffer()
                    # Convert JS ArrayBuffer to Python bytes
                    from js import Uint8Array
                    uint8_array = Uint8Array.new(array_buffer)
                    data = bytes(uint8_array.to_py())

                    # Cache the result
                    self._cache[path] = data
                    return data
                else:
                    print(f"DEBUG: ASSETS fetch failed for {path} with status {response.status}")
            except Exception as e:
                print(f"DEBUG: ASSETS binding failed for {path}: {e}")

        # Fallback to local file system (for development)
        try:
            with open(path, 'rb') as f:
                data = f.read()
                self._cache[path] = data
                return data
        except Exception as e:
            raise FileNotFoundError(f"Could not load asset: {path}. Error: {e}")

    def get_asset_sync(self, path: str) -> bytes:
        """
        Get an asset synchronously from cache (must be preloaded)

        Args:
            path: Path to the asset file

        Returns:
            bytes: The file contents

        Raises:
            KeyError: If asset not in cache
        """
        if path not in self._cache:
            # Try filesystem as fallback
            try:
                with open(path, 'rb') as f:
                    data = f.read()
                    self._cache[path] = data
                    return data
            except:
                raise KeyError(f"Asset not in cache and filesystem load failed: {path}")

        return self._cache[path]


# Global instance that can be set by the worker
_global_loader = None


def set_global_loader(env):
    """Set the global asset loader with the worker environment"""
    global _global_loader
    _global_loader = AssetLoader(env)


def get_global_loader() -> AssetLoader:
    """Get the global asset loader instance"""
    global _global_loader
    if _global_loader is None:
        # Create a fallback loader without env (for local development)
        _global_loader = AssetLoader(None)
    return _global_loader
