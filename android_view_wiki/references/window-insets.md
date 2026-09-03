# WindowInsets、边到边与键盘遮挡

## 前提：edge-to-edge 已经是默认行为

`targetSdk 35` + Android 15 及以上设备 = **窗口默认铺满全屏、内容画在系统栏底下**，不是可选项。低版本要一致效果，在 `onCreate` 里手动调 `enableEdgeToEdge()`（`androidx.activity`）。

这里讲怎么适配。哪个 targetSdk 开始强制、`Configuration` 不再排除系统栏之类的版本行为差异，见 `android-sdk-behavior-wiki` 的 `ui-compat.md`。

Android 15 起同时失效的老做法（写了也没用，别再用）：

| 老 API | 现状 |
|---|---|
| `Window.setStatusBarColor` / `android:statusBarColor` | 已废弃，Android 15 上**完全无效** |
| `Window.setNavigationBarColor` / `android:navigationBarColor` | 已废弃，对手势导航无效；仅三键导航还生效，默认取窗口背景色 |
| `Window.setDecorFitsSystemWindows` | 已废弃 |
| `View.SYSTEM_UI_FLAG_*` | 早已废弃，用 `WindowInsetsControllerCompat` |
| `layoutInDisplayCutoutMode = SHORT_EDGES / NEVER / DEFAULT` | 非浮动窗口一律按 `ALWAYS` 处理 |

## inset 是什么、怎么传递

inset 表示**窗口与系统 UI 相交的区域**，不是"边距"。它从根 View 沿 View 树向下 dispatch，谁消费谁负责让出空间。

| 类型 | 含义 | 用在哪 |
|---|---|---|
| `Type.systemBars()` | 状态栏 + 导航栏 + caption bar | 可点击、不能被遮的元素，最常用 |
| `Type.displayCutout()` | 刘海/挖孔区 | 横屏下的列表、满屏内容 |
| `Type.systemGestures()` | 系统手势优先区（返回手势、home 条） | 自己也要横滑/上滑的组件：bottom sheet、`ViewPager2`、轮播 |
| `Type.ime()` | 软键盘 | 输入框上移、聊天列表避让 |
| `Type.captionBar()` | 桌面窗口模式的标题栏 | 桌面/大屏，全屏应用也一直可见 |

多类型取并集用 `or`：`Type.systemBars() or Type.displayCutout()`。

## 标准写法

```kotlin
// Activity.onCreate
enableEdgeToEdge()
setContentView(binding.root)

ViewCompat.setOnApplyWindowInsetsListener(binding.root) { v, windowInsets ->
    val bars = windowInsets.getInsets(
        WindowInsetsCompat.Type.systemBars() or WindowInsetsCompat.Type.displayCutout()
    )
    v.updatePadding(top = bars.top, bottom = bars.bottom, left = bars.left, right = bars.right)
    WindowInsetsCompat.CONSUMED   // 已消费，不再下发
}
```

返回值决定后续分发：

- `WindowInsetsCompat.CONSUMED`——彻底消费，子 View 收不到，避免重复加 padding
- 原样返回 `windowInsets`——继续下发给子 View
- 只想让出一边就别整体消费，避免出现"上下都被顶开两次"

**Android 10（API 29）及以下有个坑**：某个 `ViewGroup` 返回 `CONSUMED` 后，**兄弟节点也收不到** inset，导致兄弟被导航栏压住。消费前先调 `ViewGroupCompat.installCompatInsetsDispatch(root)`（`androidx.core` 1.16.0+）修正这个行为。

## 列表类要用 padding 而不是 margin

```xml
<androidx.recyclerview.widget.RecyclerView
    android:layout_width="match_parent"
    android:layout_height="match_parent"
    android:clipToPadding="false" />
```

`clipToPadding="false"` + 底部 padding = 内容能滑到导航栏底下，但最后一项不会被挡住。用 margin 会让整个列表缩进去，滑动时露出空白条。

## Material 组件

`BottomAppBar`、`BottomNavigationView`、`NavigationRailView`、`NavigationView` 自己处理 inset，不要再手动加 padding（会翻倍）。

**`AppBarLayout` 不自动处理**，给它加 `android:fitsSystemWindows="true"`。

## 键盘（IME）

```kotlin
// 查可见性
val imeVisible = ViewCompat.getRootWindowInsets(view)
    ?.isVisible(WindowInsetsCompat.Type.ime()) == true

// 主动开关键盘
WindowCompat.getInsetsController(window, editText).run {
    show(WindowInsetsCompat.Type.ime())
    hide(WindowInsetsCompat.Type.ime())
}
```

约束：

- Manifest 里配 `android:windowSoftInputMode="adjustResize"`，AndroidX 那套 inset 方案在低版本上才有一致行为
- 想让内容跟着键盘逐帧同步移动（API 30+），用 `ViewCompat.setWindowInsetsAnimationCallback` + `WindowInsetsAnimationCompat.Callback`，四个回调分工：`onPrepare` 存起始位置 → `onStart` 存结束位置 → `onProgress` 每帧改 `translationY` → `onEnd` 清理临时状态
- 用了同步动画就**不要在任何父 `ViewGroup` 里消费 inset**，否则动画拿不到值
- 只需要知道"键盘开始/结束动画"、不需要逐帧的，别注册 `Callback`（它会强制动画跑在主线程），改用 `ViewTreeObserver.WindowInsetsAnimationListener`（高版本可用，系统可放到独立动画线程）

## 沉浸式与系统栏样式

```kotlin
WindowCompat.getInsetsController(window, window.decorView).apply {
    isAppearanceLightStatusBars = false      // 深色背景配浅色图标
    systemBarsBehavior = WindowInsetsControllerCompat.BEHAVIOR_SHOW_TRANSIENT_BARS_BY_SWIPE
    hide(WindowInsetsCompat.Type.systemBars())   // 全屏看图/看视频时才隐藏
}
```

系统栏底下需要色块保护（内容和图标撞色看不清）时：

- 透明栏——`enableEdgeToEdge()` 默认就是，三键导航要透明再加 `window.isNavigationBarContrastEnforced = false`（API 29+，minSdk 低于 29 要加版本判断）
- 半透明渐变——布局外套 `androidx.core.view.insets.ProtectionLayout`（`androidx.core` 1.16.0+），代码里 `setProtections(listOf(GradientProtection(WindowInsetsCompat.Side.TOP, 背景色)))`；渐变色要和内容背景一致
- 手势导航条不要做半透明保护，会显得脏

## 症状 → 排查

| 症状 | 优先查 |
|---|---|
| 标题/按钮被状态栏压住 | 根本没处理 inset；或只在低版本手动 `enableEdgeToEdge` 而高版本走了默认强制 |
| 底部按钮被导航栏挡一半 | 只处理了 `top`，没处理 `bottom`；或用了 margin 但父容器已消费 |
| 上下被顶开两倍距离 | 父子都加了 inset padding；或 Material 组件已自动处理又手动加了一次 |
| 兄弟 View 被导航栏压住（只在旧机器上） | API 29 及以下 `CONSUMED` 不下发给兄弟，缺 `ViewGroupCompat.installCompatInsetsDispatch` |
| 列表最后一项被挡 / 滑动时露白条 | `clipToPadding` 没设 false，或该用 padding 的地方用了 margin |
| 键盘弹出内容不动 | 缺 `adjustResize`；或父容器消费了 inset；或没处理 `Type.ime()` |
| 键盘动画和内容错位、闪一下 | 用了 `WindowInsetsAnimationCompat` 但同时在父容器消费 inset；或在 `onProgress` 里改了布局属性而不是 `translationY` |
| 设了 `statusBarColor` 没效果 | Android 15 上该 API 完全无效，改用 `ProtectionLayout` 或自绘背景 |
| 横屏内容被刘海切掉 | 没处理 `displayCutout()`；`layoutInDisplayCutoutMode` 已被强制成 `ALWAYS`，指望它挡住刘海没用 |
