# engine/utils/json_schema.py
import json
from typing import Dict, Any, List

class JsonSchema:
    """
    Utility class for defining, validating, and describing JSON data structures,
    primarily used for engine configuration, project files, scene data, and 
    component properties in the Inspector Panel.
    """

    # --- Standardized Primitive Types ---
    PRIMITIVE_TYPES = [
        "string", "int", "float", "boolean", "color",
        "vector2", "vector3", "vector2_list", "vector3_list", "color_list",
        "asset_selector", "uid_selector", "dropdown", "list", "dict"
    ]
    
    @staticmethod
    def is_valid_type(type_str: str) -> bool:
        """Checks if a given string is a recognized primitive type."""
        return type_str in JsonSchema.PRIMITIVE_TYPES

    @staticmethod
    def validate_schema(data: Dict[str, Any], schema: Dict[str, Dict[str, Any]]) -> List[str]:
        """
        Validates a data dictionary against a provided schema.
        Returns a list of error messages (empty list if valid).
        """
        errors = []
        
        for key, prop_schema in schema.items():
            required = prop_schema.get("required", False)
            prop_type = prop_schema.get("type")
            prop_label = prop_schema.get("label", key) # Use label for error messages
            
            # Check if property is missing but required
            if required and key not in data:
                errors.append(f"Missing required property: {prop_label}")
                continue
            
            # Check type if property is present
            if key in data:
                value = data[key]
                if not JsonSchema._check_primitive_type(value, prop_type):
                    errors.append(f"Invalid type for property '{prop_label}'. Expected '{prop_type}', got '{type(value).__name__}'.")
                    continue
                    
                # Check for range constraints (min/max)
                if prop_type in ["int", "float"] and isinstance(value, (int, float)):
                    min_val = prop_schema.get("min")
                    max_val = prop_schema.get("max")
                    if min_val is not None and value < min_val:
                        errors.append(f"Value for '{prop_label}' ({value}) is less than minimum ({min_val}).")
                    if max_val is not None and value > max_val:
                        errors.append(f"Value for '{prop_label}' ({value}) is greater than maximum ({max_val}).")
                        
        return errors
        
    @staticmethod
    def _check_primitive_type(value: Any, type_str: str) -> bool:
        """Checks if a value conforms to a simplified schema type."""
        if type_str == "string":
            return isinstance(value, str)
        elif type_str == "int":
            return isinstance(value, int)
        elif type_str == "float":
            return isinstance(value, (float, int))
        elif type_str == "boolean":
            return isinstance(value, bool)
        
        # Complex Types (List/Tuple expected for serialization)
        elif type_str == "color":
            return isinstance(value, (list, tuple)) and len(value) in [3, 4] and all(isinstance(v, (int, float)) for v in value)
        elif type_str == "vector2":
            return isinstance(value, (list, tuple)) and len(value) == 2 and all(isinstance(v, (int, float)) for v in value)
        elif type_str == "vector3":
            return isinstance(value, (list, tuple)) and len(value) == 3 and all(isinstance(v, (int, float)) for v in value)
            
        # List-of-Primitives (used by PanelProperties for vectors/colors)
        elif type_str.endswith("_list"):
             return isinstance(value, (list, tuple)) and all(isinstance(v, (int, float)) for v in value)

        # Selector/Dropdown (String is the stored value)
        elif type_str in ["asset_selector", "uid_selector", "dropdown"]:
            return isinstance(value, str) or value is None # Nullable string
            
        # Generic List/Dict
        elif type_str == "list":
            return isinstance(value, list)
        elif type_str == "dict":
            return isinstance(value, dict)

        return False

    @staticmethod
    def describe_schema(schema: Dict[str, Dict[str, Any]]):
        """
        Formats a schema dictionary into a human-readable string (for documentation).
        """
        description = "--- Schema Description ---\n"
        for key, prop_schema in schema.items():
            prop_type = prop_schema.get("type", "unknown")
            prop_label = prop_schema.get("label", key)
            required = "[REQUIRED]" if prop_schema.get("required") else ""
            read_only = "[READ ONLY]" if prop_schema.get("read_only") else ""
            default = f"(Default: {prop_schema.get('default')})" if 'default' in prop_schema else ""
            
            line = f"- {prop_label} ({key}): {prop_type.upper()} {required} {read_only} {default}"
            description += line.strip() + "\n"
            
            tooltip = prop_schema.get("tooltip")
            if tooltip:
                description += f"  > {tooltip}\n"
                
            options = prop_schema.get("options")
            if prop_type == 'dropdown' and options:
                description += f"  > Options: {', '.join(options)}\n"
                
        return description