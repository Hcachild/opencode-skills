---
name: foxcode-image-gen
description: >-
  Generate high-quality images via the FoxCode gpt-image-2 API. Use when the user
  asks to generate, create, or draw images, diagrams, illustrations, or visual
  assets — especially technical diagrams, architecture diagrams, flowcharts,
  concept art, or any AI-generated image. Triggers on: "生成图片", "画图",
  "generate image", "create diagram", "AI生图", "画一张", "生成一张图".
---

# FoxCode Image Gen

Generate images via the FoxCode proxy API (`gpt-image-2` model).

## Quick Start

Run `scripts/generate_image.py` with a prompt and output path:

```bash
python scripts/generate_image.py --prompt "你的提示词" --output "output.png"
```

Optional flags: `--size 1536x1024` (default `1024x1024`), `--quality high`.

## Workflow

1. Understand what the user wants — ask for clarification if the prompt is vague.
2. Craft a detailed prompt. For Chinese diagrams, explicitly state:
   `图中所有文字必须使用中文，文字必须清晰可读，不能有乱码。`
3. Call `scripts/generate_image.py` — it handles API auth, request, download, and save.
4. Verify the output file exists and has a reasonable size (>100 KB).
5. If the user wants multiple images, call the script once per image.

## Critical: Use Python, Not PowerShell

**Always use the Python script.** PowerShell corrupts non-ASCII characters in
JSON bodies, causing the API to receive garbled text and produce broken images.

```bash
# CORRECT — Python handles UTF-8 natively
python scripts/generate_image.py --prompt "中文提示词" --output "diagram.png"

# WRONG — PowerShell will corrupt Chinese characters
Invoke-RestMethod ... -Body '{"prompt":"中文"}'
```

## Prompt Writing Tips

- Be specific about layout: "从左到右排列", "环形布局", "三列".
- List every label the image should contain.
- Specify style: "扁平化矢量风格", "纯白背景", "圆角矩形框".
- For technical diagrams: describe boxes, arrows, colors, and icons.
- Always end with: `配色协调，留白充足，文字居中清晰。`
- Keep prompts under 500 tokens for best results.

## Supported Sizes

| Size | Aspect | Use case |
|------|--------|----------|
| `1024x1024` | Square | Icons, logos, circular layouts |
| `1536x1024` | Landscape | Flowcharts, pipelines, architecture diagrams |
| `1024x1536` | Portrait | Posters, vertical infographics |

## API Details

- Endpoint: `https://code.newcli.com/codex/v1/images/generations`
- Model: `gpt-image-2`
- Auth: `Authorization: Bearer <API_KEY>` (key is embedded in the script)
- Response: returns `url` field; script auto-downloads the image
