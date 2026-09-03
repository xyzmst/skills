# 分层映射、依赖注入与测试

## 职责分层 vs 模块分层

两套东西，别当成一套：

- **官方三层（UI / 网域 / 数据）是职责分层**，说的是"这段代码干什么"
- **项目的 `app → feature → data → core → SDK` 是模块分层**，说的是"这段代码编译进哪个产物、能依赖谁"

一个 `feature` 模块内部通常同时包含 UI 层职责（`Fragment`、`ViewModel`）和它自己的数据层职责（`Repository`、`Api`）。所以"官方说要有数据层"不等于"必须新建 data 模块"——小规模时一个 `feature` 内的 `data` 包就是数据层。

| 官方职责 | 落到项目哪里 |
|---|---|
| UI 层 | `app/ui/<domain>/`、`feature/<domain>/ui/` + `feature/<domain>/viewmodel/` |
| 数据层 | `feature/<domain>/repository|api|bean/`，跨 feature 复用的升到 `data/<domain>/` |
| 网域层（用例） | 没有独立 domain 模块时，放在使用方 feature 的领域包内；跨 feature 复用的和 Repository 一起升到 `data/` |
| SDK 封装 | `core/<sdk_name>/`，属于数据层的基础设施 |

**模块归属与依赖方向以项目规则为准。** 官方文档给的是职责划分建议，不是模块划分命令。

## 依赖方向

- 职责上：UI 层 → 网域层 → 数据层，只能向下
- 数据层和网域层**不能**出现任何 UI 层类型（`Context` 除外也不行——`Context` 该被包装成数据源）
- 用例可以依赖用例；Repository 可以依赖 Repository（谨慎，容易成环）
- 跨层只传自己层的模型和 Kotlin/协程类型，不传 `Cursor`、`Bundle`、`Uri`、`View`

导航结构：官方推荐单 Activity + Navigation（View 体系用 Navigation Fragments），多 Activity 会让共享状态和转场都变复杂。

## 依赖注入

- **构造函数注入优先**，这是默认选择。不要在类内部 `new` 依赖，也不要用单例静态获取
- **需要时才限定作用域**：类型持有需要共享的可变数据（内存缓存）、或初始化开销大且被广泛使用时，交给依赖容器管生命周期。无状态的类型（多数用例、映射器）不需要作用域，每次新建即可
- **什么时候上 Hilt**：项目出现下列任一项就值得，否则手动注入更轻
  - 多个屏幕都有 `ViewModel`
  - 用了 `WorkManager`
  - `ViewModel` 需要限定作用域到导航返回栈

```kotlin
@HiltViewModel
class NewsViewModel @Inject constructor(
    private val newsRepository: NewsRepository,
    private val savedStateHandle: SavedStateHandle,
) : ViewModel()
```

Dispatcher 也应该注入（给个默认值），否则单测里无法替换成测试调度器：

```kotlin
class NewsRepository @Inject constructor(
    private val remote: NewsRemoteDataSource,
    private val ioDispatcher: CoroutineDispatcher = Dispatchers.IO,
)
```

## 命名惯例

| 对象 | 惯例 | 例子 |
|---|---|---|
| 方法 | 动词短语 | `makePayment()` |
| 属性 | 名词短语 | `inProgressTopicSelection` |
| 返回 `Flow` 的函数 | `get{Model}Stream`，列表用复数 | `getAuthorStream()`、`getAuthorsStream()` |
| 接口实现 | 有意义的名字，实在没有用 `Default` 前缀 | `OfflineFirstNewsRepository`、`InMemoryNewsRepository`、`DefaultNewsRepository` |
| 测试替身 | `Fake` 前缀 | `FakeAuthorsRepository` |
| UiState | 功能 + `UiState` | `NewsUiState`、`NewsItemUiState` |
| 用例 | 动词 + 名词 + `UseCase` | `GetLatestNewsUseCase` |

## 测试

除了 Hello World 级别的项目，至少要有：

- `ViewModel` 的单测（含 `Flow` 行为）
- 数据层实体的单测（Repository 和数据源）
- 界面导航测试（放 CI 当回归用）

两条实践：

- **优先用 fake，而不是 mock**。fake 是接口的简单可用实现，行为真实、不需要在测试里描述交互细节；mock 框架写出来的断言常常在测"实现怎么调用的"而不是"结果对不对"
- **测 `StateFlow` 尽量断言 `value` 属性**，而不是收集发射序列；被测对象用 `WhileSubscribed` 时要保证测试里有订阅者，否则上游不启动、`value` 永远是初始值

## 症状 → 排查

| 症状 | 优先查 |
|---|---|
| 新功能全堆在 `app` 模块 | 没按职责拆到 feature/data，先定归属再动手 |
| 数据层类里出现 `Context`/`Resources` | 该能力要包成数据源接口注入，不是把 `Context` 传下去 |
| 模块之间循环依赖 | 公共部分下沉到 `core`，或用接口反转依赖 |
| 单测里没法替换线程 | Dispatcher 硬编码，改成构造函数注入 |
| `StateFlow` 单测里 `value` 一直是初始值 | 用了 `WhileSubscribed` 但测试里没有订阅者 |
| 单测大量 mock、改实现就红 | 在测交互而非结果，换 fake |
| 为了给一个类加依赖改了一长串构造函数 | 该考虑上 Hilt 了 |
| Repository 每次注入都是新实例、缓存失效 | 有共享可变状态的类型需要限定作用域 |
