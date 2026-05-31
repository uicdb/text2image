# MC Pixel Art Generator

调用 AI 生成 Minecraft 风格像素物品图标，自动去背景，邻近缩放到 64×64。

## 环境要求

- Python 3.10+
- SiliconFlow API 密钥（[注册获取](https://cloud.siliconflow.cn)）

## 安装

```bash
# 1. 克隆或下载本项目
# 2. 安装依赖
pip install -r requirements.txt
```

## 配置

```bash
# 复制配置模板
cp api_token.example.txt api_token.txt
```

编辑 `api_token.txt`：

```ini
apikey=sk-xxxxxxxxxxxxxxxx
model=Kwai-Kolors/Kolors
```

| 字段 | 说明 |
|------|------|
| `apikey` | SiliconFlow API 密钥 |
| `model` | 可选，默认 `Kwai-Kolors/Kolors`，也可选 `Tongyi-MAI/Z-Image-Turbo` |

## 命令行用法

```bash
# 默认生成"水晶法杖"
python generate_mc_pixelart.py

# 指定物品
python generate_mc_pixelart.py "diamond sword"

# 切换模型
python generate_mc_pixelart.py --model "Tongyi-MAI/Z-Image-Turbo" "iron pickaxe"
```

输出文件：`mc_pixelart_<物品名>_64x64.png`

## MCP 服务

以 MCP 工具形式运行，供 Claude Code 等客户端调用。

### 配置 MCP

编辑 `~/.claude/settings.json`，在 `mcpServers` 中添加：

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

也可参考项目中的 `mcp_config.json` 文件。

### MCP 工具参数

`generate_mc_pixelart`

| 参数 | 必填 | 说明 |
|------|------|------|
| `name` | 是 | 材质名，如 `"crystal wand"` |
| `save_path` | 是 | 图片保存目录 |
| `filename` | 否 | 自定义文件名，默认 `mc_pixelart_<name>_64x64.png` |

### MCP 调用示例

在 Claude Code 中直接对话：

> 帮我生成一个钻石剑的 MC 像素图标，存到 `C:\textures` 下

## 处理流程

```
API 生成 1024×1024  →  智能去纯色背景  →  邻近缩放 64×64  →  保存 PNG
```

- **去背景**：采样四角颜色，自动检测并移除纯色背景改为透明
- **邻近缩放**：使用 `NEAREST` 插值，保持像素艺术锐利边缘

## 项目文件

```
├── generate_mc_pixelart.py   # 核心逻辑 + CLI 入口
├── mcp_server.py             # MCP 服务
├── api_token.txt             # 你的 API 配置（不入 git）
├── api_token.example.txt     # 配置模板
├── requirements.txt          # Python 依赖
├── mcp_config.json           # MCP 配置参考
└── tool/                     # API 格式与提示词参考
```
