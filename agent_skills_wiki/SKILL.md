---
name: agent-skills-wiki
description: Agent Skills 规范与写作知识库，覆盖 SKILL.md 字段约束、渐进式披露与体积预算、description 触发机制与触发率实测、正文密度与规定程度校准、Gotchas/模板/校验循环等结构模式、带脚本时的 agent 友好接口、以及用 eval 证明 skill 有价值。当需要新建或改写 skill、判断某个 skill 该不该存在、写或修 description、skill 没触发或触发过头、SKILL.md 太长要拆 references、不确定正文该写多细多硬、给 skill 配脚本、或想验证改完到底有没有变好时使用。
---

# Agent Skills Wiki

查询型知识库，对象是 [Agent Skills 开放规范](https://agentskills.io)。只在**需要确认做法**时读对应 reference，一次读一个，不要整包拉进上下文。

给已有 skill 做体检并修复走 `optimize-skill`，那是执行流程；这里只提供判定依据。

## 动手前的三个问题（最重要）

新建或大改一个 skill 之前，按顺序回答：

1. **不带这个 skill，agent 现在就做不好吗？** 做得好就**不要建**。skill 的价值来自补上 agent 不具备的上下文，不是把它已经会的事再说一遍。
2. **内容从哪来？** 只有两个合法来源：**真实任务里你做过的纠正**（"用 X 不用 Y"、"注意边界 Z"），和**项目自有产物**（review 评论、修复补丁、故障案例、内部约定）。让模型凭通用知识生成，产出必然是"妥善处理错误""遵循最佳实践"这类空话。
3. **每一段：没有它，agent 会做错吗？** 答否就删。

第 1 问答不出具体的"会错成什么样"，就是不该建。第 2 问只有通用知识可写，说明这个域压根不需要 skill。

判断信号：**同一条规则加进去两次都没让结果变好，不要加第三次，改成删指令。**通过率加规则后不升，通常是过度约束而不是约束不够。

## 路由

| 问题 | 读 |
|---|---|
| 字段怎么填、`name` 与目录名、正文多长算超、按需加载分几层、装在哪、项目级和用户级冲突 | [references/spec.md](references/spec.md) |
| 没触发 / 不该触发时触发了、description 怎么措辞、怎么量触发率、怎么防过拟合 | [references/description.md](references/description.md) |
| 正文写什么删什么、范围划多大、指令该多硬、什么时候拆 `references/` 以及怎么写指路 | [references/authoring.md](references/authoring.md) |
| 要固定输出格式、多步流程漏步、批量或破坏性操作、环境特有的坑往哪放 | [references/patterns.md](references/patterns.md) |
| 改完不知道有没有变好、怎么证明 skill 有价值、断言怎么写、加了规则没效果 | [references/evaluation.md](references/evaluation.md) |
| 要带脚本、脚本挂住不返回、agent 读不懂脚本输出、输出被截断 | [references/scripts.md](references/scripts.md) |

判断不了归哪类时：触发相关读 `description.md`，正文内容相关读 `authoring.md`，字段和数值限制读 `spec.md`。

## 硬规则速查

不用读 reference 就该遵守的：

- `name` **必须等于父目录名**，只允许小写字母/数字/连字符，≤64 字符，不能首尾带连字符也不能连续 `--`
- `description` ≤1024 字符，必须同时含 **WHAT（能力）+ WHEN（触发场景）**，WHEN 用命令式措辞（"当需要…时使用"），不写成"本 skill 用于…"
- description 要**激进列举场景**，包括用户没点名领域的情况；本机场景必须含中文触发词，只有英文关键词会大面积漏触发
- description 里含冒号的值必须加引号，`description: Use when: ...` 是**无效 YAML**
- `SKILL.md` 控制在 **500 行 / 5000 token** 以内，超了把长清单、FAQ、字段字典移进 `references/`
- 拆分后**必须写明什么条件下读哪个文件**（"API 返回非 200 时读错误处理那篇"这种带触发条件的措辞）；"细节见 references/" 等于永远不会被读
- 正文必须写明"按需读、一次读一个，不要整包拉进上下文"，缺这句 agent 会把整个 `references/` 拉进来
- **Gotchas（违反合理假设的环境事实）必须留在 `SKILL.md`**，挪进 `references/` 就永远不会在踩坑前被读到——agent 认不出该加载它的时机
- 文件引用用相对路径（相对 skill 根目录），**只一层深**，不做嵌套引用
- **给默认值，不给菜单**：并列四个等价方案会让 agent 在选择上浪费 turn，定一个默认 + 一句逃生出口
- **讲清 why 胜过 ALWAYS/NEVER**：多种做法都成立的地方解释目的，只有脆弱、必须按序的操作才写死
- 写方法不写答案：指令要能泛化到同类任务，不是只对一个实例有效
- 带脚本时**禁止任何交互式提示**，agent 在非交互 shell 里跑，等 TTY 输入会永久挂住
- 脚本**数据走 stdout、诊断走 stderr**；输出可能大时默认给摘要（多数框架在 10~30K 字符处截断）
- 不确定某条该不该留时，**先删掉跑一遍**，比先加上去更容易看出它有没有用

## 判断标准

改完自问：**这段进上下文，会改变 agent 的行为吗？** 不会就是在烧 token。
