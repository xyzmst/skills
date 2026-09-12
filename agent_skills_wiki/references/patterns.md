# 结构模式

可复用的组织手法。不是每个 skill 都要全用，按任务挑。

## Gotchas 段落（价值最高）

很多 skill 里最有用的内容就是一张 gotchas 清单：**违反合理假设的环境特有事实**。不是通用建议（"妥善处理错误"），而是对 agent 必然会犯的错的具体纠正。

```markdown
## Gotchas
- `users` 表是软删除。查询必须带 `WHERE deleted_at IS NULL`，
  否则结果里会混进已停用账号。
- 同一个用户 ID：数据库里叫 `user_id`，认证服务里叫 `uid`，
  计费 API 里叫 `accountId`。三个指的是同一个值。
- `/health` 只要 web server 在跑就返 200，数据库连接断了也一样。
  要查完整服务健康度用 `/ready`。
```

**必须留在 `SKILL.md` 里。**放 `references/` 的前提是你能告诉 agent 何时加载它，但 gotchas 的本质是"违反直觉"——agent 根本认不出自己正走向那个坑，也就不会去读。要在它遇到之前就摆在眼前。

**每次你纠正 agent 一个错误，就把这个纠正补进 gotchas。**这是迭代 skill 最直接、性价比最高的方式。

## 输出模板

需要固定输出格式时给模板，比用散文描述格式可靠得多——模型擅长对着具体结构做模式匹配。

短模板内联在 `SKILL.md`；长的、或只在特定情况需要的放 `assets/`，从正文引用，这样只在用到时才加载。

```markdown
## 报告结构
按这个模板，具体分析可按需调整章节：

    # [分析标题]
    ## 执行摘要
    [一段话概述关键发现]
    ## 关键发现
    - 发现 1，附支撑数据
    ## 建议
    1. 具体可执行的建议
```

模板里**用占位符，不要写死示例文案**，否则会被原样照抄进输出。

## Checklist

多步流程、尤其步骤间有依赖或校验关卡时，显式清单能帮 agent 跟踪进度、不跳步。

```markdown
## 表单处理流程
进度：
- [ ] 1 分析表单（跑 scripts/analyze_form.py）
- [ ] 2 建立字段映射（编辑 fields.json）
- [ ] 3 校验映射（跑 scripts/validate_fields.py）
- [ ] 4 填表（跑 scripts/fill_form.py）
- [ ] 5 验证输出（跑 scripts/verify_output.py）
```

## Validation loop

让 agent 在往下走之前先自验证。模式是：做完 → 跑校验 → 修问题 → 重跑，直到通过。

```markdown
## 编辑流程
1. 做修改
2. 跑校验：`python scripts/validate.py output/`
3. 校验失败时：读错误信息 → 修 → 重新校验
4. 只有校验通过才继续
```

校验器不一定是脚本，一份参考文档也可以充当——让 agent 在收尾前对着参考清单核一遍自己的产出。

## Plan-validate-execute

批量或破坏性操作用这个：先产出结构化的中间计划，**对着事实源校验**，再执行。

```markdown
## PDF 表单填写
1. 提取表单字段：`python scripts/analyze_form.py input.pdf` → `form_fields.json`
   （列出每个字段名、类型、是否必填）
2. 建 `field_values.json`，把字段名映射到要填的值
3. 校验：`python scripts/validate_fields.py form_fields.json field_values.json`
   （检查字段名都存在、类型兼容、必填项没漏）
4. 校验失败就改 `field_values.json` 再校验
5. 填表：`python scripts/fill_form.py input.pdf field_values.json output.pdf`
```

**关键是第 3 步**：一个把计划（`field_values.json`）对照事实源（`form_fields.json`）校验的脚本。而且错误信息必须带可选项：

```
Field 'signature_date' not found — available fields: customer_name, order_total, signature_date_signed
```

这样 agent 才有足够信息自我纠正。只说"字段不存在"会浪费一个 turn。

## 打包脚本

迭代 skill 时对比多个测试用例的执行 trace。如果发现 agent **每次都在重新发明同一段逻辑**——画图、解析某个特定格式、校验输出——那就是信号：写一次测试过的脚本，放进 `scripts/`。

接口怎么设计见 scripts.md。

## 症状 → 排查

| 症状 | 排查 |
|---|---|
| 环境特有的坑该放哪 | 「Gotchas 段落」——必须在 `SKILL.md`，不能挪 `references/` |
| agent 反复犯同一个错 | 把纠正补进 gotchas，这是最直接的迭代方式 |
| 输出格式每次不一样 | 「输出模板」，给结构比描述格式可靠 |
| 输出里出现了模板的示例文案 | 模板里写死了示例，改成占位符 |
| 多步流程漏步或乱序 | 「Checklist」 |
| 产出有错但 agent 直接交了 | 「Validation loop」，让它自验证后才往下 |
| 批量 / 破坏性操作出错代价大 | 「Plan-validate-execute」，重点是那个对照事实源的校验脚本 |
| 校验失败但 agent 改不对 | 错误信息没带可选项，见 plan-validate-execute 末段 |
| 每次运行都在写同样的临时脚本 | 「打包脚本」，沉到 `scripts/` |
