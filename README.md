# skills

**全局的语言 / SDK API 知识域 skill** 的唯一源目录。实体文件都放这里，`.cursor` 和 `.agents` 侧只放软链，避免出现多份不同步的副本。

主体形态是知识域 wiki：一个技术域一个目录，`SKILL.md` 做路由，细节分册在 `references/`。另外收少量维护这些 wiki 所需的配套工具型 skill。

## 收什么

判据只有一条：**这个域里 agent 是不是会稳定地写错。**

- 收：版本敏感（API 废弃、行为随版本变）、反直觉、新旧写法并存有历史包袱的语言与 SDK 领域
- 不收：agent 凭训练数据就掌握的内容——Java 基础语法、通用设计模式、SOLID 之类，建了也只是白占上下文
- 不收：任务/工具型 skill（跑诊断、查日志、走审批流程），除非它是本仓 wiki 或 `cursor_rules/` 的配套件——即由规则点名调用、把细节从常驻上下文里挪出来的那种（体检、审查、开工计划）
- 不收：第三方分发的 skill（如 `lark-*`、`mx-*`、`pdf`、`playwright`、`openclaw`），它们随上游升级覆盖，纳入自管只会分叉
- 不收：与编码无关的个人领域 skill（投资、阅读、生活流程）

## 当前 skill

知识域 wiki：

| 目录 | skill 名 | 规模 | 覆盖域 |
|---|---|---|---|
| `kotlin_wiki/` | `kotlin-wiki` | 49 行 + 4 篇 | Kotlin 语言：惯用写法、协程/Flow、类型与 API 设计、常见陷阱 |
| `android_view_wiki/` | `android-view-wiki` | 87 行 + 9 篇 + 1 脚本 | Android View 层：测量布局、动画、约束、列表、触摸、渲染管线、insets、自定义 View；`scripts/layout-chain.py` 出约束拓扑 |
| `android_architecture_wiki/` | `android-architecture-wiki` | 64 行 + 6 篇 | Android 应用架构：UDF 与 UiState、ViewModel 边界与状态收集、一次性事件、数据层与 SSOT、用例判断、分层与 DI |
| `android_sdk_behavior_wiki/` | `android-sdk-behavior-wiki` | 64 行 + 6 篇 | targetSdk 升级与版本行为变更（API 33-37）：升级清单、权限收紧、前台服务与后台限制、intent 与组件导出、存储媒体、界面兼容 |
| `android_component_wiki/` | `android-component-wiki` | 51 行 + 5 篇 | Activity / Fragment 组件：生命周期与状态保存、Fragment 与 View 双生命周期、事务提交语义、结果回传与通信、启动模式与任务栈 |
| `android_gradle_wiki/` | `android-gradle-wiki` | 54 行 + 5 篇 | Gradle 构建：版本兼容与 AGP 8/9 破坏性变更、version catalog 与依赖仲裁、构建变体与签名、R8 与 keep 规则、构建性能 |
| `agent_skills_wiki/` | `agent-skills-wiki` | 59 行 + 6 篇 | Agent Skills 规范（[agentskills.io](https://agentskills.io)）：字段约束与体积预算、description 触发机制与触发率实测、正文密度与规定程度校准、结构模式、脚本接口、eval 方法 |
| `plantuml_wiki/` | `plantuml-wiki` | 67 行 + 3 篇 + 1 脚本 | PlantUML 语法与本地渲染：图类型选择判据、类图关系符号与成员分区、creole 与三色 diff 记法、类与线样式、布局干预手段、一批只有渲染过才知道的静默失败；`scripts/puml-render.sh` 本地出 PNG |

配套工具（任务型，作为例外留在本仓）：

| 目录 | skill 名 | 规模 | 用途 |
|---|---|---|---|
| `optimize_skill/` | `optimize-skill` | 128 行 | 给 skill 做体检并修复，本仓 wiki 的维护工具（`disable-model-invocation`，只显式调用）；判定依据路由到 `agent-skills-wiki` |
| `review_skill/` | `android-change-review` | 98 行 | 审查 Android 改动，输出 P0/P1/P2；判定依据路由到本仓各 wiki |
| `design_review_skill/` | `design-review` | 59 行 | 换一个模型审设计质量（冗余、过度设计、归属选择），默认不开 |
| `plan_skill/` | `change-plan` | 110 行 | 开工前的计划形态：四栏模板、质询三问、终止判据、改完对账，以及四样审批图各自的判据（状态组合矩阵 / 约束拓扑 / 改动类图 / 决策表）；由 `post-change-gpt-review` 的 B 档（定要不要出图）和 C 档点名 |

## 非 skill 目录

这两个目录没有 `SKILL.md`，不参与 agent 发现，别按 skill 的规矩去改：

| 目录 | 放什么 | 谁读 |
|---|---|---|
| `cursor_rules/` | 常驻规则实体（`*.mdc`），`~/.cursor/rules/` 下是指向这里的软链 | agent，每次会话常驻 |
| `retros/` | AI 协作失败案例集，见该目录 `README.md` | 人 |

`cursor_rules/` 的软链方式与 skills 一致，但目标目录是 `~/.cursor/rules/`：

```bash
cd ~/work_space/skills/cursor_rules
for f in *.mdc; do rm -f ~/.cursor/rules/$f && ln -s "$PWD/$f" ~/.cursor/rules/$f; done
```

规则文件曾经在两处各存一份并分叉过一次（改了外部那份，仓库这份没跟上）。**只留软链，不要拷副本。**

`retros/` 的作用是给「同一类问题第二次出现」提供证据——`post-change-gpt-review.mdc` 卡了"第二次才写规则"的触发线，而凭记忆判断是不是第二次必然失败。改规则前先去那里翻同类案例。

## 安装约定

实体放本目录，只在 `~/.agents/skills/` 建一处软链，名字必须等于 frontmatter 里的 `name`：

```bash
cd ~/work_space/skills
ln -s "$PWD/<目录名>" ~/.agents/skills/<skill-name>
```

- 目录名用下划线（`android_view_wiki`），`name` 和软链名用连字符（`android-view-wiki`）——两者不一致会导致 skill 完全不被发现
- `name` 只允许小写字母、数字、连字符，≤64 字符
- 只建 `.agents` 一处就够：Cursor 同时扫 `~/.cursor/skills/` 和 `~/.agents/skills/`，两处都有时会去重，`.cursor` 侧属于冗余
- 禁止写入 `~/.cursor/skills-cursor/`，那是 Cursor 内置目录
- 这个位置只对本机生效。Cloud Agent、远程 SSH、自建 worker 读不到用户级目录，那些场景要用项目内的 `.agents/skills/`

验证软链有效：

```bash
ls -la ~/.agents/skills/ | grep work_space
head -3 ~/.agents/skills/<skill-name>/SKILL.md
```

## 两种类型的结构

**知识域 wiki**（本仓主体，查询用）：`SKILL.md` 只做路由 + 硬规则速查，细节分册进 `references/`。

```
<wiki 目录>/
├── SKILL.md              # 路由表 + 不读 reference 就该遵守的硬规则
├── references/
│   ├── <主题>.md          # 每篇结尾带「症状 → 排查」表
│   └── ...
└── scripts/              # 可选，只在「靠目测必然出错」时才加
    └── <工具>.py
```

`scripts/` 的收录判据比 reference 严：**这件事人（和 agent）目测会稳定看错，而它是机械可算的。** 目前只有 `android_view_wiki/scripts/layout-chain.py`——约束拓扑跨文件、锚点反向依赖要全文搜，目测漏一个就是一次返工。脚本只读不写、零第三方依赖、`--help` 说清接口。

硬约束：

- `SKILL.md` 必须写明「按需读、一次读一个，不要整包拉进上下文」
- 路由行按**症状**措辞（"点击没反应"、"被状态栏挡住"），不要只写技术模块名
- 新增 reference 必须同步更新路由表，否则永远不会被读到
- reference 之间用纯文件名互相指路（`见 animation.md`），不用 markdown 链接
- 版本敏感内容标 API 版本、不标日期；已失效的老 API 单列一处写明"写了也没用"，不要和正确做法混排

**配套工具型**（有明确执行流程）：`SKILL.md` 一个文件搞定，按「流程 → 严重级别 → 修改权限 → 输出格式」组织，步骤要给具体命令。

## 待建知识域

按"agent 出错率 × 日常频次"排的，建之前先确认边界不和已有 wiki 重叠：

- **Navigation 组件**——导航图与嵌套图、参数传递与 Safe Args、深链、返回栈操作与 `popUpTo`。`launchSingleTop` 去重、导航事件建模已在 `android-architecture-wiki` 的 `events.md`，任务栈层面的行为在 `android-component-wiki` 的 `tasks-backstack.md`，新建时只补导航图自身的配置与时序
- **Room 与数据持久化**——schema 迁移（自动与手动）、返回 `Flow` 的查询、事务与挂起函数、索引与查询计划。数据层的 SSOT 与缓存策略已在 `android-architecture-wiki` 的 `data-layer.md`，这里只补 Room 自身的 API 与迁移
- **测试**——`runTest` 与 `TestDispatcher`、`Turbine` 测 `Flow`、fake 与 mock 的取舍、Espresso 的等待与稳定性。`StateFlow` 测试和 fake 优先的原则已在 `android-architecture-wiki` 的 `layering-di.md`，注意别重复

## 改完之后

调 `optimize-skill` 自查（知识域 wiki 会追加走路由闭环、内容密度、内部一致、跨 wiki 边界四步检查）。P0/P1 修掉再收工。

## 发现路径

知识库建好了不等于会被用到，入口必须接线。目前有三条路径，改动 wiki 名字时三处都要同步：

- **自动路由**——靠各 `SKILL.md` 的 `description`，是主路径
- **常驻规则**——`cursor_rules/android-view.mdc`（软链到 `~/.cursor/rules/`）末尾按域分流到各 wiki
- **审查流程**——`review_skill` 的「判定依据」一节把各类疑问指向对应 wiki，配合 `post-change-gpt-review.mdc` 生效
- **体检流程**——`optimize_skill` 开头把 skill 写法的判定依据指向 `agent-skills-wiki`，自身只留流程
- **开工流程**——`post-change-gpt-review.mdc` 的 C 档和决策表末尾指向 `change-plan`，规则只留硬要求，模板在 skill 里

## 什么时候该回来复查

版本敏感内容会过期，标了「核实于」的地方尤其。这几个时机先更新 wiki 再动手，顺序反了就等于拿过期结论改代码：

- 升 AGP / Gradle → 先更 `android-gradle-wiki` 的兼容矩阵和破坏性变更清单
- 升 compileSdk / targetSdk → 先更 `android-sdk-behavior-wiki` 的升级清单和 Play 要求
- 官方废弃某个 API → 在对应 reference 里单列「写了也没用」，不要直接删掉旧写法，否则下次看到老代码判断不出它为什么错
- **实战中 agent 判断错了 → 把这个失败模式记进对应 wiki**，这比预先扩充新知识域有用得多

最后一条是这个仓库长期价值的来源：新域按需再建，已建的域靠真实失败反哺。

## 说明

- `.DS_Store` 之类系统文件不要带进 skill 目录，已在 `.gitignore` 里挡掉
