"""MCP server wrapping the Minecraft pixel art generator.

Tools: 23 MCP tools — image generation, color analysis, wood/ore texture compositing, processing, file & OCR utilities
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
    composite_colorized,
    composite_layers,
    generate_ore_texture,
    colorize_template,
    colorize_template_pair,
    generate_sapling,
    analyze_image_colors,
    suggest_ore_colors,
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
        "name": "composite_colorized",
        "description": "Overlay colorized grayscale layers onto a base image. Useful for making ore textures (stone base + colored mineral highlights). Each overlay's luminance controls blend strength.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "base_path": {
                    "type": "string",
                    "description": "Absolute path to the base image (e.g. stone texture)",
                },
                "overlays": {
                    "type": "array",
                    "description": "List of overlay layers. Each has 'path' (grayscale overlay image) and 'color' (hex color to tint)",
                    "items": {
                        "type": "object",
                        "properties": {
                            "path": {"type": "string", "description": "Absolute path to grayscale overlay image"},
                            "color": {"type": "string", "description": "Hex color (e.g. '#FFD700' for gold)"},
                        },
                        "required": ["path", "color"],
                    },
                },
                "save_path": {
                    "type": "string",
                    "description": "Directory path to save the output image",
                },
                "filename": {
                    "type": "string",
                    "description": "Output filename, defaults to composite_output.png",
                },
            },
            "required": ["base_path", "overlays", "save_path"],
        },
    },
    {
        "name": "composite_layers",
        "description": "Stack and composite multiple image layers with optional per-layer colorization. First layer is the base. Each subsequent layer can be colorized from grayscale, tinted, or kept as-is. Supports blend modes: normal, multiply, screen, overlay. Ideal for building complex machine textures from separate material layers.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "layers": {
                    "type": "array",
                    "description": "List of layers, bottom to top. First layer is the base/background.",
                    "items": {
                        "type": "object",
                        "properties": {
                            "path": {"type": "string", "description": "Absolute path to layer image"},
                            "color": {"type": "string", "description": "Hex color to colorize grayscale pixels (e.g. '#FF4444'). Omit to keep original colors."},
                            "blend_mode": {"type": "string", "description": "Blend mode: normal (default), multiply, screen, overlay"},
                            "keep_rgb": {"type": "boolean", "description": "If true, tint the original RGB with the color instead of replacing with grayscale colorization. Default false."},
                        },
                        "required": ["path"],
                    },
                },
                "save_path": {
                    "type": "string",
                    "description": "Directory path to save the output image",
                },
                "filename": {
                    "type": "string",
                    "description": "Output filename, defaults to composite_layers.png",
                },
                "size": {
                    "type": "array",
                    "description": "Optional [width, height] canvas size. Defaults to first layer's size.",
                },
            },
            "required": ["layers", "save_path"],
        },
    },
    {
        "name": "generate_ore_texture",
        "description": "Generate a Minecraft ore texture by compositing a stone base with the ore overlay colorized to the given color. Auto-uses ore_background.png (or deepslate_ore_background.png if deepslate=true). A simplified ore generation — just pass a name and color.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "name": {
                    "type": "string",
                    "description": "Ore name (e.g. 'diamond', 'iron', 'lapis'). Used in default filename.",
                },
                "color": {
                    "type": "string",
                    "description": "Hex color for the ore (e.g. '#00FFFF' for diamond, '#FFD700' for gold).",
                },
                "save_path": {
                    "type": "string",
                    "description": "Directory path to save the output image",
                },
                "filename": {
                    "type": "string",
                    "description": "Output filename, defaults to ore_<name>.png (or deepslate_ore_<name>.png)",
                },
                "deepslate": {
                    "type": "boolean",
                    "description": "Use deepslate_ore_background.png instead of regular stone. Default false.",
                },
            },
            "required": ["name", "color", "save_path"],
        },
    },
    {
        "name": "generate_sapling",
        "description": "Generate a Minecraft sapling texture by compositing sapling_body.png and sapling_leaves.png, each independently colorized.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "name": {
                    "type": "string",
                    "description": "Wood/plant name (e.g. 'oak', 'birch', 'jungle'). Used in default filename.",
                },
                "body_color": {
                    "type": "string",
                    "description": "Hex color for the sapling body/stem (e.g. '#8B6914' for dark wood).",
                },
                "leaves_color": {
                    "type": "string",
                    "description": "Hex color for the leaves (e.g. '#228B22' for forest green).",
                },
                "save_path": {
                    "type": "string",
                    "description": "Directory path to save the output image",
                },
                "filename": {
                    "type": "string",
                    "description": "Output filename, defaults to sapling_<name>.png",
                },
            },
            "required": ["name", "body_color", "leaves_color", "save_path"],
        },
    },
    {
        "name": "generate_planks",
        "description": "Generate a Minecraft planks texture by colorizing the planks.png grayscale template.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "name": {
                    "type": "string",
                    "description": "Wood name (e.g. 'oak', 'spruce'). Used in default filename.",
                },
                "color": {
                    "type": "string",
                    "description": "Hex color for the planks (e.g. '#BC8F5A' for oak brown).",
                },
                "save_path": {
                    "type": "string",
                    "description": "Directory path to save the output image",
                },
                "filename": {
                    "type": "string",
                    "description": "Output filename, defaults to planks_<name>.png",
                },
            },
            "required": ["name", "color", "save_path"],
        },
    },
    {
        "name": "generate_log",
        "description": "Generate Minecraft log textures (side + top) by colorizing log.png and log_top.png templates.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "name": {
                    "type": "string",
                    "description": "Wood name (e.g. 'oak', 'birch'). Used in default filenames.",
                },
                "color": {
                    "type": "string",
                    "description": "Hex color for the log side (e.g. '#8B6914' for oak brown).",
                },
                "save_path": {
                    "type": "string",
                    "description": "Directory path to save the output images",
                },
                "filename": {
                    "type": "string",
                    "description": "Output filename for log side, defaults to log_<name>.png. Top gets _top suffix.",
                },
            },
            "required": ["name", "color", "save_path"],
        },
    },
    {
        "name": "generate_stripped_log",
        "description": "Generate Minecraft stripped log textures (side + top) by colorizing stripped_log.png and stripped_log_top.png templates.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "name": {
                    "type": "string",
                    "description": "Wood name (e.g. 'oak', 'birch'). Used in default filenames.",
                },
                "color": {
                    "type": "string",
                    "description": "Hex color for the stripped log (e.g. '#C4A35A' for stripped oak).",
                },
                "save_path": {
                    "type": "string",
                    "description": "Directory path to save the output images",
                },
                "filename": {
                    "type": "string",
                    "description": "Output filename for stripped log side, defaults to stripped_log_<name>.png.",
                },
            },
            "required": ["name", "color", "save_path"],
        },
    },
    {
        "name": "generate_leaves",
        "description": "Generate a Minecraft leaves texture by colorizing the leaves.png grayscale template.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "name": {
                    "type": "string",
                    "description": "Tree name (e.g. 'oak', 'spruce', 'jungle'). Used in default filename.",
                },
                "color": {
                    "type": "string",
                    "description": "Hex color for the leaves (e.g. '#228B22' for forest green).",
                },
                "save_path": {
                    "type": "string",
                    "description": "Directory path to save the output image",
                },
                "filename": {
                    "type": "string",
                    "description": "Output filename, defaults to leaves_<name>.png",
                },
            },
            "required": ["name", "color", "save_path"],
        },
    },
    {
        "name": "generate_door",
        "description": "Generate Minecraft door textures (top + bottom) by colorizing door_top.png and door_bottom.png templates.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "name": {
                    "type": "string",
                    "description": "Wood name (e.g. 'oak', 'iron'). Used in default filenames.",
                },
                "color": {
                    "type": "string",
                    "description": "Hex color for the door (e.g. '#8B6914' for oak brown).",
                },
                "save_path": {
                    "type": "string",
                    "description": "Directory path to save the output images",
                },
                "filename": {
                    "type": "string",
                    "description": "Output filename for door top, defaults to door_<name>_top.png. Bottom gets _bottom suffix.",
                },
            },
            "required": ["name", "color", "save_path"],
        },
    },
    {
        "name": "generate_trapdoor",
        "description": "Generate a Minecraft trapdoor texture by colorizing the trapdoor.png grayscale template.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "name": {
                    "type": "string",
                    "description": "Wood name (e.g. 'oak', 'iron'). Used in default filename.",
                },
                "color": {
                    "type": "string",
                    "description": "Hex color for the trapdoor (e.g. '#8B6914' for oak brown).",
                },
                "save_path": {
                    "type": "string",
                    "description": "Directory path to save the output image",
                },
                "filename": {
                    "type": "string",
                    "description": "Output filename, defaults to trapdoor_<name>.png",
                },
            },
            "required": ["name", "color", "save_path"],
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
    {
        "name": "analyze_image_colors",
        "description": "Analyze an image's color palette — extract dominant colors with hex values and coverage percentages. Optionally suggest the most vibrant colors for ore/texture generation. Use this to: 1) get a color scheme from an AI-generated item, 2) automatically pick the best colors for composite ores and wood textures.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "input_path": {
                    "type": "string",
                    "description": "Absolute path to the image to analyze",
                },
                "max_colors": {
                    "type": "integer",
                    "description": "Maximum number of dominant colors to extract. Default 6.",
                },
                "suggest_ores": {
                    "type": "boolean",
                    "description": "If true, also return suggested ore colors (top 3 most saturated hex values). Default false.",
                },
            },
            "required": ["input_path"],
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
        elif tool_name == "analyze_image_colors":
            input_path = args.get("input_path", "")
            if not input_path:
                return _rpc_error(req_id, -32602, "Missing required parameter: 'input_path'")
            analysis = analyze_image_colors(input_path, int(args.get("max_colors", 6)))
            result = {
                "analysis": analysis,
                "total_colors": len(analysis),
            }
            summary_lines = [f"Color analysis ({len(analysis)} dominant colors):"]
            for i, c in enumerate(analysis):
                pct = f"{c['coverage'] * 100:.0f}%"
                summary_lines.append(f"  {i + 1}. {c['hex']} — {pct}")
            if args.get("suggest_ores"):
                ore_colors = suggest_ore_colors(analysis)
                result["ore_suggestions"] = ore_colors
                summary_lines.append(f"\nSuggested ore colors: {', '.join(ore_colors)}")
            result["content"] = [{"type": "text", "text": "\n".join(summary_lines)}]
            return _rpc_response(req_id, result)
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
        elif tool_name == "composite_colorized":
            base_path = args.get("base_path", "")
            save_path = args.get("save_path", "")
            overlays = args.get("overlays", [])
            if not base_path or not save_path or not overlays:
                return _rpc_error(req_id, -32602, "Missing required parameters")
            out_path = composite_colorized(
                base_path, overlays, save_path,
                args.get("filename"),
            )
        elif tool_name == "composite_layers":
            layers = args.get("layers", [])
            save_path = args.get("save_path", "")
            if not layers or not save_path:
                return _rpc_error(req_id, -32602, "Missing required parameters")
            size = args.get("size")
            out_path = composite_layers(
                layers, save_path,
                tuple(size) if size else None,
                args.get("filename"),
            )
        elif tool_name == "generate_ore_texture":
            name = args.get("name", "")
            color = args.get("color", "")
            save_path = args.get("save_path", "")
            if not name or not color or not save_path:
                return _rpc_error(req_id, -32602, "Missing required parameters")
            out_path = generate_ore_texture(
                name, color, save_path,
                args.get("filename"),
                bool(args.get("deepslate", False)),
            )
        elif tool_name == "generate_sapling":
            name = args.get("name", "")
            body_color = args.get("body_color", "")
            leaves_color = args.get("leaves_color", "")
            save_path = args.get("save_path", "")
            if not name or not body_color or not leaves_color or not save_path:
                return _rpc_error(req_id, -32602, "Missing required parameters")
            out_path = generate_sapling(
                name, body_color, leaves_color, save_path,
                args.get("filename"),
            )
        elif tool_name == "generate_planks":
            name = args.get("name", "")
            color = args.get("color", "")
            save_path = args.get("save_path", "")
            if not name or not color or not save_path:
                return _rpc_error(req_id, -32602, "Missing required parameters")
            out_path = colorize_template("planks", color, save_path,
                                         args.get("filename") or f"planks_{name}.png")
        elif tool_name == "generate_log":
            name = args.get("name", "")
            color = args.get("color", "")
            save_path = args.get("save_path", "")
            if not name or not color or not save_path:
                return _rpc_error(req_id, -32602, "Missing required parameters")
            fn = args.get("filename")
            main_fn = fn if fn else f"log_{name}.png"
            top_fn = fn.replace(".png", "_top.png") if fn else f"log_{name}_top.png"
            main_path, top_path = colorize_template_pair(
                "log", "log_top", name, color, save_path, main_fn, top_fn)
            return _rpc_response(req_id, {
                "content": [{"type": "text", "text": f"Log side: {main_path}\nLog top: {top_path}"}],
                "out_path": main_path,
                "top_path": top_path,
            })
        elif tool_name == "generate_stripped_log":
            name = args.get("name", "")
            color = args.get("color", "")
            save_path = args.get("save_path", "")
            if not name or not color or not save_path:
                return _rpc_error(req_id, -32602, "Missing required parameters")
            fn = args.get("filename")
            main_fn = fn if fn else f"stripped_log_{name}.png"
            top_fn = fn.replace(".png", "_top.png") if fn else f"stripped_log_{name}_top.png"
            main_path, top_path = colorize_template_pair(
                "stripped_log", "stripped_log_top", name, color, save_path, main_fn, top_fn)
            return _rpc_response(req_id, {
                "content": [{"type": "text", "text": f"Stripped Log side: {main_path}\nStripped Log top: {top_path}"}],
                "out_path": main_path,
                "top_path": top_path,
            })
        elif tool_name == "generate_leaves":
            name = args.get("name", "")
            color = args.get("color", "")
            save_path = args.get("save_path", "")
            if not name or not color or not save_path:
                return _rpc_error(req_id, -32602, "Missing required parameters")
            out_path = colorize_template("leaves", color, save_path,
                                         args.get("filename") or f"leaves_{name}.png")
        elif tool_name == "generate_door":
            name = args.get("name", "")
            color = args.get("color", "")
            save_path = args.get("save_path", "")
            if not name or not color or not save_path:
                return _rpc_error(req_id, -32602, "Missing required parameters")
            fn = args.get("filename")
            top_fn = fn if fn else f"door_{name}_top.png"
            bottom_fn = fn.replace(".png", "_bottom.png") if fn else f"door_{name}_bottom.png"
            top_path, bottom_path = colorize_template_pair(
                "door_top", "door_bottom", name, color, save_path, top_fn, bottom_fn)
            return _rpc_response(req_id, {
                "content": [{"type": "text", "text": f"Door top: {top_path}\nDoor bottom: {bottom_path}"}],
                "out_path": top_path,
                "bottom_path": bottom_path,
            })
        elif tool_name == "generate_trapdoor":
            name = args.get("name", "")
            color = args.get("color", "")
            save_path = args.get("save_path", "")
            if not name or not color or not save_path:
                return _rpc_error(req_id, -32602, "Missing required parameters")
            out_path = colorize_template("trapdoor", color, save_path,
                                         args.get("filename") or f"trapdoor_{name}.png")
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
