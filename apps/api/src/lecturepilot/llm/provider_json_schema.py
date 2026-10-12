"""Generate strict provider schemas from the validating boundary models."""

from copy import deepcopy


def provider_json_schema(model) -> dict:
    schema = model.model_json_schema()
    definitions = schema.pop("$defs", {})

    def expand(value):
        if isinstance(value, list):
            return [expand(item) for item in value]
        if not isinstance(value, dict):
            return value
        if "$ref" in value:
            reference = value["$ref"].removeprefix("#/$defs/")
            value = {
                **deepcopy(definitions[reference]),
                **{k: v for k, v in value.items() if k != "$ref"},
            }
        result = {
            key: expand(item) for key, item in value.items() if key not in {"title", "default"}
        }
        variants = result.get("anyOf", [])
        if len(variants) == 2 and {"type": "null"} in variants:
            concrete = next(item for item in variants if item != {"type": "null"})
            if "type" in concrete:
                result = {**concrete, **{k: v for k, v in result.items() if k != "anyOf"}}
                result["type"] = [concrete["type"], "null"]
                if "enum" in result:
                    result["enum"] = [*result["enum"], None]
                if "const" in result:
                    result["enum"] = [result.pop("const"), None]
        if result.get("type") in ("object", ["object", "null"]):
            result["additionalProperties"] = False
            result["required"] = list(result.get("properties", {}))
        return result

    return expand(schema)
