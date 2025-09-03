from __future__ import annotations

"""A minimal, extensible registry for external developer tools.

Design goals:
- Lean: single small module, easy API (register, list, get schema, call).
- Extensible: supports decorator or programmatic registration.
- Useful for LLM tool schemas: can emit a JSON-schema-like parameters object.

The registry will try to auto-register functions found in `ai_toolbox.tool_utils`
if that module is importable.
"""

from dataclasses import dataclass
import inspect
import typing as t


@dataclass
class ToolDescriptor:
    name: str
    func: t.Callable
    description: str
    params_schema: dict


_REGISTRY: dict[str, ToolDescriptor] = {}


def _pytype_to_json_type(py: type) -> str:
    mapping = {
        str: "string",
        int: "integer",
        float: "number",
        bool: "boolean",
        list: "array",
        dict: "object",
    }
    return mapping.get(py, "string")


def _build_params_schema(func: t.Callable) -> dict:
    sig = inspect.signature(func)
    props: dict[str, dict] = {}
    required: list[str] = []
    for name, p in sig.parameters.items():
        # Skip VAR_POSITIONAL and VAR_KEYWORD for schema simplicity
        if p.kind in (p.VAR_POSITIONAL, p.VAR_KEYWORD):
            continue
        ann = (
            p.annotation
            if p.annotation is not inspect._empty
            else str
        )
        json_type = _pytype_to_json_type(
            ann if isinstance(ann, type) else str
        )
        prop: dict = {"type": json_type}
        if p.default is inspect._empty:
            required.append(name)
        else:
            # expose default for convenience
            prop["default"] = p.default
        props[name] = prop

    schema = {
        "type": "object",
        "properties": props,
    }
    if required:
        schema["required"] = required
    return schema


def register_tool(
    _func: t.Callable | None = None,
    *,
    name: str | None = None,
    description: str | None = None,
    params_schema: dict | None = None,
):
    """Decorator / programmatic registration for tools.

    Can be used as:
      @register_tool
      def foo(...):
          ...

    Or with metadata:
      @register_tool(name="foo", description="...", params_schema={...})
      def foo(...):
          ...
    """

    def _register(func: t.Callable) -> t.Callable:
        tool_name = name or func.__name__
        desc = description or (func.__doc__ or "").strip()
        schema = params_schema or _build_params_schema(func)
        _REGISTRY[tool_name] = ToolDescriptor(
            name=tool_name,
            func=func,
            description=desc,
            params_schema=schema,
        )
        return func

    if _func is None:
        return _register
    return _register(_func)


def list_tools() -> list[str]:
    return list(_REGISTRY.keys())


def get_tool(name: str) -> ToolDescriptor | None:
    return _REGISTRY.get(name)


def generate_tool_schema(name: str) -> dict | None:
    """Return a JSON-schema-like dict describing the tool's parameters.

    The returned dict contains: title, description, and parameters (object schema).
    """
    td = get_tool(name)
    if not td:
        return None
    return {
        "type": "function",
        "function": {
            "name": td.name,
            "description": td.description,
            "parameters": td.params_schema,
        },
    }


def generate_all_tool_schemas() -> list[dict]:
    """Return a list of tool schemas for all registered tools.

    Each item uses the same structure as `generate_tool_schema`.
    Useful to present the full tool list to an LLM.
    """
    schemas: list[dict] = []
    for name in list_tools():
        s = generate_tool_schema(name)
        if s is not None:
            schemas.append(s)
    return schemas


def call_tool(name: str, /, **kwargs):
    td = get_tool(name)
    if not td:
        raise KeyError(f"tool not found: {name}")
    return td.func(**kwargs)
