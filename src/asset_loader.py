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

        # Try different methods to load the file

        # Method 1: Try __loader__.get_data() (for bundled Data modules)
        try:
            if hasattr(sys.modules['__main__'], '__loader__'):
                loader = sys.modules['__main__'].__loader__
                # Try with src/ prefix
                try:
                    data = loader.get_data(f"src/{path}")
                    self._cache[path] = data
                    print(f"DEBUG: Loaded via __loader__ with src/ prefix: {path} ({len(data)} bytes)")
                    return data
                except:
                    pass

                # Try without src/ prefix
                try:
                    data = loader.get_data(path)
                    self._cache[path] = data
                    print(f"DEBUG: Loaded via __loader__: {path} ({len(data)} bytes)")
                    return data
                except:
                    pass
        except Exception as e:
            print(f"DEBUG: __loader__.get_data() failed: {e}")

        # Method 2: Try direct filesystem access (for local development)
        search_paths = ["", "src/", "/", "/src/"]
        for base in search_paths:
            try:
                full_path = os.path.join(base, path) if base else path
                with open(full_path, 'rb') as f:
                    data = f.read()
                self._cache[path] = data
                print(f"DEBUG: Loaded via filesystem: {full_path} ({len(data)} bytes)")
                return data
            except (FileNotFoundError, IOError, OSError):
                continue

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
