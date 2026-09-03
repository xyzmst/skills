# 常见陷阱

按"现象 → 原因 → 处理"组织。行为和预期不符时先在这里找。

## runCatching 吞掉协程取消

**现象**：协程该取消时没停，或 `finally` 逻辑错乱。

`runCatching` 捕获所有 `Throwable`，包括 `CancellationException`——那是协程正常的取消信号，被吞掉后结构化并发失效。

```kotlin
// ❌ 协程里
val r = runCatching { api.load() }

// ✅
try {
    api.load()
} catch (e: CancellationException) {
    throw e
} catch (e: Exception) {
    Logger.exp(TAG, e, "load failed")
}
```

同理，`catch (e: Exception)` / `catch (e: Throwable)` 在协程里都要先放行 `CancellationException`。

## 平台类型导致的 NPE

**现象**：调 Java 返回值时莫名 NPE，编译期没报错。

Java 返回的类型是"平台类型"（`String!`），Kotlin 不做空检查，直接当非空用就会在赋值处炸。

处理：接收 Java 返回值时显式声明可空类型，或加 `?:` 兜底。

```kotlin
val name: String? = javaObj.getName()
val safe = javaObj.getName() ?: ""
```

## data class copy 绕过校验

**现象**：明明 `init` 里校验了，还是出现非法值。

```kotlin
data class Age(val value: Int) {
    init { require(value >= 0) }
}
Age(1).copy(value = -1)   // init 不执行，校验形同虚设
```

处理：需要强校验的类不用 `data class`，或私有化构造器 + 工厂方法创建。

## Fragment 里用错 lifecycleScope

**现象**：Fragment 返回后回调触发，访问 binding 崩溃。

Fragment 的 `lifecycleScope` 绑 Fragment 实例，View 销毁后仍存活；`viewLifecycleOwner.lifecycleScope` 才随 View 销毁。

收集 UI 状态用后者，并配 `repeatOnLifecycle(STARTED)`。

## 扩展函数没有多态

**现象**：子类的扩展函数没被调用。

扩展函数编译期按**声明类型**静态分派。需要多态行为就定义成成员函数。

```kotlin
val x: Base = Derived()
x.ext()   // 调的是 Base.ext()
```

同名成员函数永远优先于扩展函数。

## 作用域函数 it 遮蔽

**现象**：嵌套 `let` 里改错了对象。

内层 `it` 遮蔽外层 `it`，看着像操作外层实际是内层。

处理：嵌套时给参数命名 `let { user -> }`；嵌套超过两层直接抽方法。

## 集合链式的中间对象

**现象**：大数据量下 `filter().map().first()` 很慢或内存抖动。

每个操作符都产生一个新集合，且是**急切求值**——`first()` 之前已经把整个列表 map 完了。

处理：数据量大或链路长时用 `asSequence()` 惰性求值。小集合（几十个）用 Sequence 反而有额外开销。

```kotlin
list.asSequence().filter { }.map { }.first()
```

## 可变集合被外部修改

**现象**：内部状态莫名被改。

```kotlin
// ❌ 返回的是同一个可变实例的引用
private val _items = mutableListOf<Item>()
val items: List<Item> get() = _items   // 调用方强转回 MutableList 就能改
```

处理：返回 `_items.toList()` 拷贝，或用不可变集合重新赋值。

## StateFlow 去重导致事件丢失

**现象**：连续两次相同的事件只响应了一次。

`StateFlow` 内建 `distinctUntilChanged`，值相等就不发射。

处理：一次性事件用 `SharedFlow`（或 `Channel`），不要用 `StateFlow`。

## StateFlow 持有可变对象

**现象**：改了状态但 UI 不刷新。

修改对象内部字段后，引用没变、`equals` 也相等，`StateFlow` 认为没变化。

处理：状态类用 `data class` + 全不可变字段，更新时 `_state.value = old.copy(...)`。

## 内部类持有外部引用

**现象**：Activity/Fragment 泄漏。

Kotlin 的 `inner class`、匿名 `object` 表达式、非 `object` 的 lambda 都可能隐式持有外部实例。

处理：不需要外部引用时用嵌套类（不加 `inner`）；长生命周期回调用弱引用或在销毁时注销。

## by lazy 的线程安全开销

`by lazy { }` 默认 `SYNCHRONIZED` 模式，每次访问有同步开销。确定只在单线程（如主线程）访问时用 `LazyThreadSafetyMode.NONE`。

## companion object 属性的访问开销

`companion object` 里的普通 `val` 会生成静态 getter 方法，高频路径上有额外调用。基本类型和 String 用 `const val` 直接内联。

## 默认参数对 Java 不可见

**现象**：Java 代码调 Kotlin 函数报参数不匹配。

默认参数只对 Kotlin 生效。需要 Java 调用时加 `@JvmOverloads` 生成重载。

## init 与属性初始化顺序

**现象**：`init` 块里读某属性拿到 null 或默认值。

`init` 块和属性初始化器**按声明顺序**执行。`init` 在后声明的属性之前跑，就读不到值。

处理：把 `init` 块放到依赖的属性声明之后。

同理，父类构造器里调用被子类覆写的方法（open 方法），此时子类属性还没初始化。

## 泛型擦除

`is List<String>` 编译不过——运行时拿不到泛型参数。需要类型判断时用 `reified` 内联函数，或传 `Class<T>`。

## 浮点与整数除法

`1 / 2` 是 `0`（整数除法）。要小数结果先转类型：`1 / 2.0`。

金额计算别用 `Double`，用 `BigDecimal` 或整数分。

## 数组判等

`arrayOf(1) == arrayOf(1)` 是 `false`（比引用）。内容判等用 `contentEquals`，嵌套数组用 `contentDeepEquals`。

`data class` 里放数组会让 `equals` 不可靠，改用 `List`。

## 症状 → 排查

| 症状 | 优先查 |
|---|---|
| 协程取消后行为异常、清理没跑 | 「runCatching 吞掉协程取消」 |
| 明明声明了非空却 NPE | 「平台类型导致的 NPE」——Java 来的值 |
| 对象绕过了构造校验拿到非法状态 | 「data class copy 绕过校验」 |
| Fragment 里协程在 View 销毁后还更新界面 | 「Fragment 里用错 lifecycleScope」 |
| 子类没有走到重写的扩展函数 | 「扩展函数没有多态」——静态分发 |
| 嵌套 `let`/`apply` 里的 `it` 指向了外层 | 「作用域函数 it 遮蔽」 |
| 事件只触发一次、相同值不再通知 | 「StateFlow 去重导致事件丢失」 |
| 改了对象内容但 `StateFlow` 不发射 | 「StateFlow 持有可变对象」——要换新实例 |
| 外部拿到集合后改掉了内部状态 | 「可变集合被外部修改」 |
| Activity/View 被内部类持有导致泄漏 | 「内部类持有外部引用」 |
| Java 侧调不到带默认参数的方法 | 「默认参数对 Java 不可见」——加 `@JvmOverloads` |
| 属性初始化时读到 null 或 0 | 「init 与属性初始化顺序」 |
| 除法结果意外为 0、金额有误差 | 「浮点与整数除法」 |
| 数组判等永远 false | 「数组判等」——用 `contentEquals` |
| 泛型类型判断失效 | 「泛型擦除」 |
| 集合链式操作性能不佳 | 「集合链式的中间对象」——考虑 `asSequence` |
