"""
Asset loader for Cloudflare Workers
Handles loading static files bundled as Data modules
"""

import sys
import os
import pkgutil


class AssetLoader:
    """Loads static assets in Cloudflare Workers"""

    def __init__(self):
        """Initialize the asset loader"""
        self._cache = {}

    def load_asset(self, path: str) -> bytes:
        """
        Load an asset file as bytes

        Args:
            path: Path to the asset file

        Returns:
            bytes: The file contents
        """
        # Check cache first
        if path in self._cache:
            return self._cache[path]

        print(f"DEBUG: === Loading asset: {path} ===")

        # Method 1: Try importlib.resources (Python 3.7+)
        try:
            import importlib.resources as importlib_resources
            parts = path.split('/')
            if len(parts) > 1:
                # For nested paths like "p_weather/sprite_rgb/house_00.png"
                # Convert to package: "p_weather.sprite_rgb" and resource: "house_00.png"
                package_parts = parts[:-1]  # All but the last part
                package_name = '.'.join(package_parts)
                resource_name = parts[-1]  # Just the filename

                print(f"DEBUG: Trying importlib.resources.read_binary('{package_name}', '{resource_name}')...")
                data = importlib_resources.read_binary(package_name, resource_name)
                if data:
                    self._cache[path] = data
                    print(f"DEBUG: ✓ SUCCESS via importlib.resources: {len(data)} bytes")
                    return data
                else:
                    print(f"DEBUG: ✗ importlib.resources returned None")
        except Exception as e:
            print(f"DEBUG: ✗ importlib.resources failed: {type(e).__name__}: {e}")

        # Method 2: Try pkgutil.get_data() for bundled modules
        try:
            # Split path into package and resource
            # e.g., "p_weather/template_rgb.bmp" -> package="p_weather", resource="template_rgb.bmp"
            parts = path.split('/')
            if len(parts) > 1:
                package_name = parts[0]
                resource_name = '/'.join(parts[1:])

                print(f"DEBUG: Trying pkgutil.get_data('{package_name}', '{resource_name}')...")
                data = pkgutil.get_data(package_name, resource_name)
                if data:
                    self._cache[path] = data
                    print(f"DEBUG: ✓ SUCCESS via pkgutil.get_data: {len(data)} bytes")
                    return data
                else:
                    print(f"DEBUG: ✗ pkgutil.get_data returned None or empty")
        except Exception as e:
            print(f"DEBUG: ✗ pkgutil.get_data failed: {type(e).__name__}: {e}")
            import traceback
            print(f"DEBUG: Traceback: {traceback.format_exc()}")

        # Method 3: Try importing as a module directly
        try:
            # Convert path to module name: p_weather/template_rgb.bmp -> p_weather.template_rgb
            module_path = path.replace('/', '.').rsplit('.', 1)[0]
            print(f"DEBUG: Trying to import module '{module_path}'...")

            import importlib
            mod = importlib.import_module(module_path)

            # Check if module has __file__ or data attribute
            if hasattr(mod, '__file__'):
                print(f"DEBUG: Module has __file__: {mod.__file__}")
                with open(mod.__file__, 'rb') as f:
                    data = f.read()
                    self._cache[path] = data
                    print(f"DEBUG: ✓ SUCCESS via module import: {len(data)} bytes")
                    return data
        except Exception as e:
            print(f"DEBUG: ✗ Module import failed: {type(e).__name__}: {e}")

        # Method 4: Try __loader__.get_data() (for bundled Data modules)
        try:
            print(f"DEBUG: Checking for __loader__...")
            if hasattr(sys.modules['__main__'], '__loader__'):
                loader = sys.modules['__main__'].__loader__
                print(f"DEBUG: __loader__ found: {type(loader)}")
                print(f"DEBUG: __loader__ has get_data: {hasattr(loader, 'get_data')}")

                if hasattr(loader, 'get_data'):
                    # Try various path combinations
                    paths_to_try = [
                        path,
                        f"src/{path}",
                        f"/{path}",
                        f"/src/{path}",
                    ]

                    for try_path in paths_to_try:
                        try:
                            print(f"DEBUG: Trying __loader__.get_data('{try_path}')...")
                            data = loader.get_data(try_path)
                            self._cache[path] = data
                            print(f"DEBUG: ✓ SUCCESS via __loader__.get_data('{try_path}'): {len(data)} bytes")
                            return data
                        except Exception as e:
                            print(f"DEBUG: ✗ Failed __loader__.get_data('{try_path}'): {type(e).__name__}: {e}")
        except Exception as e:
            print(f"DEBUG: Exception checking __loader__: {type(e).__name__}: {e}")

        # Method 5: Try direct filesystem access (for local development)
        print(f"DEBUG: Trying filesystem access...")
        search_paths = ["", "src/", "/", "/src/"]
        for base in search_paths:
            try:
                full_path = os.path.join(base, path) if base else path
                print(f"DEBUG: Trying open('{full_path}')...")
                with open(full_path, 'rb') as f:
                    data = f.read()
                self._cache[path] = data
                print(f"DEBUG: ✓ SUCCESS via filesystem: {full_path} ({len(data)} bytes)")
                return data
            except Exception as e:
                print(f"DEBUG: ✗ Failed open('{full_path}'): {type(e).__name__}: {e}")

        print(f"DEBUG: === All methods failed for: {path} ===")
        raise FileNotFoundError(f"Could not load asset: {path}")


# Global instance
_global_loader = None


def set_global_loader():
    """Initialize the global asset loader"""
    global _global_loader
    _global_loader = AssetLoader()


def get_global_loader() -> AssetLoader:
    """Get the global asset loader instance"""
    global _global_loader
    if _global_loader is None:
        _global_loader = AssetLoader()
    return _global_loader
