# description：触发机制与实测

## 触发是怎么发生的

启动时 agent 只加载所有 skill 的 `name` + `description`，用它判断当前任务要不要读全文。**description 承担了全部触发责任**——它没说清何时有用，skill 就不会被想起来。

写太窄 → 该触发时不触发；写太宽 → 不该触发时抢过来，还会和别的 skill 互相干扰。

一个容易忽略的前提：**agent 只在任务超出自身能力时才去查 skill**。"读一下这个 PDF"可能不触发 PDF skill，因为它自己就能做。skill 真正起作用的场景是陌生 API、领域特有工作流、罕见格式——这也意味着如果你的 skill 覆盖的是 agent 本来就会的事，再怎么改 description 都不会稳定触发。

## 写法四原则

**命令式措辞。** 框成对 agent 的指令，agent 在决定是否行动，就直接告诉它何时行动。

```yaml
# ❌ 陈述式
description: This skill helps with CSV analysis.
# ✅ 命令式
description: 分析 CSV 与表格数据……当用户有 CSV/TSV/Excel 文件、想探索或转换数据时使用。
```

**写用户意图，不写内部机制。** agent 拿用户的原话来匹配，不是拿你的实现来匹配。

**宁可激进。** 显式列举适用场景，**包括用户不点名领域的情况**——"even if they don't explicitly mention 'CSV' or 'analysis'"。本机场景必须含中文触发词：用户日常用中文提问，只有英文关键词会大面积漏触发。

**保持简短。** 几句到一小段。硬上限 1024 字符，但优化过程中 description 会不断膨胀，每轮都要回头量一次。

好坏对照：

```yaml
# ❌ 什么都没说
description: Helps with PDFs.
# ✅ 做什么 + 何时用，都具体
description: Extracts text and tables from PDF files, fills PDF forms, and merges multiple PDFs. Use when working with PDF documents or when the user mentions PDFs, forms, or document extraction.
```

## 触发率实测

凭感觉改 description 只能改出自己看着顺眼的版本。要量，就需要一组标注好的 query。

### 设计 query 集

约 20 条，应触发 / 不应触发各 8~10 条。

**正例**要在几个轴上分散：措辞正式度（有的规范、有的口语、有的带错别字）、是否直接点名领域（"分析这个 CSV" vs "我领导要我从这个数据文件出个图"）、详略程度（极简的和带路径列名背景的）、步骤复杂度（单步的和多步的，测试 skill 相关的那一步埋在长链条里时还能不能被认出来）。

**最有价值的正例是"skill 确实有用但从 query 字面看不出关联"的那些**。query 已经把 skill 的功能问出来了的话，任何合理 description 都会触发，测不出措辞差异。

**负例必须是近似命中**——共享关键词或概念但实际需要别的东西。对一个 CSV 分析 skill：

| query | 好不好 | 为什么 |
|---|---|---|
| `写个斐波那契函数` | ❌ | 毫不相关，什么也测不出 |
| `今天天气怎么样` | ❌ | 零关键词重叠，太容易 |
| `我要改 Excel 预算表里的公式` | ✅ | 共享"表格""数据"概念，但需要的是 Excel 编辑 |
| `写个 python 脚本读 csv 然后每行传到 postgres` | ✅ | 涉及 CSV，但任务是 ETL 不是分析 |

真实感很重要：带文件路径（`~/Downloads/report_final_v2.xlsx`）、个人语境（"我领导让我…"）、具体列名和公司名、口语和缩写。

```json
[
  { "query": "我有个表格在 ~/data/q4.xlsx，C 列收入 D 列支出，帮我加一列利润率并把低于 10% 的标出来", "should_trigger": true },
  { "query": "把这个 json 转成 yaml 最快的办法是啥", "should_trigger": false }
]
```

### 跑法

模型行为不确定，同一条 query 可能这次触发下次不触发。**每条跑 3 次算触发率**，阈值 0.5：正例触发率高于阈值算过，负例低于阈值算过。20 条 × 3 次 = 60 次调用，必须写脚本。

检测"是否触发"的方式随客户端不同——看执行日志、tool call 历史或 verbose 输出里有没有加载这个 skill 的 `SKILL.md`。如果客户端支持，**一旦结果明确就提前终止该次运行**（agent 要么去读了 skill、要么直接开始干活），能显著省时间和成本。

## 防过拟合：训练 / 验证划分

拿全部 query 去调 description，会调出一个只对这些措辞有效的版本。

- **训练集约 60%**：用来发现失败项、指导修改
- **验证集约 40%**：只用来检查改动是否泛化，**迭代过程中绝对不看**
- 两边都要有正负例的比例混合，别把正例全划进一边；随机打乱后**固定下来**，否则每轮不可比

## 优化循环

1. 在训练集和验证集上都跑一遍当前 description。训练集结果指导修改，验证集结果只用来判断改动是否泛化。
2. 找训练集里的失败项：哪些正例没触发、哪些负例误触发。
3. 改 description，重点在**泛化**：
   - 正例漏触发 → 描述太窄，扩大范围或补充"什么时候有用"的语境
   - 负例误触发 → 描述太宽，补充**它不做什么**，或划清与相邻能力的边界
   - **不要把失败 query 里的关键词直接抄进 description**，那就是过拟合。要找出这些 query 代表的一般类别，去处理那个类别
   - 连着几轮没进展就换个**结构上不同**的写法，别继续做增量微调
   - 每轮回头量字符数，别超 1024
4. 重复 1~3，直到训练集全过或不再有明显改进。
5. **按验证集通过率挑最优版本——最优版本很可能不是最后一版**，后面几轮可能已经在往训练集上过拟合。

5 轮通常够。还不见效，问题大概在 query 集（太易、太难、标错了）而不在 description。

改造前后：

```yaml
# 改前
description: Process CSV files.
# 改后
description: >
  Analyze CSV and tabular data files — compute summary statistics,
  add derived columns, generate charts, and clean messy data. Use this
  skill when the user has a CSV, TSV, or Excel file and wants to
  explore, transform, or visualize the data, even if they don't
  explicitly mention "CSV" or "analysis."
```

改后同时做了两件事：**做什么更具体**（汇总统计、派生列、图表、清洗），**何时适用更宽**（CSV/TSV/Excel，且不依赖用户说出关键词）。

## 应用结果

1. 更新 `SKILL.md` 的 `description`
2. 确认 ≤1024 字符
3. 另写 5~10 条**全新** query（正负混合）跑一遍。这些 query 没参与过优化，才是对泛化能力的诚实检验

## 症状 → 排查

| 症状 | 排查 |
|---|---|
| 该触发时没触发 | 先确认不是「触发是怎么发生的」末段那种情况——skill 覆盖的是 agent 本来就会的事；否则按「优化循环」第 3 条扩大范围 |
| 不该触发时抢了过来 | 补充"不做什么"或与相邻 skill 划边界；用近似命中的负例验证 |
| 用户用中文问就不触发 | description 缺中文触发词，见「写法四原则」 |
| 两个 skill 互相抢或互相漏 | 列出各自 description 的触发词，重叠的词就是走错门的地方 |
| 改了好几版，自己测着好但实际还是漏 | 在做过拟合，见「防过拟合」——必须有没参与优化的验证集 |
| 不知道改动有没有真的变好 | 触发率要量，见「触发率实测」；输出质量是另一件事，见 evaluation.md |
| description 越改越长 | 每轮量字符数，1024 是硬上限 |
