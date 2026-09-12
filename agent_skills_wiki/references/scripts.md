# 脚本：一次性命令、自包含脚本、agent 友好接口

## 一次性命令（不用建 scripts/）

现成的包已经能干这事时，直接在 `SKILL.md` 里写命令，不需要 `scripts/` 目录。各生态都有运行时自动解析依赖的工具：

| 工具 | 例子 | 说明 |
|---|---|---|
| `uvx` | `uvx ruff@0.8.0 check .` | 随 uv 附带，需单独装。缓存激进，重复运行接近瞬时 |
| `pipx` | `pipx run 'black==24.10.0' .` | 需单独装，但 OS 包管理器覆盖更广（`apt`/`brew`） |
| `npx` | `npx eslint@9 --fix .` | **随 npm 附带，无需额外安装** |
| `bunx` | `bunx eslint@9 --fix .` | `npx` 的等价物，仅在环境装了 Bun 时用 |
| `deno run` | `deno run --allow-read npm:eslint@9 -- --fix .` | 需权限 flag；用 `--` 分隔 Deno 自身 flag 和工具 flag |
| `go run` | `go run golang.org/x/tools/cmd/goimports@v0.28.0 .` | 内建于 go 命令 |

三条纪律：

- **版本必须 pin**（`npx eslint@9.0.0`），否则命令的行为会随时间漂移
- **前置依赖要在 `SKILL.md` 里写明**（"需要 Node.js 18+"），不要假设 agent 的环境有。运行时级别的要求用 `compatibility` frontmatter 字段
- **复杂命令要沉成脚本。**调几个 flag 的场合适合一次性命令；命令复杂到第一次写不对，就该换成 `scripts/` 里测试过的脚本

## 自包含脚本

需要可复用逻辑时，在 `scripts/` 里放一个**自己声明依赖**的脚本，agent 一条命令就能跑，不需要单独的 manifest 和安装步骤。

**Python** — [PEP 723](https://peps.python.org/pep-0723/) 的内联元数据，`# ///` 标记里写 TOML：

```python
# /// script
# dependencies = [
#   "beautifulsoup4>=4.12,<5",
# ]
# ///
from bs4 import BeautifulSoup
```

`uv run scripts/extract.py` 会建隔离环境、装声明的依赖再执行（`pipx run` 也支持 PEP 723）。可用 `requires-python` 约束版本，`uv lock --script` 生成 lockfile。

**Deno** — `npm:` / `jsr:` 说明符让脚本天然自包含：

```typescript
import * as cheerio from "npm:cheerio@1.0.0";
```

依赖全局缓存，`--reload` 强制重取。带原生插件（node-gyp）的包可能跑不起来，发预编译二进制的包最稳。

**Bun** — 找不到 `node_modules` 时运行期自动装，版本直接 pin 在 import 路径里：

```typescript
import * as cheerio from "cheerio@1.0.0";
```

不需要 `package.json`，TypeScript 原生支持。**但目录树往上任何一层存在 `node_modules`，自动安装就会被禁用**，退回标准 Node 解析。

**Ruby** — `bundler/inline`（Ruby 2.6 起自带）：

```ruby
require 'bundler/inline'
gemfile do
  source 'https://rubygems.org'
  gem 'nokogiri', '~> 1.16'
end
```

没有 lockfile，所以版本要显式 pin。工作目录里已有的 `Gemfile` 或 `BUNDLE_GEMFILE` 环境变量会干扰。

## 从 SKILL.md 引用

用相对 skill 根目录的路径，agent 自动解析。**要在正文里列出可用脚本，agent 才知道它们存在**：

```markdown
## 可用脚本
- `scripts/validate.sh` — 校验配置文件
- `scripts/process.py` — 处理输入数据

## 流程
1. 跑校验：`bash scripts/validate.sh "$INPUT_FILE"`
2. 处理结果：`python3 scripts/process.py --input results.json`
```

同一约定适用于 `references/*.md`：代码块里的执行路径**相对 skill 根目录**，因为 agent 是从那里执行命令的。

## 为 agent 设计接口

agent 靠读 stdout 和 stderr 决定下一步。几个设计选择会极大影响它用得顺不顺。

### 禁止交互式提示

**这是执行环境的硬性要求。**agent 跑在非交互 shell 里，无法响应 TTY 提示、密码框或确认菜单。阻塞等输入的脚本会**永久挂住**。

所有输入走命令行 flag、环境变量或 stdin：

```
# ❌ 挂住等输入
$ python scripts/deploy.py
Target environment: _

# ✅ 明确报错并给出指引
$ python scripts/deploy.py
Error: --env is required. Options: development, staging, production.
Usage: python scripts/deploy.py --env staging --tag v1.2.3
```

### 用 `--help` 说明用法

`--help` 输出是 agent 学习脚本接口的主要途径。要含简述、可用 flag、用例。但**保持简洁**——它会进 agent 的上下文，和其他内容抢空间。

### 错误信息要有用

**agent 拿到的错误信息直接塑造它的下一次尝试。**一句 `Error: invalid input` 就白费一个 turn。要说清：错在哪、期望什么、试什么。

```
Error: --format must be one of: json, csv, table.
       Received: "xml"
```

### 输出用结构化格式

JSON / CSV / TSV 优于自由文本——能被 agent 和标准工具（`jq`、`cut`、`awk`）同时消费，脚本才能进管道组合。

```
# ❌ 空格对齐，难以程序化解析
NAME          STATUS    CREATED
my-service    running   2025-01-15
# ✅ 字段边界无歧义
{"name": "my-service", "status": "running", "created": "2025-01-15"}
```

**数据和诊断要分开：结构化数据走 stdout，进度、警告和其他诊断走 stderr。**这样 agent 能拿到干净可解析的输出，需要时又能看诊断。

### 其余考虑

- **幂等**：agent 会重试。"不存在才创建"比"创建且重复则失败"安全
- **输入约束**：有歧义的输入要明确报错，不要猜。尽量用枚举和闭集
- **dry-run**：破坏性或有状态的操作给 `--dry-run`，让 agent 能先预览
- **退出码有意义**：不同失败类型用不同退出码（未找到、参数非法、鉴权失败），并在 `--help` 里说明每个码的含义
- **安全默认值**：破坏性操作考虑要不要 `--confirm` / `--force`
- **输出体积可预测**：**很多 agent 框架会在 10~30K 字符处自动截断工具输出**，可能丢掉关键信息。可能产生大输出时，默认给摘要或设合理上限，并支持 `--offset` 让 agent 按需取更多；不适合分页的就强制要求传 `--output`（指定文件，或显式给 `-` 才走 stdout）

## 症状 → 排查

| 症状 | 排查 |
|---|---|
| 脚本跑起来就不返回、卡死 | 「禁止交互式提示」——非交互 shell 等 TTY 输入会永久挂住 |
| agent 反复用错 flag | `--help` 缺失或不清楚 |
| 报错后 agent 乱试 | 错误信息没说清期望什么，见「错误信息要有用」 |
| agent 解析不了脚本输出 | 改结构化格式，且诊断信息别混进 stdout |
| 输出被截断丢了关键信息 | 「其余考虑」末条——默认给摘要 + `--offset`，或强制 `--output` |
| agent 重试后产生重复数据 | 幂等性，改成"不存在才创建" |
| 依赖装不上或版本漂移 | 见「自包含脚本」，用内联依赖声明并 pin 版本 |
| Bun 脚本的自动安装失效 | 上层目录树里有 `node_modules`，见 Bun 那节 |
| 命令在别人机器上跑不了 | 前置依赖没在 `SKILL.md` 声明，运行时要求用 `compatibility` 字段 |
