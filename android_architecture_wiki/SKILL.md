---
name: android-architecture-wiki
description: Android 应用架构知识库，覆盖 UI 层与 UDF、UiState 建模、ViewModel 边界与状态暴露、生命周期感知收集、一次性事件处理、Repository 与单一可信来源、数据层错误与缓存、网域层用例判断、依赖注入与分层依赖方向、可测试性。当需要决定代码放哪一层、设计 ViewModel 与 UiState、处理一次性事件或导航事件、写 Repository 与数据源、判断该不该加 UseCase、排查状态不更新/事件重复触发/配置变更丢状态时使用。
---

# Android Architecture Wiki

查询型知识库。只在**需要确认职责归属或实现方式**时读对应 reference，一次读一个，不要整包拉进上下文。

面向 View 体系（`Fragment`/`Activity` + 协程 + Flow）。官方架构指南现在以 Compose 为默认，本 wiki 取的是 View 变体的对应建议。

## 边界

**模块归属与依赖方向以项目规则为准**（哪个类放 `app`/`feature`/`data`/`core` 哪个包、feature 之间怎么跳转），本 wiki 只讲职责分层与实现细节：一段逻辑属于哪一层、状态怎么建模、层与层之间怎么通信。两者冲突时按项目规则走。

View 的测量绘制看 `android-view-wiki`，Kotlin 协程与 Flow 的语言层用法看 `kotlin-wiki`。

## 动手前的归属检查（最重要）

新增或搬动任何逻辑之前，先回答：

1. **这是业务逻辑还是 UI 行为逻辑？** 决定"数据怎么变"的是业务逻辑（下沉到 data 层，必要时经 domain 层）；决定"变化怎么显示"的是 UI 行为逻辑（留在 UI 层）。判据：换一套 UI（TV、Wear、Compose 重写）这段逻辑还成立吗？成立就是业务逻辑。
2. **它需要 Android 类型吗？** 需要 `Context`/`Resources`/`View`/`Fragment` 的，几乎一定属于 UI 层。如果一段"业务逻辑"离不开 `Context`，先怀疑它放错了层，而不是想办法把 `Context` 传进 ViewModel。
3. **同层已经有等价物了吗？** 已有 Repository 能覆盖就别加 UseCase，已有 UiState 字段能表达就别加第二条数据流。

写完自问：**这段代码换掉 UI 框架还能活吗？** 能活却写在 Activity/Fragment 里，就是放错了层。

## 路由

| 问题 | 读 |
|---|---|
| UiState 怎么定义、单个还是多个数据流、加载态与错误态怎么表达、UDF 到底怎么落地 | [references/ui-layer.md](references/ui-layer.md) |
| Toast/Snackbar 重复弹、导航被触发两次、一次性事件该用 Channel 还是状态字段、旋转后事件重放 | [references/events.md](references/events.md) |
| ViewModel 能不能拿 Context、状态怎么暴露、`stateIn` 参数怎么选、状态收集写法、配置变更与进程死亡后恢复 | [references/viewmodel-state.md](references/viewmodel-state.md) |
| Repository 该不该建、单一可信来源放哪、数据层错误怎么往上暴露、内存缓存、离开页面后请求要不要继续、定时/持久化任务 | [references/data-layer.md](references/data-layer.md) |
| 该不该加 UseCase、用例怎么命名、用例能不能有状态、用例之间能不能互相依赖 | [references/domain-layer.md](references/domain-layer.md) |
| 官方三层和项目模块分层怎么对应、依赖方向、构造函数注入与 Hilt 的取舍、命名惯例、怎么测 | [references/layering-di.md](references/layering-di.md) |

判断不了归哪类时：涉及"数据从哪来"读 `data-layer.md`，涉及"状态怎么给到界面"读 `viewmodel-state.md`。

## 硬规则速查

不用读 reference 就该遵守的：

- 业务逻辑不许写在 `Activity`/`Fragment`/自定义 `View` 里；反过来，UI 行为逻辑（取字符串资源、导航、弹 Toast/Snackbar）不许写进 `ViewModel`
- `ViewModel` 不持有 `Activity`/`Fragment`/`Context`/`Resources`/`View` 的引用；不要用 `AndroidViewModel`，需要 `Application` 说明依赖放错了层
- `ViewModel` 只在屏幕级用（`Activity`/`Fragment`/导航目的地）；可复用的 UI 组件用普通状态容器类，让状态由外部提升和控制
- UI 层不许直连数据源（`Room` DAO、`Retrofit` service、`SharedPreferences`/`DataStore`），一律走 `Repository`——**即使这个 Repository 只包一个数据源**
- `uiState` 用单个不可变对象暴露；数据来自下层 Flow 时用 `stateIn(viewModelScope, SharingStarted.WhileSubscribed(5_000), 初始值)`
- View 体系收集状态：`viewLifecycleOwner.lifecycleScope.launch { viewLifecycleOwner.repeatOnLifecycle(Lifecycle.State.STARTED) { ... } }`；不要用 `launchWhenStarted`/`launchWhenResumed`（挂起而非取消，上游还在跑）
- 不要从 `ViewModel` 往 UI 发一次性事件（`Channel`、`SharedFlow` 当事件总线）；事件在 `ViewModel` 内处理完，用状态更新表达结果，UI 消费后回调 `ViewModel` 清空
- 不要覆写 `onResume`/`onPause` 做 UI 相关的启停，用 `DefaultLifecycleObserver` 或 `repeatOnLifecycle`
- `Repository`、数据源、`UseCase` 必须主线程安全，自己负责切线程；`ViewModel` 里不做阻塞操作，也不写 `Dispatchers.IO` 兜底
- 跨层通信用协程 + Flow，跨层不传 Android 类型（`Cursor`、`Bundle`、`Uri`、`View`）
- 只在需要时才加 `UseCase`：多个 `ViewModel` 复用同一段业务逻辑，或某个 `ViewModel` 过于臃肿；简单转调一层不加
- 数据层对外暴露不可变数据；只有数据的所有者才能更新它暴露的数据

## 判断标准

改完自问：**状态只有一个可信来源吗？** 同一份信息能从两处改，就是后面所有诡异 bug 的源头。

## 扩展

新增 reference 时同步更新上面的路由表，否则不会被命中。
