---
name: android-component-wiki
description: Android Activity 与 Fragment 组件知识库，覆盖生命周期时序、onSaveInstanceState 时机与边界、Fragment 与 View 生命周期的差异、事务提交语义与状态丢失、Activity Result API、Fragment 间通信、启动模式与任务返回栈。当需要写或改 Activity/Fragment、提交 Fragment 事务、处理页面间结果回传、配置启动模式与返回栈、排查 binding 空指针 / IllegalStateException 状态丢失 / Fragment 重复添加 / 回退后崩溃 / 结果回调收不到时使用。
---

# Android Component Wiki

查询型知识库。只在**需要确认组件时序或 API 用法**时读对应 reference，一次读一个，不要整包拉进上下文。

## 边界

只讲**组件自身的时序和 API**。相邻域各有归属，不要在这里找：

- 状态该放哪、`UiState` 怎么建模、怎么收集 `Flow` → `android-architecture-wiki`
- 测量布局、动画、insets、自定义 View → `android-view-wiki`
- 预测性返回在哪个 targetSdk 生效、大屏强制重建 → `android-sdk-behavior-wiki`
- 协程作用域与取消语义 → `kotlin-wiki`

## 路由

| 问题 | 读 |
|---|---|
| 六个回调各该做什么、`onSaveInstanceState` 什么时候调、数据该在哪存、配置变更与进程死亡 | [references/activity-lifecycle.md](references/activity-lifecycle.md) |
| `binding` 空指针、Fragment 与它的 View 生命周期不一致、回退栈里的 Fragment 状态、`onDestroyView` 与 `onDestroy` | [references/fragment-lifecycle.md](references/fragment-lifecycle.md) |
| 事务不立即生效、`IllegalStateException` 状态丢失、Fragment 重复添加或叠加、返回栈行为、动画错乱 | [references/fragment-transactions.md](references/fragment-transactions.md) |
| 页面间回传结果、请求权限的回调、Fragment 之间通信、共享 `ViewModel` 的作用域怎么选 | [references/results-communication.md](references/results-communication.md) |
| 启动模式选哪个、重复打开同一页、通知点进来栈乱了、`onNewIntent`、单 Activity 架构 | [references/tasks-backstack.md](references/tasks-backstack.md) |

## 硬规则速查

- **Fragment 里凡是和 View 相关的都用 `viewLifecycleOwner`**，不要用 `this`——Fragment 比它的 View 活得久
- **`ViewBinding` 在 `onDestroyView` 里置空**，否则回退栈返回时拿到的是已销毁的 View
- **Fragment 不要写带参构造函数**，参数一律走 `arguments` 里的 `Bundle`；系统重建时只会调无参构造
- **`commit()` 是异步的**，调完立刻去 `findFragmentByTag` 拿不到；需要立即执行用 `commitNow()`，但它**不能**配 `addToBackStack()`
- **新写的事务加 `setReorderingAllowed(true)`**——默认是关的，不加会让中间态 Fragment 走多余的生命周期和动画
- **不要用 `commitAllowingStateLoss()` 消除崩溃**，它只是把"状态会丢"从异常变成静默丢失，先找清为什么在保存状态之后还在提交
- **targetSdk 28+ `onSaveInstanceState` 总在 `onStop()` 之后调用**，所以 `onStop()` 里做 Fragment 事务是安全的——那条"`onStop` 里不能提交事务"的旧经验已经过期
- **持久化数据写在 `onPause()` 或 `onStop()`**，不要依赖 `onSaveInstanceState`——它不是生命周期回调，不保证每种情况都被调用
- **`registerForActivityResult()` 必须无条件调用**，且多个启动器每次以**相同顺序**注册；不要包在 `if` 里、也不要按用户输入决定注册
- **不要再用 `startActivityForResult()` / `onActivityResult()`**，用 Activity Result API；不要用 `setTargetFragment()`，用 Fragment Result API 或共享 `ViewModel`
- **`launch()` 到结果回调之间进程可能被杀**，处理结果需要的额外状态必须自己存
- **添加 Fragment 前先 `findFragmentByTag()` 判重**，否则配置变更后会叠加两份
- **默认用 `standard` 启动模式**，改之前先确认是不是能用 Intent flag 解决——启动模式是清单级的全局行为，flag 是单次调用的

## 判断标准

改完自问：**旋转一次、从后台被杀一次、从通知点进来一次，这三条路径都试过吗？** 组件层的 bug 几乎都藏在重建路径上，正常点进去永远看不到。

## 扩展

新增 reference 时同步更新路由表。
