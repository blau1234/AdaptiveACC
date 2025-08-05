import ifcopenshell
import json
from typing import Dict, List, Any, Union

class IFCParser:
    """IFC file parser"""
    
    def __init__(self):
        self.ifc_file = None
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
            self.ifc_file = ifcopenshell.open(file_path)
            return True
        except Exception as e:
            print(f"Failed to load IFC file: {e}")
            return False
    
    def get_elements_by_type(self, element_type: str) -> List[ifcopenshell.entity_instance]:
        """Return list of IfcOpenShell instances of the given IFC type (IfcWall, IfcSlab …)."""
        
        if not self.ifc_file:
            return []
        return self.ifc_file.by_type(element_type)
    
    def extract_properties(
        self,
        target: Union["ifcopenshell.entity_instance", List["ifcopenshell.entity_instance"]]
    ) -> Union[Dict[str, Any], List[Dict[str, Any]]]:
        """Return serializable property dict(s) for one or many IFC elements."""
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