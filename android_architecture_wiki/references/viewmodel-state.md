# ViewModel 边界与状态收集

## ViewModel 的硬边界

- **不持有任何生命周期相关类型**：`Activity`、`Fragment`、`Context`、`Resources`、`View`、`Lifecycle` 都不能作为依赖传进来，也不能存成字段。`ViewModel` 活得比界面长，持有就是泄漏
- **不要用 `AndroidViewModel`**（View 体系里这是"强烈建议"级别）。需要 `Application` 说明依赖放错了层：要资源和字符串是 UI 层的事，要文件目录、`ContentResolver`、`SharedPreferences` 是数据层的事，把它们包成数据源注入进来
- **只在屏幕级用**：`Activity`/`Fragment`/导航目的地。可复用 UI 组件用普通状态容器类
- **主线程安全**：`ViewModel` 里所有工作从主线程调用必须是安全的。切线程是数据层和网域层的责任，不要在 `ViewModel` 里写 `withContext(Dispatchers.IO)` 兜底——那是在替下层擦屁股，说明下层的 API 有问题

需要 `Context` 时的自查顺序：这段逻辑是不是该留在 UI 层？如果确实是业务逻辑，它依赖的到底是 `Context` 还是 `Context` 背后的某个能力（存储、网络状态、定位）？后者就抽成数据源接口。

## 暴露状态的三种写法

**数据来自下层 Flow**——用 `stateIn`：

```kotlin
class BookmarksViewModel @Inject constructor(
    newsRepository: NewsRepository,
) : ViewModel() {

    val uiState: StateFlow<NewsFeedUiState> =
        newsRepository.getNewsResourcesStream()
            .map { it.toFeedState() }
            .stateIn(
                scope = viewModelScope,
                started = SharingStarted.WhileSubscribed(5_000),
                initialValue = NewsFeedUiState.Loading,
            )
}
```

`WhileSubscribed(5_000)` 的 5 秒不是随手写的：界面旋转时订阅者会短暂消失再回来，给 5 秒宽限期，上游（数据库监听、网络轮询）就不会被取消又重启。写 `WhileSubscribed()` 无参会让每次旋转都重连上游；写 `SharingStarted.Eagerly`/`Lazily` 则是界面不可见时上游还在跑。

**没有上游 Flow 的简单场景**——`MutableStateFlow` 对内可变、对外只读：

```kotlin
private val _uiState = MutableStateFlow(LoginUiState())
val uiState: StateFlow<LoginUiState> = _uiState.asStateFlow()

fun tryLogin(username: String, password: String) {
    viewModelScope.launch {
        _uiState.update { it.copy(isLoginInProgress = true) }
        val success = loginRepository.login(username, password)
        _uiState.update {
            if (success) it.copy(isLoginInProgress = false, isUserLoggedIn = true)
            else it.copy(isLoginInProgress = false, errorMessage = "登录失败")
        }
    }
}
```

用 `update {}` 而不是 `value = value.copy(...)`：后者在并发更新时会丢改动。

**旧模块**：`LiveData` 在 View 体系里仍是官方认可的可观察容器，生命周期由 `LifecycleOwner` 隐式处理。**跟随所在模块的既有写法**——旧模块不要为了"更现代"引入 `StateFlow`，新模块不要用 `LiveData`。

## 收集状态（View 体系）

```kotlin
class MyFragment : Fragment() {

    private val viewModel: MyViewModel by viewModels()

    override fun onViewCreated(view: View, savedInstanceState: Bundle?) {
        super.onViewCreated(view, savedInstanceState)

        viewLifecycleOwner.lifecycleScope.launch {
            viewLifecycleOwner.repeatOnLifecycle(Lifecycle.State.STARTED) {
                viewModel.uiState.collect { render(it) }
            }
        }
    }
}
```

三个都不能错的点：

- `viewLifecycleOwner` 而不是 `this`——Fragment 的生命周期比它的 View 长（回退栈里 View 已销毁、Fragment 还在），用 `this` 会在 View 销毁后继续更新已失效的 `binding`
- `repeatOnLifecycle(STARTED)`——界面不可见时**取消**收集，可见时重新开始
- `launch` 在 `repeatOnLifecycle` 外、`collect` 在里面

**不要用 `launchWhenStarted`/`launchWhenCreated`/`launchWhenResumed`**：lifecycle 2.6.0 起已废弃，官方给的替换就是 `repeatOnLifecycle`。它们的问题是界面不可见时只**挂起**协程而不取消，上游生产者仍然活跃，白烧资源。

只收集一条流时可以用 `flowWithLifecycle`：

```kotlin
viewModel.uiState
    .flowWithLifecycle(viewLifecycleOwner.lifecycle, Lifecycle.State.STARTED)
    .onEach { render(it) }
    .launchIn(viewLifecycleOwner.lifecycleScope)
```

多条流不要用它套多次（每条都会各自开销），直接用一个 `repeatOnLifecycle` 块里 `launch` 多个收集。

这里讲的是架构层面的收集契约。`Flow` 算子本身的行为（冷热流、`flowOn` 影响范围、异常与取消）属于语言层，看 `kotlin-wiki` 的 `coroutines-flow.md`，两处结论一致，改一处时同步另一处。

## 配置变更 vs 进程死亡

两件不同的事，很容易混：

| | 配置变更（旋转、深色模式、分屏） | 进程死亡（后台被系统回收） |
|---|---|---|
| `ViewModel` 实例 | 存活 | 销毁 |
| `StateFlow` 里的状态 | 保留 | 丢失 |
| 恢复靠 | `ViewModel` 本身 | `SavedStateHandle` |

只有真正需要跨进程死亡恢复的**少量关键输入**才放 `SavedStateHandle`（当前查询词、选中 id、表单草稿），别把整个 UiState 塞进去——它走的是 `Bundle`，有大小限制，放大对象会引发 `TransactionTooLargeException`。列表数据这类应该能从数据层重新拉取，不需要保存。

```kotlin
class SearchViewModel @Inject constructor(
    private val savedStateHandle: SavedStateHandle,
    repository: SearchRepository,
) : ViewModel() {

    val query: StateFlow<String> = savedStateHandle.getStateFlow(KEY_QUERY, "")

    fun onQueryChanged(value: String) {
        savedStateHandle[KEY_QUERY] = value
    }
}
```

## 生命周期回调

不要覆写 `onResume`/`onPause` 做 UI 相关的启停。用 `DefaultLifecycleObserver`（挂在 `viewLifecycleOwner.lifecycle` 上）或 `repeatOnLifecycle`，让"启动-停止"成对出现在同一处，避免只注册没注销。

## 症状 → 排查

| 症状 | 优先查 |
|---|---|
| Fragment 回退栈返回后崩在 `binding` 为 null | 收集用了 `this` 而不是 `viewLifecycleOwner` |
| 界面退到后台了还在收网络/数据库更新 | 用了 `launchWhenStarted` 或 `Eagerly`/`Lazily`，改 `repeatOnLifecycle` + `WhileSubscribed(5_000)` |
| 每次旋转都重新发一次网络请求 | `stateIn` 用了无参 `WhileSubscribed()`，给 5000ms 宽限期 |
| 旋转后状态全没了 | 状态存在 Fragment 字段里而不是 `ViewModel`；或错在数据没上提 |
| 从后台回来状态没了（旋转没问题） | 进程死亡，关键输入要走 `SavedStateHandle` |
| `TransactionTooLargeException` | 往 `SavedStateHandle`/`onSaveInstanceState` 塞了大对象 |
| `ViewModel` 泄漏 Activity | `ViewModel` 持有了 `Context`/`View`/回调；或用了 `AndroidViewModel` 顺手拿 `Application` |
| 并发更新状态时改动丢失 | 用了 `value = value.copy()`，换 `update {}` |
| `ViewModel` 里到处 `withContext(Dispatchers.IO)` | 下层没做到主线程安全，修下层而不是在这兜 |
