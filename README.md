# MC Pixel Art Generator

调用 AI 生成 Minecraft 风格像素贴图（物品、方块、Buff 图标），智能去背景，邻近缩放。

支持 **CLI** 和 **MCP 服务** 两种使用方式。

## 环境要求

- Python 3.10+
- SiliconFlow API 密钥（[注册获取](https://cloud.siliconflow.cn)）

## 安装

```bash
pip install -r requirements.txt
```

依赖：`requests`（API 调用）、`Pillow`（图像处理）。

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
| `image_size` | 可选 `WxH` 格式。Kolors 默认 `1024x1024`，Tongyi 默认 `1328x1328` |

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

#### generate_mc_pixelart — 物品图标

| 参数 | 必填 | 说明 |
|------|:--:|------|
| `name` | 是 | 物品名称，如 `"diamond sword"` |
| `save_path` | 是 | 保存目录 |
| `filename` | 否 | 文件名，默认 `mc_pixelart_<name>_<size>x<size>.png` |
| `prompt` | 否 | 自定义提示词，不填则自动拼接 |
| `size` | 否 | 16/32/64/128/256/1024，默认 64 |

> 朝向不对时用 `rotate_pixel_art` 修正，不要重新生成。

#### generate_mc_block — 方块贴图

| 参数 | 必填 | 说明 |
|------|:--:|------|
| `name` | 是 | 方块名称，如 `"grass block"` |
| `save_path` | 是 | 保存目录 |
| `filename` | 否 | 文件名，默认 `mc_block_<name>_<size>x<size>.png` |
| `prompt` | 否 | 自定义提示词 |
| `size` | 否 | 16/32/64/128/256/1024，默认 64 |

> 朝向不对时用 `rotate_pixel_art` 修正，不要重新生成。

#### generate_mc_buff — Buff 图标

| 参数 | 必填 | 说明 |
|------|:--:|------|
| `name` | 是 | 效果名称，如 `"speed boost"` |
| `save_path` | 是 | 保存目录 |
| `filename` | 否 | 文件名，默认 `mc_buff_<name>_<size>x<size>.png` |
| `prompt` | 否 | 自定义提示词 |
| `size` | 否 | 18/36/72/144/288/324，默认 72 |
| `keep_background` | 否 | 保留 AI 生成的背景，默认 `false`（去背景） |

#### rotate_pixel_art — 旋转修正

| 参数 | 必填 | 说明 |
|------|:--:|------|
| `input_path` | 是 | 原图绝对路径 |
| `save_path` | 是 | 输出目录 |
| `filename` | 否 | 文件名，默认 `<原名>_rot<角度>.png` |
| `angle` | 否 | 旋转角度，正数逆时针，默认 45 |

典型用法：生成后方向不对 → 旋转 90° 或 -90° 翻转方向，不重新生成。

#### generate_image_raw — 通用生图

| 参数 | 必填 | 说明 |
|------|:--:|------|
| `prompt` | 是 | 自定义提示词，完整描述你想生成的图像 |
| `save_path` | 是 | 保存目录 |
| `filename` | 否 | 文件名，默认 `image_raw.png` |
| `negative_prompt` | 否 | 负向提示词，排除不想要的内容 |
| `image_size` | 否 | `WxH` 格式，不填则自动根据模型选择 |

不附加任何像素风格提示词，不缩放不去背景。适用于非像素风格的通用图像生成。

### MCP 调用示例

在 Claude Code 中对话即可：

> 生成一把钻石剑的像素图标，128x128，存到 `C:\textures`

> 生成一个速度 buff 图标，用 Tongyi 模型，保留背景

> 把刚才的图片逆时针旋转 90 度

> 生成一张日落山水湖泊图，水彩风格，存到 `C:\textures`

## 处理流程

```
API 生成 1024×1024  →  全边缘采样去背景  →  NEAREST 缩放到目标尺寸  →  保存 PNG
```

- **去背景**：采样图片四条边缘的颜色，自动检测并移除背景改为透明。渐变背景也能处理。
- **邻近缩放**：全部使用 `NEAREST` 插值，保持像素艺术锐利边缘。

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
├── mcp_server.py             # MCP 服务（5 个工具）
├── api_token.txt             # API 配置（不入 git）
├── api_token.example.txt     # 配置模板
├── requirements.txt          # Python 依赖
├── mcp_config.json           # MCP 配置参考
├── README.md
└── tool/                     # API 格式与提示词参考
```
