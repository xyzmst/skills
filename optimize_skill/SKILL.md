---
name: optimize-skill
description: Audit and optimize an existing Cursor/agent skill - install location, description hit rate, token cost, duplication with other skills and rules, and instruction executability. Use when the user asks to 优化 skill、体检 skill、review 一个 skill、这个 skill 写得对不对、skill 没触发、SKILL.md 太长、精简 skill.
disable-model-invocation: true
---

# Optimize Skill

对指定 skill 做体检并修复。判断标准只有一条：**这个 skill 能不能在该触发的时候被触发，触发后能不能让 agent 少走弯路、少烧 token。**

全程在当前对话内完成，禁止启动 Subagent / Task。

## 审查流程

1. 定位
   - 读目标 `SKILL.md` 全文，`wc -l` 记行数。
   - `ls -la ~/.cursor/skills/ ~/.agents/skills/` 确认它是否真的被安装、软链是否解析成功。
   - 只在有重复嫌疑时才去看别的 skill，且只读 frontmatter（`sed -n '1,8p'`），不要整篇拉进上下文。
   - 判断形态：`SKILL.md` 只做路由、细节分册在 `references/` 的属知识库/查询型，6 步走完后追加下面的「知识库型追加检查」。

2. 检查能否被发现（第一生死线）
   - 实体目录或软链必须位于 `~/.cursor/skills/` 或项目 `.cursor/skills/`；`.agents` 生效则需 `~/.agents/skills/`。不在这些目录下 = 完全不生效。
   - 软链名必须等于 frontmatter `name`；`name` 为小写字母/数字/连字符，≤64 字符。
   - 禁止写入 `~/.cursor/skills-cursor/`（Cursor 内置保留目录）。
   - 本机安装约定：实体放 `~/work_space/skills/<dir>/`，只软链到 `~/.agents/skills/<name>` 一处，保证只有一份源。Cursor 同时扫 `.cursor` 和 `.agents` 并去重，两处都建属冗余，不要当成缺陷报。

3. 检查 description（第二生死线）
   - 第三人称，同时含 WHAT（能力）和 WHEN（触发场景），≤1024 字符。
   - 必须含中文触发词——用户日常用中文提问，只有英文关键词会大面积漏触发。
   - 与其他 skill 的 description 不得含义重叠，否则互相抢或互相漏。
   - 该自动触发的不要加 `disable-model-invocation: true`；只想显式调用的必须加。

4. 检查 token 成本
   - `SKILL.md` 超 500 行必须拆：长清单、FAQ、字段字典、参数表移到 `references/`，正文只留路由说明，命中场景才读，一次只读一个。
   - 删掉 agent 本就知道的常识解释、persona 空话、同义反复。
   - 文件引用只允许一层深，不做嵌套引用。
   - 每段自问：这段进上下文，值不值。

5. 检查冲突与重复
   - 与 `~/.cursor/rules/` 下 `alwaysApply: true` 的规则是否讲同一件事。重复会双份注入，且两边格式不一致时 agent 会随机二选一。
   - 同一件事只保留一份权威描述：rule 只留触发条件并按名字指向 skill，细节全在 skill。
   - rule/skill 内不要硬编码绝对路径，按 skill 名引用，避免挪目录后失效。

6. 检查指令可执行性
   - 步骤是否给了具体命令，还是让 agent 每次自己拼。
   - 命令是否真能覆盖声称的场景（典型错误：用 `git diff` 却漏掉 staged 改动，用 `git diff --check` 当正确性验证）。
   - 输出模板里不要写死示例文案，用占位符，否则会被原样照抄。
   - 全局约束（如禁用 Subagent、语言、权限）放开头或独立小节，不要埋在某个步骤里。
   - 术语前后统一；多方案要给默认值加逃生口，不要并列一堆选项。
   - 带脚本时：无 Windows 风格路径，依赖和用法已声明，说明是"执行"还是"阅读"。

## 知识库型追加检查

仅当目标是知识库/查询型 skill 时走这一节。

7. 检查路由闭环
   - `ls references/` 逐个对照路由表：没被路由指向的文件永远不会被读到（P1）；路由指向不存在的文件同样是 P1。
   - 路由行按**症状**措辞（"点击没反应"、"被状态栏挡住"），不要只写技术模块名——agent 是带着现象来查的，不是带着模块名来的。
   - 正文必须写明"按需读、一次读一个，不要整包拉进上下文"，缺这句 agent 会把整个 `references/` 拉进来（P1）。

8. 检查内容密度
   - 每条自问：agent 凭训练数据是不是本来就知道。只留版本敏感、反直觉、必然写错的，常识解释和文档搬运一律删。
   - 版本敏感内容标 API 版本、不标日期；已失效的老 API 单列一处写明"写了也没用"，不要和正确做法混排。
   - 每个 reference 结尾要有「症状 → 排查」表。只有原理讲解、没有症状映射的要补，否则 agent 判断不出该读哪个文件。

9. 检查内部一致
   - 同一 skill 内两个 reference 讲同一件事时，agent 会随机读一个：合并，或划清边界并互相指路。
   - reference 之间用纯文件名提及（`见 animation.md`），不用 markdown 链接，避免嵌套引用引发连环读。

10. 检查跨 wiki 边界
   - 同一技术域有多个 wiki 时（如 Kotlin / View / 架构 / 版本行为），先列出各 `SKILL.md` 的 description 触发词，重叠的词就是 agent 会走错门的地方。
   - 同一知识点出现在两个 wiki 里：结论必须一致，且各自标明"这里讲哪一面、另一面看某 wiki 某文件"，否则改一处另一处就变成错的（P1）。
   - 检查配套的 always-applied rule 和任务型 skill 有没有指向对应 wiki：知识库建了但入口没接线，等于没建。

## 严重级别

- **P0**：skill 不生效或必然被漏触发——位置错误、软链断裂、frontmatter 无法解析、`name` 与软链不一致。
- **P1**：现实场景会出错——description 缺关键触发词、与 alwaysApply 规则重复冲突、命令无法达到声称效果、正文超长明显烧 token、知识库路由断裂（孤儿 reference 或指向不存在的文件）。
- **P2**：措辞冗余、结构可优化、可维护性问题。

每条问题必须包含：

1. `文件:行号`
2. 会导致的具体后果（漏触发 / 行为错 / 多烧多少上下文）
3. 最小修复建议

拿不出具体后果的不要输出。不要把作者刻意的设计取舍当缺陷。

## 修改权限

- 直接修 P0/P1，改完重读最终文件再汇报。
- P2 只报告，不顺手改。
- 移动或删除文件前先复制并 `diff -q` 校验，确认内容一致再删旧的。
- 改动 skill 的安装位置后，必须重新验证软链能读到 `SKILL.md`。

## 输出格式

```markdown
结论：可用 / 有阻断问题

P0
- 无 / [文件:行号] 问题、后果、最小修复

P1
- 无 / ...

P2
- 无 / ...

已修改
- <文件>：<改了什么、为什么>

验证
- 已执行：<实际执行的命令>
- 验证缺口：<无法验证的部分>
```

同时点出写得好、应当保留的部分，避免下次被误改掉。
