---
name: feishu-wiki-export
description: 递归导出飞书（Lark）知识库/Wiki 为本地 Markdown 完整备份，含图片、附件、表格、Mermaid 图表与层级目录。与 feishu-doc（单篇读写）互补，面向整棵树批量导出。Use when：用户说"导出飞书文档、导出飞书知识库、备份飞书、把飞书文档导出为 md、导出整个 wiki、批量导出飞书文档、feishu wiki export、backup feishu docs、把知识库同步到本地"，或需要将飞书文档批量转 Markdown 做归档/离线检索/喂给 LLM。
---

# Feishu Wiki Export

递归导出飞书知识库节点树为本地 Markdown：`<out>/<根节点>/<根节点>.md` + 子节点目录 + `images/`、`files/` 资源目录，每个 md 首行为 `<!-- 来源: <wiki url> -->` 便于回溯。

## 依赖与凭证

- Node.js 18+（使用内置 `fetch`）
- `feishu-common`（认证库，需已安装：仓库内同级目录，或 `~/.agents/skills/feishu-common`）
- 凭证按以下顺序解析（脚本自动处理）：
  1. 环境变量 `FEISHU_APP_ID` / `FEISHU_APP_SECRET`
  2. feishu-common 旁的 `config.json`（即 `~/.agents/skills/config.json`）
  3. 自动回退搜索 `~/.agents/skills/feishu-doc-*/config.json`、`~/.config/opencode/skills/feishu-doc-*/config.json`

飞书应用需开通权限：`wiki:wiki:readonly`、`docx:document:readonly`、`drive:drive:readonly`（读图片/附件）、`sheets:spreadsheet:readonly`；并把应用加入知识库成员（否则报 `code=131006`）。

## 用法

```powershell
# 导出某个知识库分支（--url 或 --token 二选一）
node scripts/export_wiki.js --url "https://my.feishu.cn/wiki/J5rkwc0JfiAOXGkzPnucGqstnqh" --out "C:\Users\Young\Downloads\飞书文档"

# 导出整个知识库空间（space 下全部顶级节点，如个人知识库的 7 个分支）
node scripts/export_wiki.js --space 7642547123027725266 --out "C:\Users\Young\Downloads\飞书文档"

# 仅导出单个节点
node scripts/export_wiki.js --token J5rkwc0JfiAOXGkzPnucGqstnqh --out D:\backup\feishu
```

- 从技能目录（`scripts/export_wiki.js` 的所在技能根）运行，或用绝对路径运行。
- `--url` 支持 `wiki` / `docx` / `docs` / `sheets` 链接，自动取 token；带 `?fromScene=...` 等查询参数无影响。
- space_id 获取：任意节点导出时脚本会打印 `Root: <标题> space: <space_id>`，或从飞书开放平台/URL 获取。
- `--space` 需要应用具备**空间级**读取权限；若报 `131006 wiki space permission denied`，改用分支逐个导出：把各分支根节点链接传给 `--url`（分支根 token 可从已导出 md 的首行注释 `<!-- 来源: https://.../wiki/<token> -->` 提取）。

## 导出保真度

| 飞书类型 | 导出形式 |
|---|---|
| 标题/正文/加粗/斜体/删除线/行内代码/链接 | 对应 Markdown |
| 有序/无序/待办列表、引用容器 | Markdown 列表 / `>` 引用 |
| 代码块 | ` ``` ` 围栏 |
| 表格（含合并单元格） | Markdown 表格（单元格内换行用 `<br>`） |
| 图片 / 附件 | 下载到 `images/` / `files/`，正文相对路径引用 |
| 文档内嵌电子表格（sheet 块）/ 独立 sheet 节点 | 各工作表导出为 Markdown 表格（前 300 行非空数据，超出有截断提示） |
| 流程图/Mermaid（add-on 块） | ` ```mermaid ` 围栏 |
| mention 文档/用户/群、公式 | 链接/文本 |
| 旧版 doc 节点 | raw_content 纯文本回退 |
| bitable 等其它类型 | 占位提示（不支持） |

## 行为与注意

- 覆盖式导出（幂等）：重复导出到同一目录会覆盖同名文件；同名附件冲突时自动加 token 前缀，不会丢文件。
- 串行请求 + 指数退避重试；权限类错误（131006/131005/131002）立即报出。
- 结束时打印 `total/ok/failed/warnings` 统计；存在失败时退出码为 1，失败清单以 JSON 打印。
- 大知识库（数百节点）耗时按分钟计；中断后直接重跑即可。
- token 缓存位于 `~/.agents/skills/memory/feishu_token.json`（feishu-common 管理）。
