# Activity 生命周期与状态保存

## 六个回调各管什么

| 回调 | 职责 | 注意 |
|---|---|---|
| `onCreate` | 一次性初始化：绑定视图、关联 `ViewModel` | 收到 `savedInstanceState`，首次创建时为 null |
| `onStart` | 进入可见 | 与 `onStop` 成对 |
| `onResume` | 进入前台可交互 | 多窗口模式下"暂停"的 Activity 仍可能完全可见 |
| `onPause` | 即将失去前台 | 只做轻量工作；**持久化数据写在这里** |
| `onStop` | 不再可见 | 释放界面资源、做重的关闭操作 |
| `onDestroy` | 销毁 | 用 `isFinishing` 区分是真结束还是配置变更重建 |

**释放界面资源优先用 `onStop` 而不是 `onPause`**：多窗口模式下 Activity 处于暂停态但用户还看得见，在 `onPause` 里停动画、降级定位会导致用户看到静止的界面。

不要在这些回调里直接写启停逻辑（注册监听、开相机）。用 `DefaultLifecycleObserver` 把成对的启停收进一个组件，既能复用也不会漏注销——为什么这么做属于架构选择，见 `android-architecture-wiki`。

## onSaveInstanceState 的时机

**targetSdk 28（Android 9）及以上：`onSaveInstanceState` 总在 `onStop()` 之后调用。**

这一条推翻了一个流传很广的旧经验。在此之前它可能在 `onPause()` 之后的任意时刻被调用，所以"不要在 `onStop` 里提交 Fragment 事务"是对的；现在保存状态发生在 `onStop` 之后，**`onStop()` 里做事务是安全的**。

配套的一条边界：**它不是生命周期回调，不保证被调用。** 用户主动按返回退出、代码调 `finish()` 时都不会调。所以：

- 要在下次重建时恢复的**瞬时界面状态** → `onSaveInstanceState`
- 要长期保留的**用户数据**（草稿、设置） → `onPause()` 或 `onStop()` 里写库/写盘

把用户数据只存在 `onSaveInstanceState` 里，是"退出应用后草稿丢了"的经典原因。

## Bundle 的硬限制

`onSaveInstanceState` 的 `Bundle` 走 Binder 事务传给系统进程，有大小限制。塞大对象（图片、长列表、完整响应体）会抛 `TransactionTooLargeException`，而且往往在低端机或数据量大的账号上才炸。

只存**能重新拉取数据所需的最小输入**：当前选中的 id、查询词、滚动位置、表单草稿的文本。列表内容本身应该能从数据层重新取。

## 配置变更与进程死亡

两件事，恢复机制不同：

- **配置变更**（旋转、深色模式、分屏、大屏自由旋转）：Activity 走 `onPause → onStop → onDestroy`，然后立刻新建实例并 `onCreate`。`ViewModel` 存活
- **进程死亡**（后台被回收）：`ViewModel` 一起没了，只有 `onSaveInstanceState` 存进 `Bundle` 的东西能恢复

判断销毁原因不该靠自己写逻辑——把界面数据放 `ViewModel`，配置变更时它自动存活；进程死亡时靠 `SavedStateHandle`。两者的完整对照和 `SavedStateHandle` 用法见 `android-architecture-wiki` 的 `viewmodel-state.md`。

`onDestroy` 里要区分两种情况时用 `isFinishing`；`ViewModel` 侧对应的是 `onCleared` 只在真正结束时调用。

注意 targetSdk 36 起大屏设备会忽略方向锁定，**配置变更的发生频率显著上升**，原本"锁竖屏所以不会重建"的假设不再成立，见 `android-sdk-behavior-wiki`。

## killable 窗口

`onStop()` 返回之后到 `onResume()` 开始之前，进程可能被系统随时杀掉，不会再执行任何一行代码。所以这个窗口里不能有"还没落盘但必须保住"的数据。

## 症状 → 排查

| 症状 | 优先查 |
|---|---|
| 退出应用后用户输入丢失 | 只存进了 `onSaveInstanceState`，改在 `onPause`/`onStop` 落盘 |
| 旋转后状态丢失 | 状态存在 Activity 字段里，该上提到 `ViewModel` |
| 从后台回来状态丢失（旋转正常） | 进程死亡，关键输入要走 `SavedStateHandle` |
| `TransactionTooLargeException` | `Bundle` 里塞了大对象 |
| 多窗口下动画停了、界面像卡住 | 在 `onPause` 里停了界面资源，改到 `onStop` |
| 监听器泄漏或重复注册 | 启停不成对，改用 `DefaultLifecycleObserver` |
| 升级 targetSdk 后重建变频繁 | targetSdk 36 大屏忽略方向锁定 |
