# MC Pixel Art Generator

调用 AI 生成 Minecraft 风格像素贴图（物品、方块、Buff 图标），智能去背景，邻近缩放。同时提供图像处理工具集（改色、着色、像素化、图生图、OCR）。

支持 **CLI** 和 **MCP 服务**两种使用方式，共 12 个 MCP 工具。

## 环境要求

- Python 3.10+
- SiliconFlow API 密钥（[注册获取](https://cloud.siliconflow.cn)）

## 安装

```bash
pip install -r requirements.txt
```

依赖：`requests`（API 调用）、`Pillow`（图像处理）、`openai`（OCR 接口）。

## 配置

```bash
cp api_token.example.txt api_token.txt
```

编辑 `api_token.txt`：

```ini
apikey=sk-xxxxxxxxxxxxxxxx
model=Kwai-Kolors/Kolors
image_size=1024x1024
```

| 字段 | 说明 |
|------|------|
| `apikey` | SiliconFlow API 密钥 |
| `model` | 可选 `Kwai-Kolors/Kolors`（默认）或 `Tongyi-MAI/Z-Image-Turbo` |
| `image_size` | 可选 `WxH`。Kolors 默认 `1024x1024`，Tongyi 默认 `1328x1328` |

## 速率控制

Kolors 模型在 **65 秒内最多 2 次调用**（60 秒限制 + 5 秒容差），超限自动切换 Tongyi。切换时会打印 `[Rate]` 日志。

## 命令行用法

```bash
# 物品图标（默认 64x64）
python generate_mc_pixelart.py "diamond sword"

# 方块贴图
python generate_mc_pixelart.py --block "stone bricks"

# 切换模型
python generate_mc_pixelart.py --model "Tongyi-MAI/Z-Image-Turbo" "crystal wand"
```

## MCP 服务

### 配置

编辑 `~/.claude/settings.json`，在 `mcpServers` 中添加（可参考 `mcp_config.json`）：

```json
{
  "mcpServers": {
    "mc-pixelart": {
      "command": "python",
      "args": ["<项目路径>/mcp_server.py"],
      "type": "stdio"
    }
  }
}
```

重启 Claude Code 生效。

### MCP 工具

#### 生成类

所有生成工具支持 `model` 参数临时覆盖配置。

| 工具 | 说明 | 默认尺寸 | 特有参数 |
|------|------|----------|----------|
| `generate_mc_pixelart` | MC 物品图标 | 64 | prompt, size(16-1024) |
| `generate_mc_block` | MC 方块贴图（俯视 tileable） | 64 | prompt, size(16-1024) |
| `generate_mc_buff` | MC Buff 图标 | 72 | prompt, size(18-324), keep_background |
| `generate_image_raw` | 通用生图（无像素风格） | 自适应 | negative_prompt, image_size, model |
| `generate_image_to_image` | 图生图（基于参考图） | 自适应 | image_url, negative_prompt, image_size, mc_style, model |

> `generate_image_to_image` 的 `image_url` 需公网可访问。Tongyi 支持图生图，Kolors 不支持。

> 朝向不对时用 `rotate_pixel_art` 修正，**不要重新生成**。

#### 图像处理类

纯 Python 处理，不调用 AI。

| 工具 | 说明 | 关键参数 |
|------|------|----------|
| `pixelate_image` | 指定图片 → 去背景 + 邻近缩放到 MC 像素风 | input_path, size(16-1024) |
| `recolor_image` | 颜色替换/色调变换 | color, from_color, tolerance(0-255), smooth |
| `colorize_grayscale` | 灰度图着色 | color, brightness(0.5-1.5) |
| `rotate_pixel_art` | 旋转 + NEAREST 缩回原尺寸 | angle（正数逆时针，默认 45） |

#### 工具类

| 工具 | 说明 |
|------|------|
| `upload_file` | 上传文件到 SiliconFlow（JSONL 批量用）|
| `list_files` | 列出已上传的文件 |
| `image_ocr` | DeepSeek-OCR 图片文字识别/问答 |

### MCP 调用示例

> 生成一把钻石剑的像素图标，128x128，存到 `C:\textures`

> 生成一个速度 buff 图标，用 Tongyi 模型，保留背景

> 把刚才的图片逆时针旋转 90 度

> 生成一张日落山水湖泊图，水彩风格

> 把这张照片转成 MC 像素风，64x64

> 把这张红苹果图改成蓝色

## 处理流程

```
AI 生成：API 生成原始图 → 全边缘采样去背景 → NEAREST 缩放到目标尺寸 → 保存 PNG
图像处理：加载图片 → 去背景 → NEAREST 缩放 → 保存 PNG（不调 AI）
```

- **去背景**：采样图片四条边缘，中位数取色 + 动态容差。渐变背景也能处理。
- **邻近缩放**：全部使用 `NEAREST` 插值，保持像素艺术锐利边缘。
- **改色**：支持硬替换（指定色 + 容差）和 smooth 渐进模式（越近偏移越多）。

## 提示词体系

项目内置三套提示词，分别对应不同生成类型：

| 类型 | 正向强调 | 负向排除 |
|------|----------|----------|
| 物品 | 物品图标、无渐变无阴影、透明背景 | 3D、模糊、水印、阴影 |
| 方块 | 俯视图、tileable 无缝、无透视 | 3D、透视、侧视图、光照 |
| Buff | 小图标、极简轮廓、18x18 风格 | 复杂细节、场景、多物体 |

## 项目文件

```
├── generate_mc_pixelart.py   # 核心逻辑 + CLI 入口
├── mcp_server.py             # MCP 服务（12 个工具）
├── api_token.txt             # API 配置（不入 git）
├── api_token.example.txt     # 配置模板
├── requirements.txt          # Python 依赖
├── mcp_config.json           # MCP 配置参考
├── README.md
└── tool/                     # API 格式与提示词参考
```
