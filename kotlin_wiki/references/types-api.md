# 类型与 API 设计

## 类的选型

| 需求 | 用 |
|---|---|
| 纯数据载体，需要 `equals`/`hashCode`/`copy` | `data class` |
| 封闭的类型集合（状态、结果、事件） | `sealed class` / `sealed interface` |
| 无状态的分支标记 | `sealed interface` + `object` 实现 |
| 单例 | `object` |
| 固定常量集合 | `enum class` |
| 包一层值但不想有对象开销 | `@JvmInline value class` |

`sealed interface` 比 `sealed class` 灵活：一个类型可以属于多个封闭层级，且不占继承位。没有共享状态时优先用它。

```kotlin
sealed interface UiState {
    object Loading : UiState
    data class Success(val data: List<Item>) : UiState
    data class Error(val msg: String) : UiState
}
```

`enum` 需要携带不同结构的数据时改用 `sealed`。

## data class 注意

- `equals`/`hashCode`/`toString`/`copy` **只覆盖主构造器里的属性**，body 里声明的属性不参与
- `copy()` **不走 `init` 校验块**，靠 `init` 做参数校验的类别暴露 `copy`（可以私有化构造器 + 工厂方法）
- 主构造器里放可变集合（`MutableList`）会让判等不可靠，用 `List` 并保证不可变
- 作为 `StateFlow` 的状态类时，所有字段都应是不可变的

## value class

包装原始类型，避免参数搞混，运行时无装箱开销：

```kotlin
@JvmInline
value class UserId(val value: String)

fun load(id: UserId)   // 传错类型编译期就报错
```

作为可空类型、泛型参数使用时仍会装箱。

## 扩展函数

**静态解析，没有多态**——按声明类型而非运行时类型分派：

```kotlin
open class A
class B : A()
fun A.name() = "A"
fun B.name() = "B"

val x: A = B()
x.name()   // "A"，不是 "B"
```

同名成员函数**优先于**扩展函数。给第三方类加扩展时，将来对方加了同名成员，你的扩展会静默失效。

扩展函数放哪：只在当前模块用就放模块内；多模块共用才提到 `core`。别为了"好看"给什么类型都挂扩展，滥用会污染补全列表。

不能访问私有成员，不能被继承覆写。

## 委托

```kotlin
// 接口委托：组合替代继承
class Repo(private val cache: Cache) : Cache by cache

// 属性委托
val heavy by lazy { buildHeavy() }              // 默认线程安全（SYNCHRONIZED）
val heavy by lazy(LazyThreadSafetyMode.NONE) { } // 确定单线程时省开销
var name by Delegates.observable("") { _, old, new -> ... }
```

`by lazy` 只能用于 `val`。`lateinit var` 用于依赖注入/生命周期后初始化的场景。

## 可见性

Kotlin 默认 `public`，比 Java 的包私有更开放。写库/模块时要主动收紧：

| 修饰符 | 范围 |
|---|---|
| `private` | 文件或类内 |
| `internal` | 同一编译模块（Gradle module） |
| `protected` | 类及子类（顶层不可用） |
| `public` | 默认 |

模块内部实现一律 `internal`，只暴露必要 API。

## 泛型

- `out T`（协变）：只产出 T，如 `List<out T>`
- `in T`（逆变）：只消费 T，如 `Comparable<in T>`
- `reified T`：`inline fun <reified T> parse(json: String): T`，可在运行时拿到类型

需要接收任意类型但不关心具体类型时用 `*`（星投影）而不是 `Any?`。

## 空值设计

API 返回值尽量非空，用 `emptyList()` 而不是 null 表示"没有"。

需要区分"失败"和"空结果"时用 `sealed` 的结果类型，不要用 `null` 同时表达两种语义。

Kotlin 内置的 `Result` 只能表达"成功/失败"，失败方只有 `Throwable`。需要区分多种业务失败原因时，自定义 sealed 结果类更清晰。

## 与 Java 互操作

| 注解 | 作用 |
|---|---|
| `@JvmStatic` | companion 成员生成静态方法 |
| `@JvmOverloads` | 默认参数生成 Java 重载 |
| `@JvmField` | 属性暴露为字段，不生成 getter |
| `@JvmName` | 改生成的方法名，解决签名冲突 |

Java 侧要调用的 Kotlin API，默认参数无效（除非加 `@JvmOverloads`），companion 方法要写 `Companion.` 前缀（除非加 `@JvmStatic`）。

## 常量

```kotlin
// 编译期常量，内联到调用处
const val MAX_RETRY = 3

// 运行时常量
val DEFAULT_CONFIG = Config()
```

`const` 只能用于顶层、`object`、`companion object` 中的基本类型和 String。

Android 里注意：`companion object` 里的普通 `val` 会生成 getter 方法，高频调用路径上用 `const` 或 `@JvmField`。

## 症状 → 排查

| 要决定什么 / 遇到什么 | 看 |
|---|---|
| 该用 `class` / `data class` / `object` / `sealed` 哪个 | 「类的选型」 |
| `data class` 的 `copy`、`equals`、解构带来的意外 | 「data class 注意」 |
| 想给基本类型加语义又不想加对象开销 | 「value class」 |
| 该写扩展函数还是成员函数 | 「扩展函数」 |
| 属性想懒加载、想委托给别的对象 | 「委托」 |
| 想限制只在模块内可见 | 「可见性」——`internal` |
| 泛型的 `in`/`out`、`reified` 该怎么写 | 「泛型」 |
| API 该不该返回可空类型 | 「空值设计」 |
| Java 侧调用 Kotlin API 报错或签名奇怪 | 「与 Java 互操作」 |
| 常量该用 `const` 还是 `val` | 「常量」 |

只讲类型与 API 设计。放哪一层、该不该建 Repository 或 UseCase 属于架构决策，见 `android-architecture-wiki`。
