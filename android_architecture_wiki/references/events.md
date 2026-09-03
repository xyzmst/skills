# 一次性事件与导航事件

## 核心结论

**不要从 `ViewModel` 往界面发事件。** 事件在 `ViewModel` 内部处理完，把结果表达成状态更新，界面观察状态做出反应。这是官方"强烈建议"级别的要求，也是这一层最反直觉的一条。

理由是具体的：状态是可重放的，事件不是。走状态更新，配置变更（旋转）后界面重建能立刻恢复到正确画面，事件不会丢也不会被吞；配合 `SavedStateHandle` 甚至能在进程被杀后恢复。走事件通道，旋转那一瞬间没有订阅者，事件就永久丢了。

思路上的转换：不要问"界面现在该执行什么动作"，要问"这个动作会让界面处于什么状态"。

## 事件该由谁处理

| 事件 | 谁处理 |
|---|---|
| 纯 UI 状态变化（展开/收起、Tab 选中、输入框焦点） | 界面自己，不必经过 `ViewModel` |
| 需要业务逻辑（刷新、提交、收藏、登录） | `ViewModel` 暴露方法，界面调用 |
| 深层子组件里产生的点击（列表项、子控件） | 仍然是 `ViewModel`，但事件要通过 lambda 一层层上提 |

深层事件的关键约束：**不要把 `ViewModel` 传进列表或子组件**。子组件只接收它要显示的数据和要回调的 lambda，谁处理、怎么处理它不需要知道——传进去就把可复用组件和某个屏幕的实现细节焊死了。

命名：`ViewModel` 里处理事件的函数用动词（`login()`、`refreshNews()`、`validateInput()`）；回调参数用 `on + 动词 + 对象`（`onItemClick`、`onRetryClick`）。

## 消息类事件（Toast / Snackbar）

模式是"状态字段 + 消费后回调清空"，三步：

```kotlin
// 1. 状态里有一个待显示的消息
data class LatestNewsUiState(
    val news: List<News> = emptyList(),
    val isLoading: Boolean = false,
    val userMessage: String? = null,
)

class LatestNewsViewModel : ViewModel() {

    private val _uiState = MutableStateFlow(LatestNewsUiState())
    val uiState: StateFlow<LatestNewsUiState> = _uiState.asStateFlow()

    fun refreshNews() {
        viewModelScope.launch {
            if (!hasInternet()) {
                // 2. 业务逻辑要提示用户时，只更新状态，不关心怎么显示
                _uiState.update { it.copy(userMessage = "网络未连接") }
                return@launch
            }
            // ...
        }
    }

    // 3. 界面显示完之后回调，清空消息
    fun userMessageShown() {
        _uiState.update { it.copy(userMessage = null) }
    }
}
```

界面侧（View 体系）：

```kotlin
viewLifecycleOwner.lifecycleScope.launch {
    viewLifecycleOwner.repeatOnLifecycle(Lifecycle.State.STARTED) {
        viewModel.uiState.collect { state ->
            state.userMessage?.let { message ->
                Snackbar.make(binding.root, message, Snackbar.LENGTH_SHORT).show()
                viewModel.userMessageShown()      // 关键：消费后立刻通知清空
            }
            // 渲染其余状态
        }
    }
}
```

要点：`ViewModel` 不需要知道消息用 Snackbar 还是 Toast 显示，只需要知道"有一条消息待显示"。消息虽然是瞬态的，但状态在每个时刻都忠实反映了屏幕上有没有它——**漏掉第 3 步清空，就是"返回页面又弹一次"的根因**。

多条消息排队时把 `userMessage: String?` 换成 `userMessages: List<Message>`，显示后按 id 移除。

## 导航事件

同样用状态字段表达，而不是发一个"导航指令"：

```kotlin
data class LoginUiState(
    val isLoginInProgress: Boolean = false,
    val errorMessage: String? = null,
    val isUserLoggedIn: Boolean = false,
)
```

界面观察到 `isUserLoggedIn` 变 true 就跳转，跳转后要保证不会因为状态重放而跳第二次——两个手段配合用：跳转后立刻让 `ViewModel` 把标志复位（和消息清空同一个套路），并给 `navigate()` 加 `launchSingleTop = true`。注意 Navigation 默认**不会**去重，同一目的地连续 `navigate()` 两次会入栈两份，别指望它兜底。

判断谁负责：**决定"要不要导航"是业务逻辑，属于 `ViewModel`；决定"怎么导航"（`NavController`、Intent、转场动画）是 UI 行为逻辑，属于界面。**

## 反模式

| 写法 | 问题 |
|---|---|
| `Channel` / `SharedFlow` 当事件总线往 UI 发指令 | 旋转时没有订阅者，事件丢失；重复订阅时事件被谁消费不确定 |
| `SingleLiveEvent` 之类"只消费一次"的封装 | 绕过状态模型，多观察者时行为不可预测，本质是在给事件通道打补丁 |
| 在 `ViewModel` 里直接调 `NavController` / `startActivity` | UI 行为逻辑侵入 `ViewModel`，还会持有界面引用 |
| 用 `LiveData<Unit>` 触发一次性动作 | 配置变更后 `LiveData` 会重放最后一个值，导致动作再执行一次 |

## 症状 → 排查

| 症状 | 优先查 |
|---|---|
| Snackbar/Toast 返回页面时又弹一次 | 状态里的消息字段没在显示后清空（漏了 `userMessageShown()` 这一步） |
| 旋转屏幕后重复弹提示、重复跳转 | 用 `LiveData`/状态字段表达一次性动作但没复位；或依赖了事件通道 |
| 事件偶发丢失（尤其快速切页时） | `Channel`/`SharedFlow` 事件总线在无订阅者时丢事件，改成状态 |
| 导航被触发两次、返回栈里同一页两份 | 状态标志没复位，或没利用 Navigation 的目的地去重 |
| 列表项点击要透传好几层才能到 `ViewModel` | 正常，lambda 上提就是推荐做法；千万别改成把 `ViewModel` 传下去 |
| `ViewModel` 单测里没法验证跳转 | 说明跳转决策没有体现在状态上，把它变成状态字段 |
