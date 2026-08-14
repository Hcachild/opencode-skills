---
name: documentation-and-adrs
description: 记录技术决策及其背景、约束、备选方案和取舍，并维护架构决策记录、公共 API 文档、README、变更日志与面向开发代理的项目规则。适用于作出重要架构决策、比较竞争方案、新增或修改公共接口、发布影响用户行为的功能、沉淀项目上下文或反复解释同一设计原因时；不用于复述显而易见的代码或记录一次性原型。
---

# 文档与架构决策记录

## 核心原则

记录决策，不只记录代码。高价值文档应解释“为什么”：当时的背景、约束、权衡、被否决的方案和后果。代码说明构建了什么，文档说明为什么这样构建。

不要为显而易见的代码添加重复说明，不要为一次性原型制造长期维护文档，也不要用注释代替清晰的代码结构。

## 架构决策记录

架构决策记录（ADR）用于保存重要技术决策的推理过程，是最有价值的工程文档之一。

以下决策通常需要 ADR：

- 选择框架、库或主要依赖。
- 设计数据模型或数据库结构。
- 选择认证、授权或身份策略。
- 决定 API 架构，例如 REST、GraphQL 或 tRPC。
- 选择构建工具、托管平台或基础设施。
- 作出逆转成本较高的技术决策。

### ADR 存放与编号

默认将 ADR 存放在 `docs/decisions/`，使用连续编号，例如：

```text
docs/decisions/
├── 001-use-postgresql.md
├── 002-adopt-event-driven-jobs.md
└── 003-server-side-theme-initialization.md
```

遵循项目已有目录和命名约定；如果项目已采用其他位置，不要另建平行体系。

### ADR 模板

```markdown
# ADR-001：主数据库使用 PostgreSQL

## 状态
已提议 | 已接受 | 已被 ADR-XXX 取代 | 已废弃

## 日期
2025-01-15

## 背景
任务管理应用需要一个主数据库，关键要求包括：

- 关系型数据模型，用户、任务和团队之间存在关联
- 任务状态变更需要 ACID 事务
- 支持对任务内容进行全文搜索
- 小团队运维能力有限，需要可用的托管服务

## 决策
使用 PostgreSQL，并采用 Prisma ORM。

## 考虑过的替代方案

### MongoDB

- 优点：结构灵活，启动成本低
- 缺点：数据本质上是关系型，需要手工维护关系
- 否决原因：在文档数据库中处理关系数据会引入复杂关联或数据重复

### SQLite

- 优点：零配置、嵌入式、读取速度快
- 缺点：并发写入能力有限，缺少适合生产环境的托管方案
- 否决原因：不适合生产环境中的多用户 Web 应用

### MySQL

- 优点：成熟、生态广泛
- 缺点：PostgreSQL 在 JSON、全文搜索和相关工具方面更符合需求
- 否决原因：PostgreSQL 与当前功能要求更匹配

## 后果

- Prisma 提供类型安全的数据访问和迁移管理
- 可以使用 PostgreSQL 全文搜索，暂时无需引入 Elasticsearch
- 团队需要掌握 PostgreSQL，属于通用技能，风险较低
- 生产环境采用 Supabase、Neon 或 RDS 等托管服务
```

### ADR 生命周期

```text
已提议 -> 已接受 -> 已被取代或已废弃
```

- 不要删除旧 ADR，它们保存了历史背景。
- 决策变化时，新建 ADR，并明确引用和取代旧 ADR。
- 不要直接改写旧 ADR，让历史看起来像从未发生过。
- 状态、日期和取代关系必须保持可追踪。

## 行内文档

### 注释解释原因，不复述行为

```typescript
// 不推荐：只是复述代码
// 计数器加 1
counter += 1;

// 推荐：解释不明显的设计意图
// 使用滑动窗口限流，并在窗口边界重置计数器，
// 避免固定时间重置导致边界瞬时突发。
if (now - windowStart > WINDOW_SIZE_MS) {
  counter = 0;
  windowStart = now;
}
```

### 不要添加无价值注释

```typescript
// 自解释代码无需注释
function calculateTotal(items: CartItem[]): number {
  return items.reduce((sum, item) => sum + item.price * item.quantity, 0);
}

// 不要留下本应立即完成的 TODO
// TODO：增加错误处理

// 不要保留被注释掉的旧实现，版本控制系统已保存历史
// const oldImplementation = () => { /* ... */ };
```

### 在影响位置记录已知陷阱

```typescript
/**
 * 重要：必须在首次渲染前调用此函数。
 * 如果在 hydration 后调用，由于 SSR 阶段没有主题上下文，
 * 页面会短暂显示未应用样式的内容。
 *
 * 完整设计原因见 ADR-003。
 */
export function initializeTheme(theme: Theme): void {
  // ...
}
```

已知陷阱应放在最接近风险发生点的位置，并链接到更完整的决策文档。

## 公共 API 文档

公共 REST API、GraphQL Schema 和库接口必须说明输入、输出、错误和关键示例。

### TypeScript 优先使用类型与 JSDoc

```typescript
/**
 * 创建新任务。
 *
 * @param input - 任务创建数据，标题必填，描述可选
 * @returns 包含服务端生成 ID 和时间戳的任务
 * @throws {ValidationError} 标题为空或超过 200 个字符时抛出
 * @throws {AuthenticationError} 用户未认证时抛出
 *
 * @example
 * const task = await createTask({ title: '购买杂货' });
 * console.log(task.id); // "task_abc123"
 */
export async function createTask(input: CreateTaskInput): Promise<Task> {
  // ...
}
```

不要用长篇 JSDoc 重复类型已经表达的信息。重点说明约束、错误、生命周期、副作用和不明显的语义。

### REST API 使用 OpenAPI 或 Swagger

```yaml
paths:
  /api/tasks:
    post:
      summary: 创建任务
      requestBody:
        required: true
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/CreateTaskInput'
      responses:
        '201':
          description: 任务创建成功
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/Task'
        '422':
          description: 数据校验失败
```

接口实现、类型和文档应在同一次变更中提交，避免文档长期滞后。

## README 结构

项目 README 至少应覆盖：

```markdown
# 项目名称

用一段话说明项目解决什么问题。

## 快速开始

1. 克隆仓库
2. 安装依赖：`npm install`
3. 配置环境：`cp .env.example .env`
4. 启动开发服务：`npm run dev`

## 常用命令

| 命令 | 说明 |
|---|---|
| `npm run dev` | 启动开发服务 |
| `npm test` | 运行测试 |
| `npm run build` | 构建生产版本 |
| `npm run lint` | 运行代码检查 |

## 架构

简要说明项目结构和关键设计决策，并链接到相关 ADR。

## 贡献方式

说明贡献流程、编码规范和 PR 要求。
```

README 中的命令必须能在当前仓库实际执行。不要复制过时模板，也不要声称不存在的环境或依赖。

## 变更日志

发布用户可感知的功能后维护变更日志：

```markdown
# 变更日志

## [1.2.0] - 2025-01-20

### 新增

- 支持将任务分享给团队成员（#123）
- 增加任务分配邮件通知（#124）

### 修复

- 修复快速点击创建按钮时出现重复任务的问题（#125）

### 变更

- 任务列表每页数量从 20 调整为 50（#126）
```

描述用户可观察到的变化，不要把内部提交记录原样堆入变更日志。

## 面向开发代理的文档

为 AI 开发代理维护以下上下文：

- `AGENTS.md`、`CLAUDE.md` 或规则文件：记录项目约定、边界和必须遵循的流程。
- 规格文件：保持需求与当前行为一致。
- ADR：帮助代理理解历史决策，避免重复推翻已有结论。
- 行内陷阱说明：防止代理重复触发已知问题。

所有规则必须基于当前仓库事实。规则文件过期时应更新或删除，不能继续把旧约束当作现状。

## 常见错误理由

| 错误理由 | 实际问题 |
|---|---|
| “代码本身就是文档” | 代码说明做了什么，不能说明为什么这样做、否决了什么方案或有哪些约束 |
| “API 稳定后再写文档” | 文档本身是设计检查，越早写越容易暴露接口问题 |
| “没人读文档” | 后续工程师、开发代理和未来的自己都依赖这些上下文 |
| “ADR 是额外负担” | 十分钟的 ADR 能避免数月后再次进行同样的长时间争论 |
| “注释会过期” | 解释行为的注释容易过期，解释稳定原因和约束的注释更有价值 |

## 红色警报

- 重要架构决策没有书面依据。
- 公共 API 没有类型或文档。
- README 没有说明如何运行项目。
- 用注释保留旧代码，而不是删除。
- TODO 长期存在且没有跟踪机制。
- 项目有大量架构选择，却没有任何 ADR。
- 文档只复述代码，没有解释意图或约束。
- 文档中的命令、路径、版本或行为与当前代码不一致。

## 完成验收

- [ ] 重要架构决策均有 ADR。
- [ ] ADR 包含状态、日期、背景、决策、替代方案和后果。
- [ ] README 包含快速开始、常用命令和架构概览。
- [ ] 公共 API 说明输入、输出、错误和关键示例。
- [ ] 已知陷阱记录在最相关的位置。
- [ ] 没有遗留被注释掉的旧代码。
- [ ] 项目规则文件与当前代码和流程一致。
- [ ] 文档中的命令、路径和示例已按当前仓库验证。

