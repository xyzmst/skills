# 规范：字段、体积预算、安装位置

## 目录结构

一个 skill = 一个含 `SKILL.md` 的目录。除 `SKILL.md` 外全部可选，子目录名是约定不是强制：

```
skill-name/
├── SKILL.md          # 必需：frontmatter + 指令
├── scripts/          # 可执行代码
├── references/       # 按需加载的文档
└── assets/           # 模板、图片、数据文件
```

`SKILL.md` = YAML frontmatter + Markdown 正文，正文无格式限制。

## frontmatter 字段

| 字段 | 必填 | 约束 |
|---|---|---|
| `name` | 是 | ≤64 字符，仅小写字母/数字/连字符，不能首尾带 `-`、不能连续 `--`，**须与父目录同名** |
| `description` | 是 | ≤1024 字符，非空，须说清做什么 + 何时用 |
| `license` | 否 | 许可名，或指向捆绑的 license 文件 |
| `compatibility` | 否 | ≤500 字符，环境依赖（`Requires git, docker, jq`、`Requires Python 3.14+ and uv`）。多数 skill 不需要 |
| `metadata` | 否 | 字符串到字符串的映射，放规范外的自定义属性。键名要够独特避免与其他客户端冲突 |
| `allowed-tools` | 否 | 空格分隔的预授权工具（`Bash(git:*) Bash(jq:*) Read`）。**实验性**，各实现支持度不一，不要依赖 |

规范只定义以上字段。客户端私有扩展（如 Cursor 的 `disable-model-invocation`）不在规范内但被实现指南认可为合法的过滤标志——在不支持它的客户端里会被忽略，那个 skill 就会退化成可自动触发。依赖"只手动调用"这个行为时要知道它跨客户端不保证。

### `name` 反例

```yaml
name: PDF-Processing  # 大写不允许
name: -pdf            # 不能以连字符开头
name: pdf--processing # 不能连续连字符
```

### YAML 陷阱

未加引号的值里含冒号是**无效 YAML**，只是部分客户端做了加引号重试的兜底才碰巧能用：

```yaml
# ❌ 冒号破坏解析
description: Use this skill when: the user asks about PDFs
# ✅
description: "Use this skill when: the user asks about PDFs"
```

## 渐进式披露与体积预算

这是整个格式的核心机制，也是所有体积限制的来源：

| 层 | 加载什么 | 什么时候 | token 成本 |
|---|---|---|---|
| 1 目录 | 所有 skill 的 `name` + `description` | 会话启动 | 约 50~100 / 个 |
| 2 指令 | 被激活 skill 的 `SKILL.md` 正文全文 | 判定相关时 | 建议 < 5000 |
| 3 资源 | `scripts/` `references/` `assets/` 里的文件 | 正文引用到时 | 视文件 |

推论：装 20 个 skill 只付 20 份 metadata 的钱，不付 20 份指令的钱。所以**宁可多建几个边界清晰的 skill，也不要把一个 skill 写得包罗万象**。

正文上限 **500 行 / 5000 token**。超了就把细节移进 `references/`，正文只留每次都要用的核心指令。

## 文件引用

用相对 skill 根目录的路径，agent 会自动解析，不需要绝对路径：

```markdown
See [the reference guide](references/REFERENCE.md) for details.
Run the extraction script: scripts/extract.py
```

同一约定也适用于 `references/*.md` 里的路径——**代码块里的执行路径相对 skill 根目录**，因为 agent 是从那里执行命令的。

引用只保持**一层深**，不要 A 引 B 引 C 的链式嵌套，那会引发连环读。

## 安装位置与发现

规范本身**不规定 skill 目录放在哪**，只规定目录里放什么。但客户端实现已形成事实标准：

- `.agents/skills/` 是跨客户端共享的通用约定，扫这里意味着别的合规客户端装的 skill 自动可见
- 项目级（相对工作目录）与用户级（相对家目录）两个作用域都会被扫
- **同名冲突时项目级覆盖用户级**，这是各实现一致的约定；同作用域内先找到还是后找到都可接受，但应该告警说明有 skill 被遮蔽
- 部分实现还会扫 `.claude/skills/`（历史兼容）、祖先目录到 git 根（monorepo）、XDG 配置目录
- 项目级 skill 来自可能不可信的仓库（刚 clone 的开源项目），客户端应做信任门控，否则仓库可以静默往 agent 上下文里注入指令

云端 / 沙箱 agent 读不到用户级目录：项目级 skill 随代码走所以没问题，用户级和组织级必须另行下发（克隆配置仓库、设置里传 URL、Web 上传）。**依赖本机用户级目录的 skill 在 Cloud Agent 和远程 worker 里一律不生效。**

## 宽松校验

客户端实现指南要求对不合规做宽松处理，这决定了哪些问题是真阻断、哪些只是 lint：

| 问题 | 客户端应有的行为 |
|---|---|
| `name` 与父目录名不符 | 告警，**照常加载** |
| `name` 超 64 字符 | 告警，**照常加载** |
| `description` 缺失或为空 | **跳过该 skill**，记错误（没有它无法参与披露） |
| YAML 完全无法解析 | **跳过该 skill**，记错误 |

所以目录名与 `name` 不一致只是 `skills-ref validate` 会报的 lint 级问题，不影响合规客户端加载。真正会让 skill 彻底失效的只有：装错目录、软链断裂、`description` 缺失、YAML 解析失败。

## 校验命令

```bash
skills-ref validate ./my-skill
```

检查 frontmatter 合法性与命名约定，不检查内容质量。

## 症状 → 排查

| 症状 | 排查 |
|---|---|
| skill 完全不被发现 | 先确认实体或软链在被扫描的目录下；再看「宽松校验」——只有装错位置、软链断、description 缺失、YAML 挂了才是真失效 |
| 本机好用，Cloud Agent / 远程里没生效 | 见「安装位置与发现」——用户级目录读不到，要改用项目内 `.agents/skills/` |
| frontmatter 解析报错或 description 显示被截断 | 见「YAML 陷阱」，含冒号的值要加引号 |
| 同名 skill 行为和预期不一致 | 项目级覆盖用户级，查有没有被项目里的同名 skill 遮蔽 |
| `SKILL.md` 太长不知道拆多少 | 500 行 / 5000 token 是线，怎么拆和怎么写指路见 authoring.md |
| 加了 `allowed-tools` 没效果 | 实验性字段，各实现支持度不一，不要依赖 |
