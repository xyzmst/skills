---
name: kotlin-wiki
description: Kotlin 语法与惯用写法知识库，覆盖惯用法与 Java 模式对照、协程与 Flow、类型与 API 设计、常见陷阱。当需要确认某个 Kotlin 写法是否地道、排查协程/Flow 行为异常、设计 Kotlin API、或把 Java 风格代码改成 Kotlin 时使用。
---

# Kotlin Wiki

查询型知识库。只在**需要确认写法**时读对应 reference，一次读一个，不要整包拉进上下文。

## 路由

| 问题 | 读 |
|---|---|
| 这样写地道吗？Java 模式怎么改？字符串、空安全、`when`、集合、作用域函数 | [references/idioms.md](references/idioms.md) |
| 协程作用域、取消、`suspend`、Flow 冷热流、`stateIn`、异常处理 | [references/coroutines-flow.md](references/coroutines-flow.md) |
| `data`/`sealed`/`value class`、扩展函数、委托、可见性、API 设计 | [references/types-api.md](references/types-api.md) |
| 行为和预期不符、疑似踩坑、Java 互操作 NPE、性能异常 | [references/pitfalls.md](references/pitfalls.md) |

判断不了归哪类时，优先读 `pitfalls.md`。

## 硬规则速查

不用读 reference 就该遵守的：

- 字符串用模板 `"$x"` / `"${a.b}"`，不用 `+` 拼接、不用 `StringBuilder` 拼日志
- 空安全用 `?.` `?:` `?: return`；`!!` 只在当场能证明非空时用
- 默认 `val`；集合对外暴露只读 `List`，可变的留私有
- `when` 覆盖 `sealed`/`enum` 时不写 `else`，让编译器检查漏分支
- 协程用 `viewModelScope` / `lifecycleScope`，禁止 `GlobalScope`
- `runCatching` 会吞 `CancellationException`，协程里别用（见 pitfalls）

## 判断标准

写完自问：**这段直译回 Java 几乎不用改吗？** 是的话说明还在用 Java 思路写 Kotlin。

## 扩展

同类知识库按技术域各建一个目录，保持 `SKILL.md` 路由 + `references/` 细节的结构：

```
<skill 源目录>/
├── kotlin-wiki/
│   ├── SKILL.md
│   └── references/
├── android-view-wiki/      # View 层：测量布局、动画、约束、列表、触摸、渲染
└── <其他技术域>-wiki/
```

新增 reference 时同步更新上面的路由表，否则不会被命中。
