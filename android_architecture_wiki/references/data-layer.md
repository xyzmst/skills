# 数据层

数据层承载应用的**绝大部分业务逻辑**，对外暴露应用数据。UI 层永远不直连数据源。

## Repository 与数据源

- **即使只有一个数据源，也要建 Repository**。它给 UI 层一个稳定的门面，后面换实现（`SharedPreferences` → `DataStore`、加一层缓存）不会波及上层
- 一个 Repository 对应一种数据类型/一个业务领域，不是"一个页面一个"
- **数据源不要按实现细节命名**：`UserSharedPreferencesDataSource` 这种名字一旦迁移到 DataStore 就得改遍调用方。叫 `UserLocalDataSource` / `UserRemoteDataSource`
- 依赖接口而非实现：既方便替换，也方便测试时注入 fake
- **暴露不可变数据**：避免被其他类篡改，也天然可以多线程安全共享

```kotlin
interface NewsRepository {
    fun getNewsStream(): Flow<List<Article>>
    suspend fun refresh()
}

class OfflineFirstNewsRepository @Inject constructor(
    private val local: NewsLocalDataSource,
    private val remote: NewsRemoteDataSource,
) : NewsRepository { /* ... */ }
```

## 单一可信来源（SSOT）

每种数据只有一个地方说得算，其他地方都是它的投影。SSOT 可以是数据库，也可以是 Repository 里的内存缓存——**不同 Repository 可以有不同的 SSOT**（`LoginRepository` 用内存缓存，`PaymentsRepository` 直接用网络）。

Repository 的职责就是合并多个数据源、解决它们之间的冲突，然后维护这一个可信来源。

离线优先的典型形态：数据库是 SSOT，UI 只观察数据库的 `Flow`；网络请求的结果写进数据库，由数据库把变化推给 UI。**不要让 UI 同时观察数据库和监听网络回调**——那就是两个可信来源。

## 主线程安全

调用 Repository 和数据源必须**从主线程调用是安全的**，切线程是它们自己的责任：

- `Room`、`Retrofit`、`Ktor` 的 `suspend` 方法本身已经主线程安全，直接用，不用再包 `withContext`
- 手写的阻塞操作（读文件、大列表过滤、位图处理）要自己 `withContext(Dispatchers.IO / Default)`
- 判据：调用方不需要知道该切哪个线程

## 错误怎么往上暴露

用 Kotlin 原生机制，两种建模方式选一种并在项目里保持统一：

**抛异常**——`suspend` 函数用 `try/catch`，`Flow` 用 `catch` 算子；数据层可以定义自己的异常类型（`UserNotAuthenticatedException`）表达已知的失败。调用方（通常是 `ViewModel`）负责捕获并转成 UiState 里的错误态。

**返回 `Result<T>`**——把"可能失败"写进签名，调用方不会忘记处理。适合已知失败分支多、需要区分处理的场景。

```kotlin
// ViewModel 侧：捕获后转成状态，不要让异常穿透到 UI
viewModelScope.launch {
    _uiState.update { it.copy(isLoading = true) }
    runCatching { newsRepository.refresh() }
        .onSuccess { _uiState.update { s -> s.copy(isLoading = false) } }
        .onFailure { e ->
            _uiState.update { s -> s.copy(isLoading = false, userMessage = e.toUserMessage()) }
        }
}
```

注意 `Flow` 里的 `catch` 只能捕获**上游**异常，放在收集之后无效；`runCatching` 会连 `CancellationException` 一起吞掉，在协程里用要么显式重抛，要么改用 `try/catch` 只捕获业务异常。

## 内存缓存与并发

缓存可以放 Repository 也可以放数据源，取决于谁需要复用。可变缓存必须防并发读写，官方示例用 `Mutex`：

```kotlin
class NewsRepository(
    private val remote: NewsRemoteDataSource,
    private val externalScope: CoroutineScope,
) {
    private var latestNews: List<Article> = emptyList()
    private val mutex = Mutex()

    suspend fun getLatestNews(refresh: Boolean = false): List<Article> {
        if (refresh || latestNews.isEmpty()) {
            val news = remote.fetchLatestNews()
            mutex.withLock { latestNews = news }
        }
        return mutex.withLock { latestNews }
    }
}
```

## 操作的作用域：三种，别混

| 类型 | 生命周期 | 用什么 |
|---|---|---|
| 面向界面 | 界面消失即取消（列表刷新、搜索） | 调用方的 `viewModelScope` |
| 面向应用 | 应用还在就该完成（缓存网络结果、上报） | Repository **自己的** `CoroutineScope`（构造函数注入，通常配 `Dispatchers.Default`） |
| 面向业务 | 进程死了也要完成（上传日志、同步） | `WorkManager` |

关键一条：**面向应用的操作不能用调用方的 scope**。用户离开页面 → `viewModelScope` 取消 → 网络结果没写进缓存，下次进来又要重新请求。做法是 Repository 在自己的 scope 里 `async`，调用方 `await`：

```kotlin
class NewsRepository(
    private val remote: NewsRemoteDataSource,
    private val externalScope: CoroutineScope,   // 注入，不要自己 new
) {
    suspend fun getLatestNews(): List<Article> =
        externalScope.async {
            remote.fetchLatestNews().also { cache(it) }
        }.await()
}
```

用户还在页面上就能拿到结果；用户走了，`await` 被取消，但 `async` 内部逻辑继续跑完并写入缓存。

`WorkManager` 场景下，**业务逻辑要封装成独立的类（当作一个数据源），`Worker` 只负责在约束满足时调度它**，这样换执行环境不用改业务代码。

## 每层自己的模型

复杂应用里不要让一个类穿透所有层：

- 远程数据源把网络响应映射成只含应用需要字段的简单类
- Repository 把 DAO 实体映射成上层需要的数据类
- `ViewModel` 把它们组装进 `UiState`

小项目不必强求，但只要出现"为了 UI 显示往数据库实体上加字段"，就该拆了。

## 症状 → 排查

| 症状 | 优先查 |
|---|---|
| `ViewModel` 里出现 DAO / Retrofit service | 缺 Repository，UI 层直连了数据源 |
| 同一份数据两处显示不一致 | 没有 SSOT，UI 同时观察了多个来源 |
| 切页面回来又重新请求一次 | 面向应用的操作用了 `viewModelScope`，改用注入的外部 scope |
| 主线程卡顿但没做 IO | 大列表过滤/映射没切线程，或在 `Flow` 收集侧做了重计算 |
| 异常直接崩到 UI | 数据层异常没在 `ViewModel` 侧捕获转成错误状态 |
| `Flow` 的 `catch` 不生效 | `catch` 只捕获上游，位置错了 |
| 协程取消变成"业务失败"提示 | `runCatching` 吞了 `CancellationException` |
| 缓存偶发脏数据 / 并发崩溃 | 可变缓存没有 `Mutex` 保护 |
| 换存储实现要改一堆上层 | 数据源按实现细节命名、或 Repository 没有接口 |
| `Worker` 里堆满业务逻辑 | 业务逻辑该抽成独立数据源类，`Worker` 只调度 |
