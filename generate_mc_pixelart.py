import requests
import base64
import os
import sys
import time
from io import BytesIO
from PIL import Image


TOKEN_FILE = os.path.join(os.path.dirname(__file__), "api_token.txt")
API_URL = "https://api.siliconflow.cn/v1/images/generations"
SIZE_OPTIONS = [16, 32, 64, 128, 256, 1024]
BUFF_SIZE_OPTIONS = [18, 36, 72, 144, 288, 324]
DEFAULT_SIZE = 64
DEFAULT_BUFF_SIZE = 72
AVAILABLE_MODELS = ["Kwai-Kolors/Kolors", "Tongyi-MAI/Z-Image-Turbo"]
FALLBACK_MODEL = "Tongyi-MAI/Z-Image-Turbo"
RATE_LIMIT_CALLS = 2
RATE_LIMIT_WINDOW = 65  # seconds, includes 5s tolerance over 60s

# ── Rate limiter ──
_model_timestamps: dict[str, list[float]] = {}


def _check_rate_and_switch(model: str) -> str:
    """Auto-switch to fallback model if the current model is rate-limited."""
    now = time.time()
    _model_timestamps.setdefault(model, [])
    # Clean old timestamps
    _model_timestamps[model] = [t for t in _model_timestamps[model]
                                  if now - t < RATE_LIMIT_WINDOW]
    if len(_model_timestamps[model]) >= RATE_LIMIT_CALLS:
        print(f"[Rate] {model} hit rate limit ({RATE_LIMIT_CALLS} calls in {RATE_LIMIT_WINDOW}s), "
              f"switching to {FALLBACK_MODEL}")
        return FALLBACK_MODEL
    return model


def _record_call(model: str) -> None:
    _model_timestamps.setdefault(model, []).append(time.time())
DEFAULT_MODEL = "Kwai-Kolors/Kolors"

# Model-specific recommended image sizes
MODEL_IMAGE_SIZES = {
    "Kwai-Kolors/Kolors": "1024x1024",
    "Tongyi-MAI/Z-Image-Turbo": "1328x1328",
}
DEFAULT_IMAGE_SIZE = "1024x1024"

# ── Item prompt (from tool/提示词.txt) ──
ITEM_POSITIVE = (
    "game texture map, Minecraft style, pixel art item icon, "
    "32x32 pixels, pixel art style, flat colors, no gradient, no shadow, "
    "flat vector art, no shading, no gradient, "
    "isolated on transparent background, game asset"
)
ITEM_NEGATIVE = (
    "photorealistic, 3D render, gradient, blurry, watermark, text, "
    "signature, character, background, shadow, depth"
)

# ── Block texture prompt ──
BLOCK_POSITIVE = (
    "Minecraft block texture, top-down view, tileable seamless pattern, "
    "32x32 pixels, pixel art style, flat colors, no gradient, no shadow, "
    "flat vector art, no shading, no perspective, no lighting, "
    "game texture atlas, isolated on transparent background, game asset"
)
BLOCK_NEGATIVE = (
    "photorealistic, 3D render, perspective, depth, gradient, blurry, "
    "watermark, text, signature, character, background, shadow, lighting, "
    "isometric, side view, angled view"
)

# ── Buff / status effect icon prompt ──
BUFF_POSITIVE = (
    "Minecraft status effect icon, buff potion effect symbol, "
    "18x18 pixel art, small minimalist icon, simple clean silhouette, "
    "flat colors, no gradient, no shadow, no detail, bold readable shape, "
    "flat vector art, no shading, "
    "isolated on transparent background, game UI asset"
)
BUFF_NEGATIVE = (
    "photorealistic, 3D render, gradient, blurry, watermark, text, "
    "signature, background, shadow, depth, complex, detailed, "
    "character, scene, multiple objects"
)


def load_config():
    """Load token and optional settings from api_token.txt.

    File format (one per line, # for comments):
        apikey=sk-your-api-key
        model=Kwai-Kolors/Kolors
        image_size=1024x1024   (optional, auto-detected if not set)
    """
    path = os.path.abspath(TOKEN_FILE)
    if not os.path.exists(path):
        print(f"[ERROR] Config file not found: {path}")
        print("Create api_token.txt with apikey= and model= entries.")
        sys.exit(1)

    token = None
    model = DEFAULT_MODEL
    image_size = None
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" not in line:
                continue
            key, _, value = line.partition("=")
            key = key.strip()
            value = value.strip()
            if key == "apikey":
                token = value
            elif key == "model":
                model = value
            elif key == "image_size":
                image_size = value

    if not token or token == "sk-your-api-key-here":
        print("[ERROR] Please set apikey= in api_token.txt")
        sys.exit(1)

    if model not in AVAILABLE_MODELS:
        print(f"[WARN] Unknown model '{model}', falling back to {DEFAULT_MODEL}")
        model = DEFAULT_MODEL

    if not image_size:
        image_size = MODEL_IMAGE_SIZES.get(model, DEFAULT_IMAGE_SIZE)

    return token, model, image_size


def generate_image(token: str, model: str, prompt: str,
                    style_positive: str = ITEM_POSITIVE,
                    style_negative: str = ITEM_NEGATIVE,
                    image_size: str = DEFAULT_IMAGE_SIZE) -> Image.Image:
    model = _check_rate_and_switch(model)
    payload = {
        "model": model,
        "prompt": f"{prompt}, {style_positive}",
        "negative_prompt": style_negative,
        "image_size": image_size,
        "batch_size": 1,
        "num_inference_steps": 20,
        "guidance_scale": 7.5,
    }
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }

    print(f"Generating image via SiliconFlow API (model={model}) ...")
    resp = requests.post(API_URL, json=payload, headers=headers, timeout=120)
    _record_call(model)
    resp.raise_for_status()
    data = resp.json()

    images = data.get("images", [])
    if not images:
        print("[ERROR] No images in response:", data)
        sys.exit(1)

    image_obj = images[0]

    # Try base64-encoded image first
    b64_str = image_obj.get("b64_json", "")
    if b64_str:
        if b64_str.startswith("data:"):
            b64_str = b64_str.split(",", 1)[1]
        img_bytes = base64.b64decode(b64_str)
        return Image.open(BytesIO(img_bytes)).convert("RGBA")

    # Otherwise download from URL
    url = image_obj.get("url", "")
    if url:
        print(f"Downloading image from: {url}")
        resp = requests.get(url, timeout=60)
        resp.raise_for_status()
        return Image.open(BytesIO(resp.content)).convert("RGBA")

    print("[ERROR] No image data in response:", image_obj)
    sys.exit(1)


def remove_solid_background(img: Image.Image, tolerance: int = 40) -> Image.Image:
    """Detect and remove a solid-color background by sampling all 4 edges.

    Samples pixels along the top, bottom, left, and right edges to detect the
    background color, then makes any similar pixel transparent.
    Handles gradient backgrounds better than corner-only sampling.
    """
    w, h = img.size
    pixels = img.load()
    edge_width = max(2, min(8, w // 8, h // 8))

    # Collect edge pixels (skip the corners to avoid content that touches edges)
    samples = []
    margin = edge_width * 2
    # Top & bottom edges
    for x in range(margin, w - margin):
        for d in range(edge_width):
            for pos in [(x, d), (x, h - 1 - d)]:
                r, g, b, a = pixels[pos[0], pos[1]]
                if a > 0:
                    samples.append((r, g, b))
    # Left & right edges
    for y in range(margin, h - margin):
        for d in range(edge_width):
            for pos in [(d, y), (w - 1 - d, y)]:
                r, g, b, a = pixels[pos[0], pos[1]]
                if a > 0:
                    samples.append((r, g, b))

    if len(samples) < 50:
        print("Background removal skipped (edges mostly transparent)")
        return img

    # Find the most common color cluster (simple median approach)
    samples.sort()
    median = samples[len(samples) // 2]
    bg_color = median

    # Check if edges are consistent enough
    distances = [(s[0] - bg_color[0]) ** 2 + (s[1] - bg_color[1]) ** 2 + (s[2] - bg_color[2]) ** 2
                 for s in samples]
    distances.sort()
    p90_dist = int(distances[int(len(distances) * 0.9)] ** 0.5)

    if p90_dist > 80:
        print(f"Background removal skipped (edges too varied, p90_dist={p90_dist})")
        return img

    # Use the 90th percentile + buffer as tolerance
    effective_tol = max(tolerance, p90_dist + 15)
    print(f"Removing background color ~RGB({bg_color[0]}, {bg_color[1]}, {bg_color[2]}) "
          f"[tolerance={effective_tol}, p90={p90_dist}]")

    tol_sq = effective_tol * effective_tol
    removed = 0
    for y in range(h):
        for x in range(w):
            r, g, b, a = pixels[x, y]
            if a == 0:
                continue
            dist = (r - bg_color[0]) ** 2 + (g - bg_color[1]) ** 2 + (b - bg_color[2]) ** 2
            if dist <= tol_sq:
                pixels[x, y] = (r, g, b, 0)
                removed += 1

    total = w * h
    print(f"Made {removed}/{total} pixels transparent ({removed * 100 // total}%)")
    return img


def _ensure_png_ext(filename: str) -> str:
    return filename if filename.endswith(".png") else f"{filename}.png"


def scale_pixel_art(img: Image.Image, size: tuple[int, int]) -> Image.Image:
    """Nearest-neighbor downscale to preserve pixel-art sharpness."""
    return img.resize(size, Image.NEAREST)


def generate_mc_pixelart(token: str, model: str, item: str,
                          save_path: str | None = None,
                          filename: str | None = None,
                          prompt: str | None = None,
                          size: int = DEFAULT_SIZE,
                          image_size: str | None = None) -> str:
    """Generate a Minecraft pixel art item icon and save to disk.

    Returns the absolute path to the saved file.
    """
    if prompt:
        full_prompt = prompt
    else:
        full_prompt = item
    img_size = image_size or MODEL_IMAGE_SIZES.get(model, DEFAULT_IMAGE_SIZE)

    img = generate_image(token, model, full_prompt, ITEM_POSITIVE, ITEM_NEGATIVE, img_size)

    img = remove_solid_background(img)
    scaled = scale_pixel_art(img, (size, size))

    out_dir = save_path if save_path else os.path.dirname(__file__)
    os.makedirs(out_dir, exist_ok=True)
    out_name = _ensure_png_ext(filename) if filename else f"mc_pixelart_{item.replace(' ', '_')}_{size}x{size}.png"
    out_path = os.path.join(out_dir, out_name)

    scaled.save(out_path, "PNG")
    return os.path.abspath(out_path)


def generate_mc_block(token: str, model: str, name: str,
                       save_path: str | None = None,
                       filename: str | None = None,
                       prompt: str | None = None,
                       size: int = DEFAULT_SIZE,
                       image_size: str | None = None) -> str:
    """Generate a Minecraft block texture and save to disk.

    Returns the absolute path to the saved file.
    """
    if prompt:
        full_prompt = prompt
    else:
        full_prompt = name
    img_size = image_size or MODEL_IMAGE_SIZES.get(model, DEFAULT_IMAGE_SIZE)

    img = generate_image(token, model, full_prompt, BLOCK_POSITIVE, BLOCK_NEGATIVE, img_size)

    img = remove_solid_background(img)
    scaled = scale_pixel_art(img, (size, size))

    out_dir = save_path if save_path else os.path.dirname(__file__)
    os.makedirs(out_dir, exist_ok=True)
    out_name = _ensure_png_ext(filename) if filename else f"mc_block_{name.replace(' ', '_')}_{size}x{size}.png"
    out_path = os.path.join(out_dir, out_name)

    scaled.save(out_path, "PNG")
    return os.path.abspath(out_path)


def generate_mc_buff(token: str, model: str, name: str,
                      save_path: str | None = None,
                      filename: str | None = None,
                      prompt: str | None = None,
                      size: int = DEFAULT_BUFF_SIZE,
                      keep_background: bool = False,
                      image_size: str | None = None) -> str:
    """Generate a Minecraft buff/status effect icon and save to disk.

    Returns the absolute path to the saved file.
    """
    if prompt:
        full_prompt = prompt
    else:
        full_prompt = name
    img_size = image_size or MODEL_IMAGE_SIZES.get(model, DEFAULT_IMAGE_SIZE)

    img = generate_image(token, model, full_prompt, BUFF_POSITIVE, BUFF_NEGATIVE, img_size)

    if not keep_background:
        img = remove_solid_background(img)
    scaled = scale_pixel_art(img, (size, size))

    out_dir = save_path if save_path else os.path.dirname(__file__)
    os.makedirs(out_dir, exist_ok=True)
    out_name = _ensure_png_ext(filename) if filename else f"mc_buff_{name.replace(' ', '_')}_{size}x{size}.png"
    out_path = os.path.join(out_dir, out_name)

    scaled.save(out_path, "PNG")
    return os.path.abspath(out_path)


def _download_api_image(data: dict) -> Image.Image:
    """Extract and download an image from a SiliconFlow API response."""
    images = data.get("images", [])
    if not images:
        print("[ERROR] No images in response:", data)
        sys.exit(1)
    image_obj = images[0]
    b64_str = image_obj.get("b64_json", "")
    if b64_str:
        if b64_str.startswith("data:"):
            b64_str = b64_str.split(",", 1)[1]
        return Image.open(BytesIO(base64.b64decode(b64_str))).convert("RGBA")
    url = image_obj.get("url", "")
    if url:
        print(f"Downloading image from: {url}")
        resp = requests.get(url, timeout=60)
        resp.raise_for_status()
        return Image.open(BytesIO(resp.content)).convert("RGBA")
    print("[ERROR] No image data in response:", image_obj)
    sys.exit(1)


def generate_image_raw(token: str, model: str, prompt: str, negative: str = "",
                         save_path: str | None = None,
                         filename: str | None = None,
                         image_size: str | None = None) -> str:
    """Generate a raw AI image without any pixel-art style prompts or post-processing.

    Returns the absolute path to the saved file.
    """
    model = _check_rate_and_switch(model)
    img_size = image_size or MODEL_IMAGE_SIZES.get(model, DEFAULT_IMAGE_SIZE)
    payload = {
        "model": model,
        "prompt": prompt,
        "negative_prompt": negative,
        "image_size": img_size,
        "batch_size": 1,
        "num_inference_steps": 20,
        "guidance_scale": 7.5,
    }
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }
    print(f"Generating raw image via SiliconFlow API (model={model}) ...")
    resp = requests.post(API_URL, json=payload, headers=headers, timeout=120)
    _record_call(model)
    resp.raise_for_status()
    data = resp.json()

    images = data.get("images", [])
    if not images:
        print("[ERROR] No images in response:", data)
        sys.exit(1)

    image_obj = images[0]
    b64_str = image_obj.get("b64_json", "")
    if b64_str:
        if b64_str.startswith("data:"):
            b64_str = b64_str.split(",", 1)[1]
        img = Image.open(BytesIO(base64.b64decode(b64_str))).convert("RGBA")
    else:
        url = image_obj.get("url", "")
        if not url:
            print("[ERROR] No image data in response:", image_obj)
            sys.exit(1)
        print(f"Downloading image from: {url}")
        resp = requests.get(url, timeout=60)
        resp.raise_for_status()
        img = Image.open(BytesIO(resp.content)).convert("RGBA")

    out_dir = save_path if save_path else os.path.dirname(__file__)
    os.makedirs(out_dir, exist_ok=True)
    out_name = _ensure_png_ext(filename) if filename else "image_raw.png"
    out_path = os.path.join(out_dir, out_name)
    img.save(out_path, "PNG")
    return os.path.abspath(out_path)


def generate_image_to_image(token: str, model: str, prompt: str, image_url: str,
                             negative: str = "", save_path: str | None = None,
                             filename: str | None = None,
                             image_size: str | None = None,
                             mc_style: bool = False) -> str:
    """Generate an AI image based on a reference image and prompt.

    Args:
        image_url: URL of the reference image. Must be a publicly accessible URL.
        mc_style: If True, append Minecraft pixel-art style prompts and post-process.

    Returns the absolute path to the saved file.
    """
    model = _check_rate_and_switch(model)
    img_size = image_size or MODEL_IMAGE_SIZES.get(model, DEFAULT_IMAGE_SIZE)
    full_prompt = prompt
    full_negative = negative
    if mc_style:
        full_prompt = f"{prompt}, {ITEM_POSITIVE}"
        full_negative = f"{negative}, {ITEM_NEGATIVE}" if negative else ITEM_NEGATIVE

    payload = {
        "model": model,
        "prompt": full_prompt,
        "negative_prompt": full_negative,
        "image": image_url,
        "image_size": img_size,
        "batch_size": 1,
        "num_inference_steps": 20,
        "guidance_scale": 7.5,
    }
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }
    print(f"Generating image-to-image via SiliconFlow API (model={model}) ...")
    resp = requests.post(API_URL, json=payload, headers=headers, timeout=120)
    _record_call(model)
    resp.raise_for_status()
    data = resp.json()

    img = _download_api_image(data)
    if mc_style:
        img = remove_solid_background(img)
        img = scale_pixel_art(img, (DEFAULT_SIZE, DEFAULT_SIZE))

    out_dir = save_path if save_path else os.path.dirname(__file__)
    os.makedirs(out_dir, exist_ok=True)
    out_name = _ensure_png_ext(filename) if filename else "image2image.png"
    out_path = os.path.join(out_dir, out_name)
    img.save(out_path, "PNG")
    return os.path.abspath(out_path)


def composite_colorized(base_path: str, overlays: list[dict], save_path: str,
                        filename: str | None = None) -> str:
    """Overlay colorized grayscale layers onto a base image.

    Each overlay dict: {'path': str, 'color': '#hex'}
    The overlay image's luminance controls blending strength —
    brighter pixels apply more of the target color.

    Returns the absolute path to the saved file.
    """
    base = Image.open(base_path).convert("RGBA")
    bw, bh = base.size

    for ol in overlays:
        ov_path = ol["path"]
        color = ol["color"]
        target_r = int(color[1:3], 16)
        target_g = int(color[3:5], 16)
        target_b = int(color[5:7], 16)

        overlay = Image.open(ov_path).convert("RGBA")
        if overlay.size != (bw, bh):
            overlay = overlay.resize((bw, bh), Image.NEAREST)

        op = overlay.load()
        bp = base.load()
        for y in range(bh):
            for x in range(bw):
                or_, og, ob, oa = op[x, y]
                if oa == 0:
                    continue
                # Use grayscale luminance + overlay alpha as blend factor
                lum = (0.299 * or_ + 0.587 * og + 0.114 * ob) / 255.0
                blend = min(1.0, lum * (oa / 255.0))
                if blend < 0.01:
                    continue
                br, bg, bb, ba = bp[x, y]
                # Overlay alpha wins: ore paints over transparent base areas too
                out_a = max(ba, oa)
                nr = int(br * (1 - blend) + target_r * blend)
                ng = int(bg * (1 - blend) + target_g * blend)
                nb = int(bb * (1 - blend) + target_b * blend)
                bp[x, y] = (nr, ng, nb, out_a)

        print(f"  Composited {os.path.basename(ov_path)} with {color}")

    out_dir = save_path
    os.makedirs(out_dir, exist_ok=True)
    out_name = _ensure_png_ext(filename) if filename else "composite_output.png"
    out_path = os.path.join(out_dir, out_name)
    base.save(out_path, "PNG")
    return os.path.abspath(out_path)


def composite_layers(layers: list[dict], save_path: str,
                      size: tuple[int, int] | None = None,
                      filename: str | None = None) -> str:
    """Stack and composite multiple image layers with optional per-layer colorization.

    Each layer dict:
        path:       str   — image file path
        color:      str   — hex color to tint grayscale pixels (optional)
        blend_mode: str   — 'normal' (default), 'multiply', 'screen', 'overlay'
        keep_rgb:   bool  — if True, keep original RGB even when color is set
                             (colorize only areas where original pixels are not transparent)

    The first layer determines canvas size (unless size is given).
    Layers stack bottom-to-top. Colorized layers use luminance-weighted
    blending — brighter pixels apply more of the target color.

    Returns the absolute path to the saved file.
    """
    if not layers:
        raise ValueError("At least one layer required")

    # Determine canvas size from first layer
    first = Image.open(layers[0]["path"]).convert("RGBA")
    canvas_size = size if size else first.size
    canvas = Image.new("RGBA", canvas_size, (0, 0, 0, 0))
    if first.size != canvas_size:
        first = first.resize(canvas_size, Image.NEAREST)
    fp = first.load()
    cp = canvas.load()
    for y in range(canvas_size[1]):
        for x in range(canvas_size[0]):
            r, g, b, a = fp[x, y]
            if a > 0:
                cp[x, y] = (r, g, b, a)
    print(f"  Layer 1 (base): {os.path.basename(layers[0]['path'])}")

    # Stack remaining layers
    for i, layer in enumerate(layers[1:], start=2):
        img = Image.open(layer["path"]).convert("RGBA")
        if img.size != canvas_size:
            img = img.resize(canvas_size, Image.NEAREST)
        color = layer.get("color")
        blend_mode = layer.get("blend_mode", "normal")
        keep_rgb = layer.get("keep_rgb", False)

        ip = img.load()
        for y in range(canvas_size[1]):
            for x in range(canvas_size[0]):
                ir, ig, ib, ia = ip[x, y]
                if ia == 0:
                    continue
                cr, cg, cb, ca = cp[x, y]

                if color and not keep_rgb:
                    # Colorize grayscale overlay
                    tr = int(color[1:3], 16)
                    tg = int(color[3:5], 16)
                    tb = int(color[5:7], 16)
                    lum = (0.299 * ir + 0.587 * ig + 0.114 * ib) / 255.0
                    blend = min(1.0, lum * (ia / 255.0))
                    if blend < 0.01:
                        continue
                    nr = int(cr * (1 - blend) + tr * blend)
                    ng = int(cg * (1 - blend) + tg * blend)
                    nb = int(cb * (1 - blend) + tb * blend)
                elif color and keep_rgb:
                    # Tint only: mix target color with original RGB
                    tr = int(color[1:3], 16)
                    tg = int(color[3:5], 16)
                    tb = int(color[5:7], 16)
                    blend = ia / 255.0
                    nr = int(ir * (1 - blend * 0.5) + tr * blend * 0.5)
                    ng = int(ig * (1 - blend * 0.5) + tg * blend * 0.5)
                    nb = int(ib * (1 - blend * 0.5) + tb * blend * 0.5)
                else:
                    nr, ng, nb = ir, ig, ib

                if blend_mode == "multiply":
                    nr = int(cr * nr / 255)
                    ng = int(cg * ng / 255)
                    nb = int(cb * nb / 255)
                elif blend_mode == "screen":
                    nr = 255 - int((255 - cr) * (255 - nr) / 255)
                    ng = 255 - int((255 - cg) * (255 - ng) / 255)
                    nb = 255 - int((255 - cb) * (255 - nb) / 255)
                elif blend_mode == "overlay":
                    nr = int(cr * cr / 255 * 2) if cr < 128 else 255 - int((255 - cr) * (255 - cr) / 255 * 2)
                    ng = int(cg * cg / 255 * 2) if cg < 128 else 255 - int((255 - cg) * (255 - cg) / 255 * 2)
                    nb = int(cb * cb / 255 * 2) if cb < 128 else 255 - int((255 - cb) * (255 - cb) / 255 * 2)
                    nr = int(nr * 0.5 + nr * 0.5)
                    ng = int(ng * 0.5 + ng * 0.5)
                    nb = int(nb * 0.5 + nb * 0.5)

                out_a = max(ca, ia)
                cp[x, y] = (nr, ng, nb, out_a)

        parts = [os.path.basename(layer['path'])]
        if color:
            parts.append(color)
        if blend_mode != "normal":
            parts.append(blend_mode)
        print(f"  Layer {i}: {' | '.join(parts)}")

    out_dir = save_path
    os.makedirs(out_dir, exist_ok=True)
    out_name = _ensure_png_ext(filename) if filename else "composite_layers.png"
    out_path = os.path.join(out_dir, out_name)
    canvas.save(out_path, "PNG")
    return os.path.abspath(out_path)


def pixelate_image(input_path: str, save_path: str,
                    size: int = DEFAULT_SIZE,
                    filename: str | None = None) -> str:
    """Convert any image to Minecraft pixel-art style.

    Applies background removal + nearest-neighbor downscale, exactly like
    the post-processing pipeline used by generate_mc_pixelart, but
    without calling the AI generation API.

    Returns the absolute path to the saved file.
    """
    img = Image.open(input_path).convert("RGBA")
    img = remove_solid_background(img)
    scaled = scale_pixel_art(img, (size, size))

    out_dir = save_path
    os.makedirs(out_dir, exist_ok=True)
    base = os.path.splitext(os.path.basename(input_path))[0]
    out_name = _ensure_png_ext(filename) if filename else f"{base}_pixel_{size}x{size}.png"
    out_path = os.path.join(out_dir, out_name)
    scaled.save(out_path, "PNG")
    return os.path.abspath(out_path)


def recolor_image(input_path: str, save_path: str, color: str,
                    from_color: str | None = None,
                    filename: str | None = None,
                    tolerance: int = 60,
                    smooth: bool = False) -> str:
    """Replace one color with another, or shift the hue of the entire image.

    Args:
        input_path: Path to the source image.
        color: Target color in hex format (e.g. '#FF4444'). If from_color is
               omitted, applies a hue shift toward this color to all pixels.
        from_color: Source color to replace (hex). If specified, only pixels
                    matching this color (within tolerance) are changed.
        tolerance: Euclidean distance tolerance for from_color matching.
        smooth: If True, blend proportionally rather than hard replace.
                Pixels closer to from_color shift more toward color;
                pixels at tolerance distance stay unchanged.
    """
    img = Image.open(input_path).convert("RGBA")
    target_r = int(color[1:3], 16)
    target_g = int(color[3:5], 16)
    target_b = int(color[5:7], 16)

    if from_color:
        src_r = int(from_color[1:3], 16)
        src_g = int(from_color[3:5], 16)
        src_b = int(from_color[5:7], 16)
        tol_sq = tolerance * tolerance
        pixels = img.load()
        changed = 0
        for y in range(img.height):
            for x in range(img.width):
                r, g, b, a = pixels[x, y]
                if a == 0:
                    continue
                dist = (r - src_r) ** 2 + (g - src_g) ** 2 + (b - src_b) ** 2
                if dist <= tol_sq:
                    if smooth:
                        # Proportional blend: closer pixels shift more
                        t = 1.0 - (dist / tol_sq) ** 0.5  # 0=far, 1=exact match
                        nr = int(r + (target_r - r) * t)
                        ng = int(g + (target_g - g) * t)
                        nb = int(b + (target_b - b) * t)
                    else:
                        nr, ng, nb = target_r, target_g, target_b
                    pixels[x, y] = (nr, ng, nb, a)
                    changed += 1
        print(f"Recolored {changed} pixels from {from_color} -> {color}" +
              (" (smooth)" if smooth else ""))
    else:
        # Hue overlay mode: blend target color based on pixel luminance
        pixels = img.load()
        for y in range(img.height):
            for x in range(img.width):
                r, g, b, a = pixels[x, y]
                if a == 0:
                    continue
                lum = int(0.299 * r + 0.587 * g + 0.114 * b)
                nr = min(255, int(target_r * lum / 255 * 2))
                ng = min(255, int(target_g * lum / 255 * 2))
                nb = min(255, int(target_b * lum / 255 * 2))
                nr = min(255, max(0, nr + (lum - 128)))
                ng = min(255, max(0, ng + (lum - 128)))
                nb = min(255, max(0, nb + (lum - 128)))
                pixels[x, y] = (nr, ng, nb, a)
        print(f"Applied hue overlay color {color}")

    out_dir = save_path
    os.makedirs(out_dir, exist_ok=True)
    base = os.path.splitext(os.path.basename(input_path))[0]
    tag = from_color.replace("#", "") if from_color else "hue"
    out_name = _ensure_png_ext(filename) if filename else f"{base}_recolor_{tag}_{color.replace('#', '')}.png"
    out_path = os.path.join(out_dir, out_name)
    img.save(out_path, "PNG")
    return os.path.abspath(out_path)


def colorize_grayscale(input_path: str, save_path: str, color: str,
                       filename: str | None = None,
                       brightness: float = 1.0) -> str:
    """Colorize a grayscale image with a target color.

    Multiplies each pixel's luminance by the target color, producing a
    tinted version while preserving the original brightness variation.

    Args:
        input_path: Path to the grayscale source image.
        color: Target color in hex format (e.g. '#FF4444').
        brightness: Output brightness multiplier (0.5 = darker, 1.5 = brighter).
    """
    img = Image.open(input_path).convert("RGBA")
    target_r = int(color[1:3], 16)
    target_g = int(color[3:5], 16)
    target_b = int(color[5:7], 16)

    pixels = img.load()
    for y in range(img.height):
        for x in range(img.width):
            r, g, b, a = pixels[x, y]
            if a == 0:
                continue
            lum = (0.299 * r + 0.587 * g + 0.114 * b) / 255.0
            nr = min(255, int(target_r * lum * brightness))
            ng = min(255, int(target_g * lum * brightness))
            nb = min(255, int(target_b * lum * brightness))
            pixels[x, y] = (nr, ng, nb, a)

    out_dir = save_path
    os.makedirs(out_dir, exist_ok=True)
    base = os.path.splitext(os.path.basename(input_path))[0]
    out_name = _ensure_png_ext(filename) if filename else f"{base}_colorize_{color.replace('#', '')}.png"
    out_path = os.path.join(out_dir, out_name)
    img.save(out_path, "PNG")
    print(f"Colorized with {color} (brightness={brightness})")
    return os.path.abspath(out_path)


# ── Utility: file upload / list / OCR ──

def upload_file(token: str, file_path: str, purpose: str = "batch") -> dict:
    """Upload a file to SiliconFlow and return the file info (id, filename, etc.)."""
    url = "https://api.siliconflow.cn/v1/files"
    headers = {"Authorization": f"Bearer {token}"}
    with open(file_path, "rb") as f:
        files = {"file": (os.path.basename(file_path), f)}
        data = {"purpose": purpose}
        resp = requests.post(url, headers=headers, data=data, files=files, timeout=60)
    resp.raise_for_status()
    return resp.json()


def list_files(token: str) -> list:
    """List all uploaded files on SiliconFlow."""
    url = "https://api.siliconflow.cn/v1/files"
    headers = {"Authorization": f"Bearer {token}"}
    resp = requests.get(url, headers=headers, timeout=30)
    resp.raise_for_status()
    result = resp.json()
    return result.get("data", result) if isinstance(result, dict) else result


def image_ocr(token: str, image_url: str, prompt: str = "What's in this image?",
               max_tokens: int = 300) -> str:
    """Run OCR / visual Q&A on an image using DeepSeek-OCR.

    Args:
        image_url: Publicly accessible URL of the image to analyze.
        prompt: Question to ask about the image.
    Returns the model's text response.
    """
    from openai import OpenAI
    client = OpenAI(
        api_key=token,
        base_url="https://api.siliconflow.cn/v1",
    )
    resp = client.chat.completions.create(
        model="deepseek-ai/DeepSeek-OCR",
        messages=[{
            "role": "user",
            "content": [
                {"type": "text", "text": prompt},
                {"type": "image_url", "image_url": {"url": image_url}},
            ],
        }],
        max_tokens=max_tokens,
    )
    return resp.choices[0].message.content or ""


def rotate_pixel_art(input_path: str, save_path: str,
                      filename: str | None = None,
                      angle: float = 45.0) -> str:
    """Rotate an image then scale back to original size using NEAREST.

    Useful for fixing item orientation (e.g. making a horizontal sword diagonal).
    Returns the absolute path to the saved file.
    """
    img = Image.open(input_path).convert("RGBA")
    orig_size = img.size

    # Rotate with expand so content is not cropped
    rotated = img.rotate(angle, resample=Image.NEAREST, expand=True)

    # Scale back to original dimensions, preserving pixel-art sharpness
    result = rotated.resize(orig_size, Image.NEAREST)

    out_dir = save_path
    os.makedirs(out_dir, exist_ok=True)
    base = os.path.splitext(os.path.basename(input_path))[0]
    out_name = _ensure_png_ext(filename) if filename else f"{base}_rot{int(angle)}.png"
    out_path = os.path.join(out_dir, out_name)

    result.save(out_path, "PNG")
    return os.path.abspath(out_path)


def generate_ore_texture(name: str, color: str, save_path: str,
                         filename: str | None = None) -> str:
    """Generate an ore texture using standard stone base + ore overlay.

    Automatically uses ore_background.png as the base and ore_overlay.png
    as the grayscale overlay, colorizing it with the given color.

    Args:
        name: Ore name (e.g. 'diamond', 'iron') for default filename.
        color: Hex color for the ore (e.g. '#00FFFF' for diamond).
        save_path: Directory to save the output.
        filename: Custom output filename. Defaults to ore_<name>.png.

    Returns the absolute path to the saved file.
    """
    project_dir = os.path.dirname(os.path.abspath(__file__))
    base_path = os.path.join(project_dir, "ore_background.png")
    overlay_path = os.path.join(project_dir, "ore_overlay.png")

    if not os.path.exists(base_path):
        raise FileNotFoundError(f"Base texture not found: {base_path}")
    if not os.path.exists(overlay_path):
        raise FileNotFoundError(f"Overlay texture not found: {overlay_path}")

    overlays = [{"path": overlay_path, "color": color}]
    out_name = _ensure_png_ext(filename) if filename else f"ore_{name}.png"

    return composite_colorized(base_path, overlays, save_path, out_name)


def main():
    token, model, image_size = load_config()

    # Parse CLI: [--block] [--model MODEL] [item_name]
    args = sys.argv[1:]
    mode = "item"
    item = "crystal wand"
    i = 0
    while i < len(args):
        if args[i] == "--model" and i + 1 < len(args):
            model = args[i + 1]
            if model not in AVAILABLE_MODELS:
                print(f"[WARN] Unknown model '{model}', using {DEFAULT_MODEL}")
                model = DEFAULT_MODEL
            i += 2
        elif args[i] == "--block":
            mode = "block"
            i += 1
        else:
            item = args[i]
            i += 1

    print(f"Mode: {mode}, Model: {model}, Image size: {image_size}")
    if mode == "block":
        out_path = generate_mc_block(token, model, item, image_size=image_size)
    else:
        out_path = generate_mc_pixelart(token, model, item, image_size=image_size)
    print(f"Saved: {out_path}")


if __name__ == "__main__":
    main()
