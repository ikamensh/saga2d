"""JSON / summary helpers for :class:`Scene`.

Kept as a sibling of ``scene.py`` so the ``Scene.summary()`` /
``Scene.summary_json()`` one-line dumps can never drift out of sync:
both go through the same canonical ``_component_to_json`` shape.
"""

from __future__ import annotations

from typing import Any


def _component_to_json(component: Any, include_bounds: bool = False) -> dict[str, Any]:
    """Convert a UI component to a JSON-serialisable dict.

    Recursive over children. The returned shape is stable enough for
    tooling to consume — debug overlays, snapshot tests, IDE plugins.
    Keys are omitted when not meaningful (no ``text_style`` key when
    the component has none), so a snapshot diff stays focused on
    actual differences.

    When *include_bounds* is ``True``, each node carries
    ``"bounds": [x, y, w, h]`` from the component's computed
    rectangle. Off by default because bounds depend on viewport
    size and so make snapshots resolution-coupled.
    """
    node: dict[str, Any] = {"type": type(component).__name__}

    if hasattr(component, "_text_rv"):
        rv = component._text_rv
        if getattr(rv, "is_reactive", False):
            node["text"] = {"reactive": True}
        else:
            node["text"] = {"reactive": False, "value": rv.value}

    if hasattr(component, "_value_rv"):
        rv = component._value_rv
        if getattr(rv, "is_reactive", False):
            node["value"] = {"reactive": True}
        else:
            node["value"] = {"reactive": False, "value": rv.value}

    text_style = getattr(component, "_text_style", None)
    if isinstance(text_style, str):
        node["text_style"] = text_style

    anchor = getattr(component, "_anchor", None)
    if anchor is not None:
        node["anchor"] = anchor.name

    margin = getattr(component, "_margin", 0)
    if margin:
        node["margin"] = margin

    if include_bounds:
        node["bounds"] = [
            getattr(component, "_computed_x", 0),
            getattr(component, "_computed_y", 0),
            getattr(component, "_computed_w", 0),
            getattr(component, "_computed_h", 0),
        ]

    children = getattr(component, "_children", None)
    if children:
        node["children"] = [
            _component_to_json(c, include_bounds=include_bounds)
            for c in children
        ]

    return node


def _describe_component(component: Any) -> str:
    """One-line human-readable description — format from the JSON node.

    Keeping a single canonical data shape (the JSON node) and formatting
    from it means :meth:`Scene.summary` and :meth:`Scene.summary_json`
    can never drift out of sync.
    """
    node = _component_to_json(component)
    return _format_node(node)


def _format_node(node: dict[str, Any]) -> str:
    """Render a ``_component_to_json`` node as the iter-20 one-line form."""
    cls = node["type"]
    parts: list[str] = []

    text = node.get("text")
    if text is not None:
        if text["reactive"]:
            parts.append("← callable")
        else:
            value = text["value"]
            parts.append(f'"{value}"' if value else '""')

    value = node.get("value")
    if value is not None:
        if value["reactive"]:
            parts.append("← callable")
        else:
            parts.append(f"value={value['value']}")

    if "text_style" in node:
        parts.append(f"text_style={node['text_style']}")
    if "anchor" in node:
        parts.append(f"anchor={node['anchor']}")
    if "margin" in node:
        parts.append(f"margin={node['margin']}")
    if "bounds" in node:
        x, y, w, h = node["bounds"]
        parts.append(f"bounds=[{x},{y} {w}x{h}]")

    if parts:
        return f"{cls} " + ", ".join(parts)
    return cls


def _walk_json_with_depth(node: dict[str, Any], depth: int = 0):
    """Depth-first walk over a JSON node's children, yielding
    ``(depth, node)`` pairs starting from direct children."""
    for child in node.get("children", []):
        yield (depth, child)
        yield from _walk_json_with_depth(child, depth + 1)
