import requests
import base64
import os
import sys
from io import BytesIO
from PIL import Image


TOKEN_FILE = os.path.join(os.path.dirname(__file__), "api_token.txt")
API_URL = "https://api.siliconflow.cn/v1/images/generations"
SIZE_OPTIONS = [16, 32, 64, 128, 256, 1024]
BUFF_SIZE_OPTIONS = [18, 36, 72, 144, 288, 324]
DEFAULT_SIZE = 64
DEFAULT_BUFF_SIZE = 72
AVAILABLE_MODELS = ["Kwai-Kolors/Kolors", "Tongyi-MAI/Z-Image-Turbo"]
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

    print("Generating image via SiliconFlow API ...")
    resp = requests.post(API_URL, json=payload, headers=headers, timeout=120)
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


def generate_image_raw(token: str, model: str, prompt: str, negative: str = "",
                         save_path: str | None = None,
                         filename: str | None = None,
                         image_size: str | None = None) -> str:
    """Generate a raw AI image without any pixel-art style prompts or post-processing.

    Returns the absolute path to the saved file.
    """
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
    print("Generating raw image via SiliconFlow API ...")
    resp = requests.post(API_URL, json=payload, headers=headers, timeout=120)
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
