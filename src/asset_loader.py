"""
Asset loader for Cloudflare Workers
Handles loading static files bundled as Data modules
"""

import sys
import os


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

        # Method 1: Try __loader__.get_data() (for bundled Data modules)
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
                else:
                    print(f"DEBUG: __loader__ exists but has no get_data method")
                    print(f"DEBUG: __loader__ attributes: {dir(loader)}")
            else:
                print(f"DEBUG: No __loader__ found in __main__")
        except Exception as e:
            print(f"DEBUG: Exception checking __loader__: {type(e).__name__}: {e}")

        # Method 2: Try direct filesystem access (for local development)
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
