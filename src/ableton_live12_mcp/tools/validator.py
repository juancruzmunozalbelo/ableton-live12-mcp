"""
Pure Python stdlib JSON Schema Draft-07 Validator
=================================================
Validates incoming arguments dictionary against tool inputSchema in pure standard library.
"""

import math
from typing import Any, Dict, List, Optional


class ValidationError(ValueError):
    """Raised when tool arguments fail JSON schema validation."""
    pass


def validate_argument_dict(schema: Dict[str, Any], data: Dict[str, Any], path: str = "root") -> None:
    """Validates data dictionary against a Draft-07 object schema."""
    if not isinstance(data, dict):
        raise ValidationError(f"{path}: expected object, got {type(data).__name__}")

    obj_schema = dict(schema)
    if "type" not in obj_schema:
        obj_schema["type"] = "object"

    validate_value(obj_schema, data, path)


def validate_value(schema: Dict[str, Any], val: Any, path: str) -> None:
    """Validates an individual value against its schema specification."""
    # anyOf
    if "anyOf" in schema:
        matched = False
        errors: List[str] = []
        for sub_schema in schema["anyOf"]:
            try:
                validate_value(sub_schema, val, path)
                matched = True
                break
            except ValidationError as err:
                errors.append(str(err))
        if not matched:
            raise ValidationError(f"{path}: value {val!r} did not match any allowed type in anyOf: {errors}")
        return

    # oneOf
    if "oneOf" in schema:
        matches = 0
        errors: List[str] = []
        for sub_schema in schema["oneOf"]:
            try:
                validate_value(sub_schema, val, path)
                matches += 1
            except ValidationError as err:
                errors.append(str(err))
        if matches != 1:
            raise ValidationError(f"{path}: value {val!r} matched {matches} schemas in oneOf (expected 1): {errors}")
        return

    expected_type = schema.get("type")
    is_object_schema = expected_type == "object" or (
        expected_type is None and any(k in schema for k in ("properties", "required", "additionalProperties"))
    )

    if expected_type == "integer":
        if not isinstance(val, int) or isinstance(val, bool):
            raise ValidationError(f"{path}: expected integer, got {type(val).__name__}")
    elif expected_type == "number":
        if not isinstance(val, (int, float)) or isinstance(val, bool):
            raise ValidationError(f"{path}: expected number, got {type(val).__name__}")
        if isinstance(val, float) and math.isnan(val):
            raise ValidationError(f"{path}: NaN is not a valid number")
    elif expected_type == "string":
        if not isinstance(val, str):
            raise ValidationError(f"{path}: expected string, got {type(val).__name__}")
        if "minLength" in schema and len(val) < schema["minLength"]:
            raise ValidationError(f"{path}: string shorter than minLength {schema['minLength']}")
        if "maxLength" in schema and len(val) > schema["maxLength"]:
            raise ValidationError(f"{path}: string longer than maxLength {schema['maxLength']}")
    elif expected_type == "boolean":
        if not isinstance(val, bool):
            raise ValidationError(f"{path}: expected boolean, got {type(val).__name__}")
    elif expected_type == "null":
        if val is not None:
            raise ValidationError(f"{path}: expected null, got {type(val).__name__}")
    elif expected_type == "array":
        if not isinstance(val, list):
            raise ValidationError(f"{path}: expected array, got {type(val).__name__}")
        if "minItems" in schema and len(val) < schema["minItems"]:
            raise ValidationError(f"{path}: array has fewer items than minItems {schema['minItems']}")
        if "maxItems" in schema and len(val) > schema["maxItems"]:
            raise ValidationError(f"{path}: array has more items than maxItems {schema['maxItems']}")
        if "items" in schema:
            items_schema = schema["items"]
            if isinstance(items_schema, dict):
                for idx, item in enumerate(val):
                    validate_value(items_schema, item, f"{path}[{idx}]")
            elif isinstance(items_schema, list):
                for idx, item in enumerate(val):
                    if idx < len(items_schema):
                        validate_value(items_schema[idx], item, f"{path}[{idx}]")
    elif is_object_schema:
        if not isinstance(val, dict):
            raise ValidationError(f"{path}: expected object, got {type(val).__name__}")

        # Check required fields
        for req in schema.get("required", []):
            if req not in val:
                raise ValidationError(f"{path}: missing required parameter '{req}'")

        props = schema.get("properties", {})
        additional_props = schema.get("additionalProperties", True)

        for prop_key, prop_val in val.items():
            if prop_key in props:
                validate_value(props[prop_key], prop_val, f"{path}.{prop_key}")
            elif additional_props is False:
                raise ValidationError(f"{path}: unrecognized property '{prop_key}' (additionalProperties is False)")
            elif isinstance(additional_props, dict):
                validate_value(additional_props, prop_val, f"{path}.{prop_key}")
            # If additional_props is True or omitted, extra properties are allowed per Draft-07

    # Numeric Bounds
    if isinstance(val, float) and math.isnan(val):
        if any(k in schema for k in ("minimum", "maximum", "exclusiveMinimum", "exclusiveMaximum")):
            raise ValidationError(f"{path}: NaN is not a valid number")
    if "minimum" in schema:
        if isinstance(val, (int, float)) and not isinstance(val, bool):
            if val < schema["minimum"]:
                raise ValidationError(f"{path}: value {val} < minimum {schema['minimum']}")
    if "maximum" in schema:
        if isinstance(val, (int, float)) and not isinstance(val, bool):
            if val > schema["maximum"]:
                raise ValidationError(f"{path}: value {val} > maximum {schema['maximum']}")
    if "exclusiveMinimum" in schema:
        if isinstance(val, (int, float)) and not isinstance(val, bool):
            if val <= schema["exclusiveMinimum"]:
                raise ValidationError(f"{path}: value {val} <= exclusiveMinimum {schema['exclusiveMinimum']}")
    if "exclusiveMaximum" in schema:
        if isinstance(val, (int, float)) and not isinstance(val, bool):
            if val >= schema["exclusiveMaximum"]:
                raise ValidationError(f"{path}: value {val} >= exclusiveMaximum {schema['exclusiveMaximum']}")

    # Enums
    if "enum" in schema:
        matched = False
        for allowed in schema["enum"]:
            if val == allowed and type(val) is type(allowed):
                matched = True
                break
            if (
                isinstance(val, (int, float))
                and isinstance(allowed, (int, float))
                and not isinstance(val, bool)
                and not isinstance(allowed, bool)
            ):
                if val == allowed:
                    matched = True
                    break
        if not matched:
            raise ValidationError(f"{path}: value {val!r} not in allowed enum {schema['enum']}")
