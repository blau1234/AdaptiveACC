"""
IFC File Manager - Context manager for safe IfcOpenShell file handling.

This module provides a context manager to properly handle IfcOpenShell file lifecycle,
preventing AttributeError warnings during interpreter shutdown.
"""

import ifcopenshell
from typing import Optional


class IFCFileManager:
    """
    Context manager for IfcOpenShell files.

    Usage:
        with IFCFileManager("path/to/file.ifc") as ifc_file:
            # Use ifc_file normally
            walls = ifc_file.by_type("IfcWall")

    This ensures proper cleanup and prevents shutdown warnings.
    """

    def __init__(self, file_path: str):
        """
        Initialize the IFC file manager.

        Args:
            file_path: Path to the IFC file
        """
        self.file_path = file_path
        self.ifc_file: Optional[ifcopenshell.file] = None

    def __enter__(self) -> ifcopenshell.file:
        """
        Open the IFC file.

        Returns:
            Opened IFC file object
        """
        self.ifc_file = ifcopenshell.open(self.file_path)
        return self.ifc_file

    def __exit__(self, exc_type, exc_val, exc_tb):
        """
        Close the IFC file safely.

        Args:
            exc_type: Exception type if an error occurred
            exc_val: Exception value if an error occurred
            exc_tb: Exception traceback if an error occurred

        Returns:
            False to propagate any exceptions
        """
        if self.ifc_file is not None:
            try:
                # Explicitly delete the file object to trigger cleanup
                # while the wrapper module is still available
                del self.ifc_file
                self.ifc_file = None
            except Exception:
                # Silently ignore cleanup errors
                pass
        return False
