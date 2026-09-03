# 协程与 Flow

## 作用域

| 场景 | 用 |
|---|---|
| ViewModel | `viewModelScope`（`onCleared` 自动取消） |
| Activity/Fragment | `lifecycleScope` |
| 只在界面可见时跑 | `repeatOnLifecycle(STARTED) { ... }` |
| 应用级长任务 | 自建 `CoroutineScope(SupervisorJob() + Dispatchers.Default)`，明确管生命周期 |

禁止 `GlobalScope`：不受生命周期约束，必然泄漏。

Fragment 里收集 Flow 用 `viewLifecycleOwner.lifecycleScope`，不是 `lifecycleScope`——后者绑 Fragment 实例，View 销毁后仍在跑，回调里碰 binding 会崩。

## 调度器

| Dispatcher | 用途 |
|---|---|
| `Main` | UI 更新 |
| `Main.immediate` | 已在主线程时不重新调度，减少一帧延迟 |
| `IO` | 网络、文件、数据库 |
| `Default` | CPU 密集（解析、排序、图片处理） |

`suspend` 函数应当**自己保证线程安全**（内部 `withContext`），调用方不需要关心该切哪个线程。

```kotlin
// ✅ 挂起函数内部自己切
suspend fun loadUser(id: String): User = withContext(Dispatchers.IO) {
    api.getUser(id)
}
```

## 并发

```kotlin
// ❌ 串行，耗时相加
val a = loadA()
val b = loadB()

// ✅ 并行，耗时取最大
coroutineScope {
    val a = async { loadA() }
    val b = async { loadB() }
    process(a.await(), b.await())
}
```

`async` 必须在 `coroutineScope` / `supervisorScope` 内用，别挂到外部长生命周期 scope 上。

结构化并发：`coroutineScope` 一个子协程失败会取消全部兄弟并向上抛；`supervisorScope` 子协程互相独立。

## 取消

取消靠协作。CPU 密集循环里要主动检查：

```kotlin
while (isActive) { ... }
// 或在挂起点之间
ensureActive()
```

`CancellationException` 是正常控制流，**不能吞**：

```kotlin
// ❌ 吞掉取消，协程无法正常结束
try {
    doWork()
} catch (e: Exception) {
    Logger.e(TAG, "failed")
}

// ✅
try {
    doWork()
} catch (e: CancellationException) {
    throw e
} catch (e: Exception) {
    Logger.exp(TAG, e, "failed")
}
```

同理 **`runCatching` 会捕获 `CancellationException`**，协程里别直接用；要用就在 `onFailure` 里把 `CancellationException` 重新抛出。

取消后还要执行的清理放 `withContext(NonCancellable)`，或用 `try/finally`。

## 异常

- `launch`：异常直接抛到 `CoroutineExceptionHandler` / 崩溃
- `async`：异常留到 `await()` 才抛，不 `await` 就静默丢失

`try/catch` 包住 `launch { }` 这个调用**捕不到**协程体内的异常，要包在协程体内部。

## Flow 冷热

| 类型 | 特性 | 用途 |
|---|---|---|
| `Flow` | 冷流，每次 collect 重新执行 | 一次性数据源、数据库查询 |
| `StateFlow` | 热流，有当前值，去重（`distinctUntilChanged`），新订阅立刻收到最新值 | UI 状态 |
| `SharedFlow` | 热流，无当前值，可配 replay | 一次性事件（弹窗、导航、Toast） |

状态用 `StateFlow`，事件用 `SharedFlow`。用 `StateFlow` 发事件会因为去重导致相同事件发两次只响应一次。

```kotlin
private val _state = MutableStateFlow<UiState>(UiState.Init)
val state = _state.asStateFlow()

private val _effect = MutableSharedFlow<Effect>()
val effect = _effect.asSharedFlow()
```

对外一律暴露只读版本（`asStateFlow()` / `asSharedFlow()`），不要直接暴露 `Mutable*`。

`StateFlow` 去重基于 `equals`。持有可变对象或数组时判等不可靠，状态类用 `data class` + 不可变字段。

## 常用操作符

| 需求 | 操作符 |
|---|---|
| 新值到来时取消上一次处理 | `collectLatest` / `flatMapLatest` |
| 搜索输入防抖 | `debounce(300)` |
| 冷流转热流共享 | `stateIn(scope, SharingStarted.WhileSubscribed(5000), initial)` |
| 切上游执行线程 | `flowOn(Dispatchers.IO)`（只影响上游） |
| 异常处理 | `catch { }`（只捕上游） |

`WhileSubscribed(5000)` 的 5 秒是为了扛过屏幕旋转，避免重建时上游被取消重订阅。

## 与回调 / 老代码桥接

```kotlin
// 单次回调 → suspend
suspend fun getLocation(): Location = suspendCancellableCoroutine { cont ->
    val listener = object : Listener {
        override fun onResult(loc: Location) { cont.resume(loc) }
        override fun onError(e: Throwable) { cont.resumeWithException(e) }
    }
    manager.request(listener)
    cont.invokeOnCancellation { manager.remove(listener) }   // 必须注销，否则泄漏
}

// 多次回调 → Flow
fun observeConnection(): Flow<State> = callbackFlow {
    val cb = object : Callback {
        override fun onChange(s: State) { trySend(s) }
    }
    register(cb)
    awaitClose { unregister(cb) }   // 必须写：既注销回调，也是 callbackFlow 的强制要求
}
```

`suspendCancellableCoroutine` 的 `cont` 只能 resume 一次，多次 resume 会抛异常。

## 测试与调试

挂起函数测试用 `runTest`。需要控制时间用 `TestDispatcher` 的 `advanceTimeBy`。

调试加 JVM 参数 `-Dkotlinx.coroutines.debug` 可在线程名里看到协程标识。

## 症状 → 排查

| 症状 | 优先查 |
|---|---|
| 离开页面后任务还在跑 | 作用域选错，见「作用域」 |
| 取消了但协程还在执行 | 取消是协作式的，纯计算循环要主动检查，见「取消」 |
| `finally` 里的清理没执行完 | 取消后不能再挂起，清理要包 `NonCancellable`，见「取消」 |
| 异常没被捕获、直接崩了 | `launch` 与 `async` 传播方式不同，见「异常」 |
| `catch {}` 没抓到异常 | `catch` 只捕上游 |
| `flowOn` 没有生效 | 只影响上游，见「调度器」 |
| 主线程卡顿 | 阻塞调用没切 `Dispatchers.IO`，见「调度器」 |
| 几个请求本该并行却串行 | 顺序 `await` 了，见「并发」 |
| 每个收集者都触发一次重新请求 | 冷流需要 `stateIn`/`shareIn` 转热，见「Flow 冷热」 |
| 回调改成 Flow 后不结束或泄漏 | `callbackFlow` 漏了 `awaitClose` |
| 测试里协程没跑完就断言 | 用 `runTest`，见「测试与调试」 |

Android 界面侧的收集写法和 `ViewModel` 状态暴露（`repeatOnLifecycle`、`stateIn` 的参数取舍、配置变更与进程死亡）属于架构决策，见 `android-architecture-wiki` 的 `viewmodel-state.md`；这里只讲协程与 `Flow` 本身的语义。
