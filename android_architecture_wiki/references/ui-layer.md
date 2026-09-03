# UI 层与单向数据流

## UiState 是什么

界面是 UiState 的直观呈现：UiState 变了，界面立刻跟着变。它不是"数据模型的副本"，而是**完全渲染这个屏幕所需的全部信息**。

```kotlin
data class NewsUiState(
    val isSignedIn: Boolean = false,
    val isPremium: Boolean = false,
    val newsItems: List<NewsItemUiState> = emptyList(),
    val userMessages: List<Message> = emptyList(),
)
```

命名惯例：**功能 + UiState**（`NewsUiState`、列表项用 `NewsItemUiState`）。

**必须不可变。** UiState 可变意味着界面能改自己显示的数据，同一条信息就有了两个可信来源——典型后果是列表项的 `bookmarked` 在 Fragment 里被改了一次、数据层又推一次，两边打架。原则：**只有数据的所有者才能更新它暴露的数据。**

## UDF：状态向下、事件向上

- `ViewModel` 持有并暴露状态，界面观察它
- 界面把用户操作通过方法调用交给 `ViewModel`
- `ViewModel` 处理操作、更新状态
- 新状态回流到界面渲染

好处不是形式好看，是三件具体的事：界面只有一个可信来源（数据一致）、状态生产逻辑可以脱离界面单测（可测试）、状态变化只有一条固定路径（可维护）。

## 两类逻辑必须分开

| | 业务逻辑 | UI 行为逻辑 |
|---|---|---|
| 决定 | 数据怎么变 | 变化怎么显示 |
| 例子 | 收藏一篇文章、下单、存用户偏好 | 取字符串资源、导航到某页、弹 Snackbar、展开/收起 |
| 该放 | data 层，必要时经 domain 层 | UI 层（`Fragment`/`Activity`/状态容器类） |
| 绝不能放 | UI 层 | `ViewModel` |

判据：**换一套 UI（TV、Wear、Compose 重写）这段逻辑还成立吗？** 成立 = 业务逻辑。需要 `Context`/`Resources` 的，基本都是 UI 行为逻辑。

## 状态容器怎么选

| 作用域 | 用什么 |
|---|---|
| 一个屏幕 / 导航目的地 | `ViewModel`（配置变更后自动存活，可访问数据层） |
| 可复用的 UI 组件（自定义组合控件、底部栏、复杂列表项） | 普通状态容器类，状态由外部提升和控制 |

**不要给可复用 UI 组件配 `ViewModel`**：它会把组件和某个屏幕的数据来源绑死，复用就无从谈起。普通状态容器类跟随界面的生命周期，可以持有 Android SDK 依赖；`ViewModel` 活得更久，不行。

## 单个 UiState 还是多个数据流

默认单个。相关状态放一起才能保证使用方任何时刻拿到的都是自洽的快照——分成两条流，很容易出现"列表已更新、书签数还是旧的"。

派生状态用属性而不是新字段：

```kotlin
val NewsUiState.canBookmarkNews: Boolean get() = isSignedIn && isPremium
```

拆成多条流的两种正当情况：

- **数据完全不相关**，且更新频率差异大（一个每秒变、一个几乎不变），捆在一起的代价大于收益
- **`PagingData`**：它本身就不是不可变类型，不能塞进不可变 UiState，必须单独一条流暴露

字段一多，任一字段变化都会让整个流发射一次、界面整体刷新。View 体系里没有自动 diff，必要时用 `distinctUntilChanged()` 或按字段 `map {}.distinctUntilChanged()` 后再收集。

## 加载态与错误态

最简形式就是字段，不要一上来就设计状态机：

```kotlin
data class NewsUiState(
    val isLoading: Boolean = false,
    val newsItems: List<NewsItemUiState> = emptyList(),
    val userMessages: List<Message> = emptyList(),   // 错误也是消息
)
```

- 加载中：`Boolean` 字段
- 错误：不只是 `Boolean`，通常要带消息文本和"重试"这类关联操作，所以建模成数据类而不是布尔值
- 几种状态**互斥**（要么加载中、要么成功、要么失败，不可能并存）时才用 `sealed`；只是"可能同时存在"的组合就用 data class 加字段

错误消息的展示与清除属于事件范畴，见 events.md。

## 症状 → 排查

| 症状 | 优先查 |
|---|---|
| 界面显示的数据和数据层不一致 | UiState 是不是可变的、有没有在 UI 层直接改状态 |
| 改一个无关字段导致整个列表重建/闪烁 | UiState 字段过多、缺 `distinctUntilChanged`、该拆流没拆 |
| 两块相关数据偶尔不同步 | 分成了多条流，该合成一个 UiState |
| `ViewModel` 里出现 `getString`/`Context`/导航调用 | UI 行为逻辑写进了 `ViewModel`，上移到 UI 层 |
| 复用的组件搬到别的页面就跑不起来 | 给可复用组件配了 `ViewModel`，改成普通状态容器类 |
| 分页列表状态诡异丢失 | `PagingData` 被塞进了不可变 UiState，单独暴露 |
| 业务规则散落在多个 Fragment 里 | 业务逻辑留在了 UI 层，下沉到 data 层或用例 |
