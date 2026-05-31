"""MCP server wrapping the Minecraft pixel art generator.

Provides a single tool: generate_mc_pixelart
"""

import json
import sys
import os

# Ensure project root is on the import path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from generate_mc_pixelart import (  # noqa: E402
    load_config,
    generate_mc_pixelart,
    AVAILABLE_MODELS,
    DEFAULT_MODEL,
)

TOOL_NAME = "generate_mc_pixelart"
TOOL_DESCRIPTION = (
    "Generate a Minecraft-style pixel art item icon using AI, "
    "remove solid-color background, and nearest-neighbor downscale to 64x64."
)


def _rpc_response(req_id, result):
    return {"jsonrpc": "2.0", "id": req_id, "result": result}


def _rpc_error(req_id, code, message):
    return {"jsonrpc": "2.0", "id": req_id, "error": {"code": code, "message": message}}


def _send(msg: dict) -> None:
    sys.stdout.write(json.dumps(msg, ensure_ascii=False) + "\n")
    sys.stdout.flush()


def handle_initialize(req_id: int | str, _params: dict) -> dict:
    return _rpc_response(req_id, {
        "protocolVersion": "2024-11-05",
        "capabilities": {"tools": {}},
        "serverInfo": {"name": "mc-pixelart-generator", "version": "1.0.0"},
    })


def handle_tools_list(req_id: int | str, _params: dict) -> dict:
    return _rpc_response(req_id, {
        "tools": [{
            "name": TOOL_NAME,
            "description": TOOL_DESCRIPTION,
            "inputSchema": {
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string",
                        "description": "Material/item name to generate, e.g. 'crystal wand', 'diamond sword'",
                    },
                    "save_path": {
                        "type": "string",
                        "description": "Directory path to save the generated PNG file",
                    },
                    "filename": {
                        "type": "string",
                        "description": "Output filename (e.g. 'crystal_wand.png'), defaults to mc_pixelart_<name>_64x64.png",
                    },
                    "prompt": {
                        "type": "string",
                        "description": "Custom description of the item to generate. If omitted, defaults to the item name combined with Minecraft pixel art style prompts.",
                    },
                },
                "required": ["name", "save_path"],
            },
        }]
    })


def handle_tools_call(req_id: int | str, params: dict) -> dict:
    tool_name = params.get("name", "")
    if tool_name != TOOL_NAME:
        return _rpc_error(req_id, -32601, f"Unknown tool: {tool_name}")

    args = params.get("arguments", {})
    item_name = args.get("name", "")
    save_path = args.get("save_path", "")
    filename = args.get("filename")  # optional
    prompt = args.get("prompt")  # optional custom prompt

    if not item_name:
        return _rpc_error(req_id, -32602, "Missing required parameter: 'name'")
    if not save_path:
        return _rpc_error(req_id, -32602, "Missing required parameter: 'save_path'")

    try:
        token, model = load_config()
        out_path = generate_mc_pixelart(token, model, item_name, save_path, filename, prompt)
        return _rpc_response(req_id, {
            "content": [{"type": "text", "text": f"Image saved to: {out_path}"}],
            "out_path": out_path,
        })
    except Exception as exc:
        return _rpc_error(req_id, -32000, str(exc))


ROUTES = {
    "initialize": handle_initialize,
    "tools/list": handle_tools_list,
    "tools/call": handle_tools_call,
}


def run():
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            msg = json.loads(line)
        except json.JSONDecodeError:
            continue

        req_id = msg.get("id")
        method = msg.get("method", "")
        params = msg.get("params", {})

        # Handle notifications (no id) — just acknowledge initialized
        if req_id is None:
            continue

        handler = ROUTES.get(method)
        if handler is None:
            _send(_rpc_error(req_id, -32601, f"Method not found: {method}"))
            continue

        _send(handler(req_id, params))


if __name__ == "__main__":
    run()
