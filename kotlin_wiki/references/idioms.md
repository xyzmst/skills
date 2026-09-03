# 惯用写法与 Java 模式对照

## 字符串

模板优先。只有在循环里拼大文本时才用 `StringBuilder` / `buildString`。

```kotlin
// ❌
val msg = "user=" + user.id + ", age=" + user.age

// ✅
val msg = "user=${user.id}, age=${user.age}"

// ✅ 循环拼大文本才这样
val csv = buildString {
    rows.forEach { appendLine("${it.id},${it.name}") }
}
```

多行文本用 `"""..."""` + `trimIndent()`，别手工拼 `\n`。

## 空安全

| 场景 | 写法 |
|---|---|
| 链式取值 | `a?.b?.c` |
| 兜底值 | `value ?: default` |
| 提前返回 | `val x = maybe ?: return`（lambda 里 `?: return@name`） |
| 抛异常 | `requireNotNull(x) { "x 不能为空" }` |
| 非空才执行 | `x?.let { ... }` |
| 两个都非空 | `if (a != null && b != null)`，别套两层 `let` |

`!!` 只在能当场证明非空时用（刚判过、刚赋过值）。想不清楚就用 `?: return`。

`lateinit` 适合"稍后一定会初始化且不为空"的场景，访问前可用 `::x.isInitialized` 判断。不能用于基本类型。

## 分支

```kotlin
// ❌ Java 式长链
if (type == 1) { ... } else if (type == 2) { ... } else { ... }

// ✅
when (type) {
    1 -> ...
    2 -> ...
    else -> ...
}

// ✅ 无参 when 替代复杂条件链
val level = when {
    score >= 90 -> "A"
    score >= 60 -> "B"
    else -> "C"
}
```

`when` 作为表达式覆盖 `sealed` / `enum` 时**不要写 `else`**，将来加分支编译器会报错提醒。写了 `else` 就失去这个保护。

## 集合

```kotlin
// ❌ Java 式
val result = mutableListOf<String>()
for (u in users) {
    if (u.age > 18) result.add(u.name)
}

// ✅
val result = users.filter { it.age > 18 }.map { it.name }
```

常用：

| 目的 | 写法 |
|---|---|
| 找第一个/找不到返回 null | `firstOrNull { }` |
| 是否存在 | `any { }` / `none { }` |
| 转 Map | `associateBy { it.id }` |
| 分组 | `groupBy { it.type }` |
| 空集合兜底 | `list.orEmpty()` |
| 过滤空元素 | `listOfNotNull(a, b)` / `mapNotNull { }` |
| 求和 | `sumOf { it.price }` |
| 拼接展示 | `joinToString(", ") { it.name }` |

链式操作每步都产生中间集合。数据量大（数千以上）或链路长时用 `asSequence()` 惰性求值，末尾 `toList()`。小集合用 Sequence 反而更慢。

## 作用域函数

| 函数 | 上下文 | 返回 | 典型用途 |
|---|---|---|---|
| `let` | `it` | lambda 结果 | 非空判断后处理、转换 |
| `apply` | `this` | 接收者 | 配置对象后返回自身 |
| `also` | `it` | 接收者 | 副作用（打日志、埋点） |
| `run` | `this` | lambda 结果 | 需要接收者上下文并返回结果 |
| `with` | `this` | lambda 结果 | 对同一对象多次操作 |
| `takeIf` | `it` | 自身或 null | 条件过滤成可空 |

只在能减少样板时用。嵌套超过两层就该抽方法——嵌套时 `it` 会被内层遮蔽，可读性骤降。需要嵌套时给参数命名：`outer.let { user -> inner.let { order -> ... } }`。

## 函数与参数

```kotlin
// ❌ Java 式重载
fun show(msg: String) = show(msg, 0)
fun show(msg: String, duration: Int) { ... }

// ✅ 默认参数
fun show(msg: String, duration: Int = 0) { ... }
```

参数超过 3 个，或有同类型相邻参数时，调用处用具名实参：`show(msg = "hi", duration = 1)`。

单表达式函数省掉大括号和 `return`：`fun double(x: Int) = x * 2`。

## 相等与比较

`==` 调 `equals`（结构相等），`===` 才是引用相等。Java 的 `equals` 习惯直接用 `==` 即可。

比较可空值：`a == b` 本身就处理了 null，不用先判空。

## 类型转换

```kotlin
// ✅ 安全转换 + 兜底
val text = value as? String ?: return

// ✅ 智能转换：is 判断后自动转
if (value is String) {
    println(value.length)   // 不用再强转
}
```

`var` 属性、其他模块的属性无法智能转换，先赋给局部 `val`。

## 症状 → 排查

| 想写什么 / 遇到什么 | 看 |
|---|---|
| 一长串判空、`!!` 满天飞 | 「空安全」 |
| 智能转换报"无法智能转换" | 「类型转换」——`var` 和跨模块属性不行，先赋给局部 `val` |
| `as` 抛 `ClassCastException` | 「类型转换」——用 `as?` 加兜底 |
| 不知道该用 `let` / `run` / `apply` / `also` / `with` | 「作用域函数」 |
| 集合处理写成了 for 循环手动累加 | 「集合」 |
| 为不同参数组合写了一堆重载 | 「函数与参数」——用默认参数和具名参数 |
| `==` 与 `===` 的区别、判等结果意外 | 「相等与比较」 |
| 多分支 `if/else if` 链很长 | 「分支」——用 `when` |
| 字符串拼接、多行文本、格式化很啰嗦 | 「字符串」 |

只讲怎么写得地道。运行时行为出错（取消被吞、平台类型 NPE、`StateFlow` 去重）见 pitfalls.md。
