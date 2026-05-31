import requests
import base64
import os
import sys
from io import BytesIO
from PIL import Image


TOKEN_FILE = os.path.join(os.path.dirname(__file__), "api_token.txt")
API_URL = "https://api.siliconflow.cn/v1/images/generations"
TARGET_SIZE = (64, 64)
AVAILABLE_MODELS = ["Kwai-Kolors/Kolors", "Tongyi-MAI/Z-Image-Turbo"]
DEFAULT_MODEL = "Kwai-Kolors/Kolors"

# ── Minecraft pixel art prompt (from tool/提示词.txt) ──
POSITIVE_PROMPT = (
    "game texture map, Minecraft style, pixel art item icon, "
    "32x32 pixels, pixel art style, flat colors, no gradient, no shadow, "
    "flat vector art, no shading, no gradient, "
    "isolated on transparent background, game asset"
)
NEGATIVE_PROMPT = (
    "photorealistic, 3D render, gradient, blurry, watermark, text, "
    "signature, character, background, shadow, depth"
)


def load_config():
    """Load token and optional settings from api_token.txt.

    File format (one per line, # for comments):
        apikey=sk-your-api-key
        model=Kwai-Kolors/Kolors
    """
    path = os.path.abspath(TOKEN_FILE)
    if not os.path.exists(path):
        print(f"[ERROR] Config file not found: {path}")
        print("Create api_token.txt with apikey= and model= entries.")
        sys.exit(1)

    token = None
    model = DEFAULT_MODEL
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

    if not token or token == "sk-your-api-key-here":
        print("[ERROR] Please set apikey= in api_token.txt")
        sys.exit(1)

    if model not in AVAILABLE_MODELS:
        print(f"[WARN] Unknown model '{model}', falling back to {DEFAULT_MODEL}")
        model = DEFAULT_MODEL

    return token, model


def generate_image(token: str, model: str, prompt: str, negative_prompt: str = "") -> Image.Image:
    payload = {
        "model": model,
        "prompt": f"{prompt}, {POSITIVE_PROMPT}",
        "negative_prompt": f"{negative_prompt}, {NEGATIVE_PROMPT}",
        "image_size": "1024x1024",
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
    """Detect and remove a solid-color background by sampling image corners.

    Samples the four corners, computes the dominant background color, then
    makes any pixel within *tolerance* Euclidean distance transparent.
    Only triggers when corners are consistent (max corner variance < threshold).
    """
    w, h = img.size
    pixels = img.load()

    # Sample corner regions (10x10 patches) to find background color
    corner_size = min(10, w // 4, h // 4)
    corners = [
        (0, 0),                          # top-left
        (w - corner_size, 0),            # top-right
        (0, h - corner_size),            # bottom-left
        (w - corner_size, h - corner_size),  # bottom-right
    ]
    samples = []
    for cx, cy in corners:
        for dx in range(corner_size):
            for dy in range(corner_size):
                r, g, b, a = pixels[cx + dx, cy + dy]
                if a > 0:
                    samples.append((r, g, b))

    if len(samples) < corner_size * corner_size:  # too few opaque corner pixels
        print("Background removal skipped (corners already transparent)")
        return img

    # Average corner color
    avg_r = sum(s[0] for s in samples) // len(samples)
    avg_g = sum(s[1] for s in samples) // len(samples)
    avg_b = sum(s[2] for s in samples) // len(samples)
    bg_color = (avg_r, avg_g, avg_b)

    # Check corner consistency — if corners vary too much, skip
    max_dist = max(
        (s[0] - avg_r) ** 2 + (s[1] - avg_g) ** 2 + (s[2] - avg_b) ** 2
        for s in samples
    )
    corner_variance = int(max_dist ** 0.5)
    if corner_variance > 60:
        print(f"Background removal skipped (corners inconsistent, variance={corner_variance})")
        return img

    print(f"Removing solid background color: RGB({bg_color[0]}, {bg_color[1]}, {bg_color[2]}) "
          f"[tolerance={tolerance}, corner_variance={corner_variance}]")

    tol_sq = tolerance * tolerance
    transparent = 0
    for y in range(h):
        for x in range(w):
            r, g, b, a = pixels[x, y]
            if a == 0:
                continue
            dist = (r - bg_color[0]) ** 2 + (g - bg_color[1]) ** 2 + (b - bg_color[2]) ** 2
            if dist <= tol_sq:
                pixels[x, y] = (r, g, b, 0)
                transparent += 1

    total = w * h
    print(f"Made {transparent}/{total} pixels transparent ({transparent * 100 // total}%)")
    return img


def scale_pixel_art(img: Image.Image, size: tuple[int, int]) -> Image.Image:
    """Nearest-neighbor downscale to preserve pixel-art sharpness."""
    return img.resize(size, Image.NEAREST)


def generate_mc_pixelart(token: str, model: str, item: str,
                          save_path: str | None = None,
                          filename: str | None = None,
                          prompt: str | None = None) -> str:
    """Generate a Minecraft pixel art image and save to disk.

    Returns the absolute path to the saved file.
    """
    if prompt:
        full_prompt = f"{prompt}, {POSITIVE_PROMPT}"
    else:
        full_prompt = f"{item}, {POSITIVE_PROMPT}"
    negative = NEGATIVE_PROMPT

    img = generate_image(token, model, full_prompt, negative)
    original_size = img.size

    img = remove_solid_background(img)
    scaled = scale_pixel_art(img, TARGET_SIZE)

    out_dir = save_path if save_path else os.path.dirname(__file__)
    os.makedirs(out_dir, exist_ok=True)
    out_name = filename if filename else f"mc_pixelart_{item.replace(' ', '_')}_{TARGET_SIZE[0]}x{TARGET_SIZE[1]}.png"
    out_path = os.path.join(out_dir, out_name)

    scaled.save(out_path, "PNG")
    return os.path.abspath(out_path)


def main():
    token, model = load_config()

    # Parse CLI: [--model MODEL] [item_name]
    args = sys.argv[1:]
    item = "crystal wand"
    i = 0
    while i < len(args):
        if args[i] == "--model" and i + 1 < len(args):
            model = args[i + 1]
            if model not in AVAILABLE_MODELS:
                print(f"[WARN] Unknown model '{model}', using {DEFAULT_MODEL}")
                model = DEFAULT_MODEL
            i += 2
        else:
            item = args[i]
            i += 1

    print(f"Model: {model}")
    out_path = generate_mc_pixelart(token, model, item)
    print(f"Saved: {out_path}")


if __name__ == "__main__":
    main()
