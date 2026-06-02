"""MCP server wrapping the Minecraft pixel art generator.

Tools: generate_mc_pixelart, generate_mc_block, generate_mc_buff, generate_image_raw, rotate_pixel_art
"""

import json
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from generate_mc_pixelart import (  # noqa: E402
    load_config,
    generate_mc_pixelart,
    generate_mc_block,
    generate_mc_buff,
    generate_image_raw,
    rotate_pixel_art,
    SIZE_OPTIONS,
    BUFF_SIZE_OPTIONS,
    DEFAULT_SIZE,
    DEFAULT_BUFF_SIZE,
)

SIZE_DESC = f"Output size in pixels ({', '.join(str(s) for s in SIZE_OPTIONS)}). Default: "
BUFF_SIZE_DESC = f"Output size in pixels ({', '.join(str(s) for s in BUFF_SIZE_OPTIONS)}). Default: "

TOOLS = [
    {
        "name": "generate_mc_pixelart",
        "description": "Generate a Minecraft-style pixel art item icon using AI, remove solid-color background, and nearest-neighbor downscale. IMPORTANT: if the generated image has wrong orientation or direction, DO NOT regenerate — use rotate_pixel_art to fix it instead.",
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
                    "description": "Output filename, defaults to mc_pixelart_<name>_<size>x<size>.png",
                },
                "prompt": {
                    "type": "string",
                    "description": "Custom description of the item. If omitted, uses the name combined with Minecraft pixel art style prompts.",
                },
                "size": {
                    "type": "integer",
                    "description": SIZE_DESC + str(DEFAULT_SIZE) + ".",
                },
            },
            "required": ["name", "save_path"],
        },
    },
    {
        "name": "generate_mc_block",
        "description": "Generate a Minecraft-style block texture (top-down, tileable) using AI, remove solid-color background, and nearest-neighbor downscale. IMPORTANT: if the generated image has wrong orientation, DO NOT regenerate — use rotate_pixel_art to fix it instead.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "name": {
                    "type": "string",
                    "description": "Block name to generate, e.g. 'grass block', 'stone bricks', 'oak planks'",
                },
                "save_path": {
                    "type": "string",
                    "description": "Directory path to save the generated PNG file",
                },
                "filename": {
                    "type": "string",
                    "description": "Output filename, defaults to mc_block_<name>_<size>x<size>.png",
                },
                "prompt": {
                    "type": "string",
                    "description": "Custom description of the block texture. If omitted, uses the name combined with block texture style prompts.",
                },
                "size": {
                    "type": "integer",
                    "description": SIZE_DESC + str(DEFAULT_SIZE) + ".",
                },
            },
            "required": ["name", "save_path"],
        },
    },
    {
        "name": "generate_mc_buff",
        "description": "Generate a Minecraft-style status effect / buff icon using AI, then nearest-neighbor downscale. IMPORTANT: if the generated icon has wrong orientation, DO NOT regenerate — use rotate_pixel_art to fix it instead.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "name": {
                    "type": "string",
                    "description": "Buff/effect name, e.g. 'speed boost', 'strength', 'fire resistance'",
                },
                "save_path": {
                    "type": "string",
                    "description": "Directory path to save the generated PNG file",
                },
                "filename": {
                    "type": "string",
                    "description": "Output filename, defaults to mc_buff_<name>_<size>x<size>.png",
                },
                "prompt": {
                    "type": "string",
                    "description": "Custom description of the buff icon. If omitted, uses the name combined with buff icon style prompts.",
                },
                "size": {
                    "type": "integer",
                    "description": BUFF_SIZE_DESC + str(DEFAULT_BUFF_SIZE) + ".",
                },
                "keep_background": {
                    "type": "boolean",
                    "description": "Set to true to keep the AI-generated background. Default false (background removed).",
                },
            },
            "required": ["name", "save_path"],
        },
    },
    {
        "name": "generate_image_raw",
        "description": "Generate a raw AI image from a custom prompt. No Minecraft pixel-art style is applied — use this for general-purpose image generation (non-pixel art, photorealistic, illustrations, etc.).",
        "inputSchema": {
            "type": "object",
            "properties": {
                "prompt": {
                    "type": "string",
                    "description": "Custom image generation prompt (required). Describe exactly what you want.",
                },
                "save_path": {
                    "type": "string",
                    "description": "Directory path to save the generated PNG file",
                },
                "filename": {
                    "type": "string",
                    "description": "Output filename, defaults to image_raw.png",
                },
                "negative_prompt": {
                    "type": "string",
                    "description": "Negative prompt — what to avoid in the image.",
                },
                "image_size": {
                    "type": "string",
                    "description": "Image size in 'WxH' format. Auto-detected from model if not set.",
                },
            },
            "required": ["prompt", "save_path"],
        },
    },
    {
        "name": "rotate_pixel_art",
        "description": "Rotate an existing image then nearest-neighbor scale back to original size. This is the PREFERRED way to fix item orientation — use this instead of regenerating. For example: if a sword is horizontal but should be diagonal (bottom-left to top-right), rotate 45 degrees. If orientation is mirrored, rotate 90 degrees.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "input_path": {
                    "type": "string",
                    "description": "Absolute path to the image file to rotate",
                },
                "save_path": {
                    "type": "string",
                    "description": "Directory path to save the rotated image",
                },
                "filename": {
                    "type": "string",
                    "description": "Output filename, defaults to <original>_rot<angle>.png",
                },
                "angle": {
                    "type": "number",
                    "description": "Rotation angle in degrees (default 45). Positive = counter-clockwise.",
                },
            },
            "required": ["input_path", "save_path"],
        },
    },
]

TOOL_NAMES = {t["name"] for t in TOOLS}


def _rpc_response(req_id, result):
    return {"jsonrpc": "2.0", "id": req_id, "result": result}


def _rpc_error(req_id, code, message):
    return {"jsonrpc": "2.0", "id": req_id, "error": {"code": code, "message": message}}


def _send(msg: dict) -> None:
    sys.stdout.write(json.dumps(msg, ensure_ascii=False) + "\n")
    sys.stdout.flush()


def handle_initialize(req_id, _params):
    return _rpc_response(req_id, {
        "protocolVersion": "2024-11-05",
        "capabilities": {"tools": {}},
        "serverInfo": {"name": "mc-pixelart-generator", "version": "1.1.0"},
    })


def handle_tools_list(req_id, _params):
    return _rpc_response(req_id, {"tools": TOOLS})


def handle_tools_call(req_id, params):
    tool_name = params.get("name", "")
    if tool_name not in TOOL_NAMES:
        return _rpc_error(req_id, -32601, f"Unknown tool: {tool_name}")

    args = params.get("arguments", {})

    try:
        if tool_name == "rotate_pixel_art":
            input_path = args.get("input_path", "")
            save_path = args.get("save_path", "")
            if not input_path:
                return _rpc_error(req_id, -32602, "Missing required parameter: 'input_path'")
            if not save_path:
                return _rpc_error(req_id, -32602, "Missing required parameter: 'save_path'")
            out_path = rotate_pixel_art(
                input_path, save_path,
                args.get("filename"),
                float(args.get("angle", 45.0)),
            )
        elif tool_name == "generate_image_raw":
            prompt = args.get("prompt", "")
            save_path = args.get("save_path", "")
            if not prompt:
                return _rpc_error(req_id, -32602, "Missing required parameter: 'prompt'")
            if not save_path:
                return _rpc_error(req_id, -32602, "Missing required parameter: 'save_path'")
            token, model, img_size = load_config()
            image_size = args.get("image_size")
            out_path = generate_image_raw(
                token, model, prompt,
                args.get("negative_prompt", ""),
                save_path,
                args.get("filename"),
                image_size if image_size else img_size,
            )
        else:
            item_name = args.get("name", "")
            save_path = args.get("save_path", "")
            if not item_name:
                return _rpc_error(req_id, -32602, "Missing required parameter: 'name'")
            if not save_path:
                return _rpc_error(req_id, -32602, "Missing required parameter: 'save_path'")

            filename = args.get("filename")
            prompt = args.get("prompt")
            size = args.get("size")
            image_size = args.get("image_size")

            token, model, img_size = load_config()
            if image_size:
                img_size = image_size

            if tool_name == "generate_mc_block":
                out_path = generate_mc_block(token, model, item_name, save_path, filename, prompt,
                                              size if size else DEFAULT_SIZE, img_size)
            elif tool_name == "generate_mc_buff":
                out_path = generate_mc_buff(token, model, item_name, save_path, filename, prompt,
                                             size if size else DEFAULT_BUFF_SIZE,
                                             bool(args.get("keep_background", False)), img_size)
            else:
                out_path = generate_mc_pixelart(token, model, item_name, save_path, filename, prompt,
                                                 size if size else DEFAULT_SIZE, img_size)

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

        if req_id is None:
            continue

        handler = ROUTES.get(method)
        if handler is None:
            _send(_rpc_error(req_id, -32601, f"Method not found: {method}"))
            continue

        _send(handler(req_id, params))


if __name__ == "__main__":
    run()
