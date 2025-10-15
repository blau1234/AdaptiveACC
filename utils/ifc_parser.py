import ifcopenshell
import json
from typing import Dict, List, Any, Union
from utils.ifc_file_manager import IFCFileManager

class IFCParser:
    """IFC file parser"""

    def __init__(self):
        self.ifc_file = None
        self.ifc_file_manager = None
        self.file_path = None
        self.elements = {}

    def load_file(self, file_path: str) -> bool:
        """
        Load IFC file
        Args:
            file_path: IFC file path

        Returns:
            bool: Whether loading was successful
        """
        try:
            # Store the file path for later use
            self.file_path = file_path
            # Open the file using the manager to verify it's valid
            with IFCFileManager(file_path) as ifc_file:
                # File is valid, store reference for lazy loading
                self.ifc_file = None  # Will be loaded when needed
            return True
        except Exception as e:
            print(f"Failed to load IFC file: {e}")
            return False

    def _ensure_file_loaded(self):
        """Ensure the IFC file is loaded for operations."""
        if self.ifc_file is None and self.file_path:
            self.ifc_file_manager = IFCFileManager(self.file_path)
            self.ifc_file = self.ifc_file_manager.__enter__()

    def close(self):
        """Close the IFC file if it's open."""
        if self.ifc_file_manager is not None:
            self.ifc_file_manager.__exit__(None, None, None)
            self.ifc_file = None
            self.ifc_file_manager = None
    
    def get_elements_by_type(self, element_type: str) -> List[ifcopenshell.entity_instance]:
        """Return list of IfcOpenShell instances of the given IFC type (IfcWall, IfcSlab …)."""
        self._ensure_file_loaded()
        if not self.ifc_file:
            return []
        return self.ifc_file.by_type(element_type)
    
    def extract_properties(
        self,
        target: Union["ifcopenshell.entity_instance", List["ifcopenshell.entity_instance"]]
    ) -> Union[Dict[str, Any], List[Dict[str, Any]]]:
        """Return serializable property dict(s) for one or many IFC elements."""
        self._ensure_file_loaded()
        def _one(e):
            props = {}
            if hasattr(e, 'ObjectPlacement') and e.ObjectPlacement:
                props['placement'] = str(e.ObjectPlacement)
            if hasattr(e, 'IsDefinedBy'):
                for rel in e.IsDefinedBy:
                    if rel.is_a('IfcRelDefinesByProperties'):
                        pset = rel.RelatingPropertyDefinition
                        if pset.is_a('IfcPropertySet'):
                            props.update({p.Name: p.NominalValue.wrappedValue
                                        for p in pset.HasProperties})
            return props

        return [ _one(el) for el in target ] if isinstance(target, list) else _one(target)

    def __del__(self):
        """Destructor to ensure file is properly closed."""
        self.close()