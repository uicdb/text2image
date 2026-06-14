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
    generate_image_to_image,
    recolor_image,
    colorize_grayscale,
    pixelate_image,
    upload_file,
    list_files,
    image_ocr,
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
                "model": {
                    "type": "string",
                    "description": "Optional model override. Available: Kwai-Kolors/Kolors, Tongyi-MAI/Z-Image-Turbo.",
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
                "model": {
                    "type": "string",
                    "description": "Optional model override. Available: Kwai-Kolors/Kolors, Tongyi-MAI/Z-Image-Turbo.",
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
                "model": {
                    "type": "string",
                    "description": "Optional model override. Available: Kwai-Kolors/Kolors, Tongyi-MAI/Z-Image-Turbo.",
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
                "model": {
                    "type": "string",
                    "description": "Optional model override. Defaults to api_token.txt setting. Available: Kwai-Kolors/Kolors, Tongyi-MAI/Z-Image-Turbo.",
                },
            },
            "required": ["prompt", "save_path"],
        },
    },
    {
        "name": "generate_image_to_image",
        "description": "Generate an AI image based on a reference image URL plus a prompt. The reference image guides the composition/style while the prompt describes desired changes.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "prompt": {
                    "type": "string",
                    "description": "Prompt describing the desired output image",
                },
                "image_url": {
                    "type": "string",
                    "description": "Publicly accessible URL of the reference image to transform",
                },
                "save_path": {
                    "type": "string",
                    "description": "Directory path to save the generated PNG file",
                },
                "filename": {
                    "type": "string",
                    "description": "Output filename, defaults to image2image.png",
                },
                "negative_prompt": {
                    "type": "string",
                    "description": "Negative prompt — what to avoid in the image.",
                },
                "image_size": {
                    "type": "string",
                    "description": "Image size in 'WxH' format. Auto-detected from model if not set.",
                },
                "model": {
                    "type": "string",
                    "description": "Optional model override. Defaults to the model in api_token.txt. Available: Kwai-Kolors/Kolors, Tongyi-MAI/Z-Image-Turbo.",
                },
                "mc_style": {
                    "type": "boolean",
                    "description": "Set to true to apply Minecraft pixel-art styling and post-processing (background removal + 64x64 scaling).",
                },
            },
            "required": ["prompt", "image_url", "save_path"],
        },
    },
    {
        "name": "pixelate_image",
        "description": "Convert any image to Minecraft pixel-art style: remove solid background + nearest-neighbor scale to target size. No AI generation — pure image processing.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "input_path": {
                    "type": "string",
                    "description": "Absolute path to the source image",
                },
                "save_path": {
                    "type": "string",
                    "description": "Directory path to save the output image",
                },
                "filename": {
                    "type": "string",
                    "description": "Output filename, defaults to <original>_pixel_<size>x<size>.png",
                },
                "size": {
                    "type": "integer",
                    "description": "Output size in pixels (16, 32, 64, 128, 256, 1024). Default 64.",
                },
            },
            "required": ["input_path", "save_path"],
        },
    },
    {
        "name": "recolor_image",
        "description": "Recolor an image by replacing a specific color or applying a hue overlay. Useful for creating monster/item variants (e.g. turn a red sword blue, or recolor a green zombie to purple).",
        "inputSchema": {
            "type": "object",
            "properties": {
                "input_path": {
                    "type": "string",
                    "description": "Absolute path to the source image file",
                },
                "save_path": {
                    "type": "string",
                    "description": "Directory path to save the output image",
                },
                "color": {
                    "type": "string",
                    "description": "Target color in hex format (e.g. '#FF4444' for red)",
                },
                "from_color": {
                    "type": "string",
                    "description": "Source color to replace in hex format. If omitted, applies a color tint overlay to the entire image.",
                },
                "filename": {
                    "type": "string",
                    "description": "Output filename, defaults to <original>_recolor_<color>.png",
                },
                "tolerance": {
                    "type": "integer",
                    "description": "Color matching tolerance when from_color is specified (0-255). Default 60.",
                },
                "smooth": {
                    "type": "boolean",
                    "description": "If true, blend colors proportionally instead of hard replacement. Closer pixels shift more toward target; far pixels stay closer to original. Default false.",
                },
            },
            "required": ["input_path", "save_path", "color"],
        },
    },
    {
        "name": "colorize_grayscale",
        "description": "Colorize a grayscale image with a target color. Multiplies each pixel's luminance by the target color, creating a tinted variant.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "input_path": {
                    "type": "string",
                    "description": "Absolute path to the grayscale source image",
                },
                "save_path": {
                    "type": "string",
                    "description": "Directory path to save the output image",
                },
                "color": {
                    "type": "string",
                    "description": "Target color in hex format (e.g. '#3498DB' for blue)",
                },
                "filename": {
                    "type": "string",
                    "description": "Output filename, defaults to <original>_colorize_<color>.png",
                },
                "brightness": {
                    "type": "number",
                    "description": "Brightness multiplier. 1.0 = normal, 0.5 = darker, 1.5 = brighter. Default 1.0.",
                },
            },
            "required": ["input_path", "save_path", "color"],
        },
    },
    {
        "name": "upload_file",
        "description": "Upload a local file to SiliconFlow API. Returns file info including ID that can be used for batch processing or image-to-image reference.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "file_path": {
                    "type": "string",
                    "description": "Absolute path to the local file to upload",
                },
                "purpose": {
                    "type": "string",
                    "description": "File purpose, e.g. 'batch'. Default 'batch'.",
                },
            },
            "required": ["file_path"],
        },
    },
    {
        "name": "list_files",
        "description": "List all files uploaded to SiliconFlow API.",
        "inputSchema": {
            "type": "object",
            "properties": {},
        },
    },
    {
        "name": "image_ocr",
        "description": "Run OCR / visual question-answering on an image using DeepSeek-OCR. Provide an image URL and a question about it.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "image_url": {
                    "type": "string",
                    "description": "Publicly accessible URL of the image to analyze",
                },
                "prompt": {
                    "type": "string",
                    "description": "Question to ask about the image. Default: 'What\\'s in this image?'",
                },
                "max_tokens": {
                    "type": "integer",
                    "description": "Maximum tokens in response. Default 300.",
                },
            },
            "required": ["image_url"],
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
        elif tool_name == "pixelate_image":
            input_path = args.get("input_path", "")
            save_path = args.get("save_path", "")
            if not input_path or not save_path:
                return _rpc_error(req_id, -32602, "Missing required parameters")
            size = args.get("size", DEFAULT_SIZE)
            out_path = pixelate_image(
                input_path, save_path,
                int(size) if size else DEFAULT_SIZE,
                args.get("filename"),
            )
        elif tool_name == "recolor_image":
            input_path = args.get("input_path", "")
            save_path = args.get("save_path", "")
            color = args.get("color", "")
            if not input_path or not save_path or not color:
                return _rpc_error(req_id, -32602, "Missing required parameters")
            out_path = recolor_image(
                input_path, save_path, color,
                args.get("from_color"),
                args.get("filename"),
                int(args.get("tolerance", 60)),
                bool(args.get("smooth", False)),
            )
        elif tool_name == "colorize_grayscale":
            input_path = args.get("input_path", "")
            save_path = args.get("save_path", "")
            color = args.get("color", "")
            if not input_path or not save_path or not color:
                return _rpc_error(req_id, -32602, "Missing required parameters")
            out_path = colorize_grayscale(
                input_path, save_path, color,
                args.get("filename"),
                float(args.get("brightness", 1.0)),
            )
        elif tool_name == "upload_file":
            file_path = args.get("file_path", "")
            if not file_path:
                return _rpc_error(req_id, -32602, "Missing required parameter: 'file_path'")
            token, _, _ = load_config()
            result = upload_file(token, file_path, args.get("purpose", "batch"))
            return _rpc_response(req_id, {
                "content": [{"type": "text", "text": json.dumps(result, ensure_ascii=False)}],
                "file_info": result,
            })
        elif tool_name == "list_files":
            token, _, _ = load_config()
            result = list_files(token)
            return _rpc_response(req_id, {
                "content": [{"type": "text", "text": json.dumps(result, ensure_ascii=False)}],
                "files": result,
            })
        elif tool_name == "image_ocr":
            image_url = args.get("image_url", "")
            if not image_url:
                return _rpc_error(req_id, -32602, "Missing required parameter: 'image_url'")
            token, _, _ = load_config()
            text = image_ocr(
                token, image_url,
                args.get("prompt", "What's in this image?"),
                int(args.get("max_tokens", 300)),
            )
            return _rpc_response(req_id, {
                "content": [{"type": "text", "text": text}],
                "ocr_result": text,
            })
        elif tool_name == "generate_image_raw":
            prompt = args.get("prompt", "")
            save_path = args.get("save_path", "")
            if not prompt:
                return _rpc_error(req_id, -32602, "Missing required parameter: 'prompt'")
            if not save_path:
                return _rpc_error(req_id, -32602, "Missing required parameter: 'save_path'")
            token, model, img_size = load_config()
            if args.get("model"):
                model = args["model"]
            image_size = args.get("image_size")
            out_path = generate_image_raw(
                token, model, prompt,
                args.get("negative_prompt", ""),
                save_path,
                args.get("filename"),
                image_size if image_size else img_size,
            )
        elif tool_name == "generate_image_to_image":
            prompt = args.get("prompt", "")
            image_url = args.get("image_url", "")
            save_path = args.get("save_path", "")
            if not prompt:
                return _rpc_error(req_id, -32602, "Missing required parameter: 'prompt'")
            if not image_url:
                return _rpc_error(req_id, -32602, "Missing required parameter: 'image_url'")
            if not save_path:
                return _rpc_error(req_id, -32602, "Missing required parameter: 'save_path'")
            token, model, img_size = load_config()
            if args.get("model"):
                model = args["model"]
            image_size = args.get("image_size")
            out_path = generate_image_to_image(
                token, model, prompt, image_url,
                args.get("negative_prompt", ""),
                save_path,
                args.get("filename"),
                image_size if image_size else img_size,
                bool(args.get("mc_style", False)),
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
            if args.get("model"):
                model = args["model"]
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
