# Fragment 事务

## commit() 是异步的

`commit()` 不立即执行事务，只是**调度**到主线程稍后运行。所以：

```kotlin
supportFragmentManager.beginTransaction()
    .replace(R.id.container, DetailFragment())
    .commit()

// ❌ 这里拿不到，事务还没跑
val f = supportFragmentManager.findFragmentById(R.id.container)
```

三种处理方式：

| 方式 | 语义 | 限制 |
|---|---|---|
| `commit()` | 异步调度，绝大多数场景用它 | 提交后不能立即拿到 Fragment |
| `commitNow()` | 立即在当前线程执行 | **不能与 `addToBackStack()` 同用** |
| `commit()` + `executePendingTransactions()` | 执行所有待处理事务 | 与 `addToBackStack()` 兼容 |

官方的建议是：绝大多数用例 `commit()` 就够。需要立即拿到实例时优先 `commitNow()`；如果同时又要进返回栈，只能用 `commit()` 加 `executePendingTransactions()`。

## setReorderingAllowed(true)

**默认是关闭的**（为了行为兼容），但新写的事务应该开：

```kotlin
supportFragmentManager.commit {
    setReorderingAllowed(true)
    replace(R.id.container, DetailFragment())
    addToBackStack("detail")
}
```

开启后，多个事务一起执行时，**中间态的 Fragment**（加进来又立刻被替换掉的那个）不会经历生命周期变化、也不会执行动画和转场。这个标志同时影响事务的初始执行和 `popBackStack()` 的逆向操作。

不开的表现是：快速连续操作时看到一闪而过的中间页面、动画叠加错乱、中间 Fragment 白跑一轮 `onCreateView`/`onDestroyView`。

## 状态丢失异常

`IllegalStateException: Can not perform this action after onSaveInstanceState`——在状态已经保存之后再提交事务，这个事务不可能被保存进 `Bundle`，系统直接抛异常。

**先搞清时机**：targetSdk 28+ 起 `onSaveInstanceState` 在 `onStop()` 之后调用，所以 `onStop()` 里提交事务是安全的。真正会撞上的是**保存状态之后到下次 `onStart` 之前**到达的回调：

- 网络请求返回时页面已经退到后台
- 定时器、`postDelayed` 在后台触发
- 广播、推送回调

修法按优先级：

1. **把提交绑定到生命周期**——用 `viewLifecycleOwner.lifecycleScope` + `repeatOnLifecycle(STARTED)` 收集状态，后台期间根本不会收到（推荐，从根上消除）
2. **改成状态驱动**——回调只更新 `ViewModel` 里的状态，界面在恢复时按状态决定显示什么，而不是回调直接指挥导航
3. **提交前检查** `isStateSaved`（少数确实无法上提的场景）

**`commitAllowingStateLoss()` 不是修法。** 它只是把"这个事务会丢"从抛异常改成静默丢失——用户回到页面时该显示的对话框没了、该跳的页没跳。它的合理用途极少（比如确实无所谓的埋点式 UI），拿它消除崩溃等于把可见问题换成不可复现问题。

## 同一事务是原子的

一个 `FragmentTransaction` 是一组原子操作。对**同一个 Fragment 实例**在同一事务里同时 `detach` 和 `attach` 会互相抵消——这其实是好事，避免了销毁再立刻重建 View。

如果真要"分离后立即重新附加"（比如强制重建 View），必须用**两个独立事务**：`commit()` 之后 `executePendingTransactions()`，再提交第二个。

## 避免重复添加

配置变更后 Activity 重建，`onCreate` 会再跑一遍。如果无条件添加 Fragment，就会叠加两份（表现为界面重影、两套监听器）。系统已经帮你恢复了原来的 Fragment，所以要判重：

```kotlin
override fun onCreate(savedInstanceState: Bundle?) {
    super.onCreate(savedInstanceState)
    setContentView(R.layout.activity_main)

    if (savedInstanceState == null) {          // 只在首次创建时添加
        supportFragmentManager.commit {
            setReorderingAllowed(true)
            add<ItemListFragment>(R.id.container, tag = TAG_LIST)
        }
    }
}
```

用 `savedInstanceState == null` 判断，或者 `findFragmentByTag(TAG_LIST) == null`。**给 Fragment 带 tag** 是个好习惯，否则后续找不回它。

## 返回栈

默认**不**加入返回栈，要显式 `addToBackStack()`。加了之后：

- `replace()` + `addToBackStack()`：旧 Fragment 的 View 被销毁（走 `onDestroyView`），实例保留在栈里，返回时重建 View
- `popBackStack()` 出栈；带 name 参数的 `popBackStack(name, POP_BACK_STACK_INCLUSIVE)` 可以一次弹到指定位置
- 返回栈状态由 `FragmentManager` 自己保存和恢复，不用手动管

需要拦截返回键时用 `OnBackPressedDispatcher`，绑到 `viewLifecycleOwner`：

```kotlin
requireActivity().onBackPressedDispatcher.addCallback(viewLifecycleOwner) {
    // 处理返回；不需要处理时 isEnabled = false 让事件继续传
}
```

不要覆写 Activity 的 `onBackPressed()`——它已弃用，且在预测性返回手势下行为不同，版本门控见 `android-sdk-behavior-wiki` 的 `ui-compat.md`。

## 症状 → 排查

| 症状 | 优先查 |
|---|---|
| `IllegalStateException ... after onSaveInstanceState` | 后台期间的回调在提交事务，把提交绑到 `repeatOnLifecycle(STARTED)` |
| 提交后立刻 `findFragment` 拿到 null | `commit()` 是异步的，用 `commitNow()` 或 `executePendingTransactions()` |
| `commitNow` 报不能和返回栈同用 | 改 `commit()` + `executePendingTransactions()` |
| 旋转后界面重影、两份 Fragment | `onCreate` 无条件添加，加 `savedInstanceState == null` 判断 |
| 看到一闪而过的中间页、动画叠加 | 缺 `setReorderingAllowed(true)` |
| detach 后 attach 没有重建 View | 同一事务内互相抵消，拆成两个事务 |
| 返回键行为异常 | 用了已弃用的 `onBackPressed()`，改 `OnBackPressedDispatcher` |
| 对话框/跳转在返回前台后消失 | 用了 `commitAllowingStateLoss()`，事务被静默丢弃 |
