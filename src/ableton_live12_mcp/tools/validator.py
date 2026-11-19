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


_NON_FINITE_STRINGS = frozenset({
    "nan",
    "+nan",
    "-nan",
    "inf",
    "+inf",
    "-inf",
    "infinity",
    "+infinity",
    "-infinity",
})


def _check_finite_scalar(val: Any, path: str) -> None:
    if isinstance(val, float) and (math.isnan(val) or math.isinf(val)):
        label = "NaN" if math.isnan(val) else "Inf"
        raise ValidationError(f"{path}: {label} is not a valid number")
    if isinstance(val, str) and val.strip().lower() in _NON_FINITE_STRINGS:
        raise ValidationError(f"{path}: non-finite string {val!r} is not allowed in parameter values")


def _check_finite_recursive(val: Any, path: str) -> None:
    _check_finite_scalar(val, path)
    if isinstance(val, list):
        for idx, item in enumerate(val):
            _check_finite_recursive(item, f"{path}[{idx}]")
    elif isinstance(val, dict):
        for k, v in val.items():
            _check_finite_recursive(v, f"{path}.{k}")


def _matches_json_type(val: Any, expected: str) -> bool:
    if expected == "integer":
        return isinstance(val, int) and not isinstance(val, bool)
    if expected == "number":
        return isinstance(val, (int, float)) and not isinstance(val, bool)
    if expected == "string":
        return isinstance(val, str)
    if expected == "boolean":
        return isinstance(val, bool)
    if expected == "null":
        return val is None
    if expected == "array":
        return isinstance(val, list)
    if expected == "object":
        return isinstance(val, dict)
    return True


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
    _check_finite_scalar(val, path)

    # anyOf (evaluated alongside sibling keywords per Draft-07)
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
            raise ValidationError(f"{path}: value {val!r} did not match any allowed schema in anyOf: {errors}")

    # oneOf (evaluated alongside sibling keywords per Draft-07)
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

    expected_type = schema.get("type")
    if isinstance(expected_type, list):
        if not any(_matches_json_type(val, t) for t in expected_type):
            raise ValidationError(f"{path}: expected type in {expected_type}, got {type(val).__name__}")
    elif isinstance(expected_type, str):
        if not _matches_json_type(val, expected_type):
            raise ValidationError(f"{path}: expected {expected_type}, got {type(val).__name__}")
    else:
        # Untyped schema without object/array structure still rejects nested non-finite values
        if isinstance(val, (list, dict)) and not any(
            k in schema for k in ("properties", "required", "additionalProperties", "items", "anyOf", "oneOf")
        ):
            _check_finite_recursive(val, path)

    if isinstance(val, str):
        if "minLength" in schema and len(val) < schema["minLength"]:
            raise ValidationError(f"{path}: string shorter than minLength {schema['minLength']}")
        if "maxLength" in schema and len(val) > schema["maxLength"]:
            raise ValidationError(f"{path}: string longer than maxLength {schema['maxLength']}")
    elif isinstance(val, list):
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
                    else:
                        _check_finite_recursive(item, f"{path}[{idx}]")
        else:
            for idx, item in enumerate(val):
                _check_finite_recursive(item, f"{path}[{idx}]")
    elif isinstance(val, dict):
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
            else:
                _check_finite_recursive(prop_val, f"{path}.{prop_key}")

    # Numeric Bounds
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
