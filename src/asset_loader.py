"""
Asset loader for Cloudflare Workers
Handles loading static files from the virtual filesystem
"""

import os


class AssetLoader:
    """Loads static assets in Cloudflare Workers from virtual filesystem"""

    def __init__(self):
        """Initialize the asset loader"""
        self._cache = {}
        # Possible base paths where files might be located in the worker
        self._search_paths = [
            "",  # Current directory
            "/",  # Root
            "/src/",  # Src directory with leading slash
            "src/",  # Src directory without leading slash
        ]

    def _find_file(self, path: str) -> str:
        """
        Try to find a file in various possible locations

        Args:
            path: Relative path to the file

        Returns:
            str: The actual path where the file was found

        Raises:
            FileNotFoundError: If file cannot be found
        """
        # Remove leading slash if present
        clean_path = path.lstrip('/')

        # Try each search path
        for base in self._search_paths:
            full_path = os.path.join(base, clean_path) if base else clean_path
            try:
                with open(full_path, 'rb') as f:
                    f.read(1)  # Just test if readable
                print(f"DEBUG: Found file at: {full_path}")
                return full_path
            except (FileNotFoundError, IOError, OSError):
                continue

        raise FileNotFoundError(f"Could not find asset: {path} in any search path")

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

        # Find and load the file
        actual_path = self._find_file(path)
        with open(actual_path, 'rb') as f:
            data = f.read()

        # Cache the result
        self._cache[path] = data
        print(f"DEBUG: Loaded {path} ({len(data)} bytes)")
        return data


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
