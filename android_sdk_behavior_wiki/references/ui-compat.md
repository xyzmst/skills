# 界面兼容性变更

升 targetSdk 之后界面出问题，几乎都是下面四条之一。

## Edge-to-edge 强制（targetSdk 35+）

targetSdk 35 起在 Android 15 设备上**默认全屏铺开**，不处理 insets 的内容会被状态栏、导航栏、刘海挡住。典型受害者：顶部 AppBar、悬浮按钮、列表底部项、底部按钮条。

targetSdk 36 起 `R.attr#windowOptOutEdgeToEdgeEnforcement` 已弃用并停用——在 Android 16 设备上设了也没用（跑在 Android 15 设备上仍然有效）。也就是说**没有退路了**，必须处理 insets。

已经做过 edge-to-edge 的也要复查：需要给状态栏或三按钮导航加自定义背景保护时，用 `WindowInsets.Type#tappableElement()` 拿三按钮导航栏高度、`WindowInsets.Type#statusBars()` 拿状态栏高度，把保护层放到系统栏后面，不要硬编码高度。

具体写法（`enableEdgeToEdge()`、`setOnApplyWindowInsetsListener`、键盘 insets、已废弃的系统栏着色 API）看 `android-view-wiki` 的 `window-insets.md`，这里不重复。

## Configuration 不再排除系统栏（targetSdk 35+）

以前 `Configuration` 返回的窗口尺寸是**扣掉系统栏**的，现在不扣。

- 用 `Configuration` 的宽高**做布局计算**的地方必须改：布局交给 `ConstraintLayout` / `CoordinatorLayout` 自己算，要系统栏高度用 `WindowInsets`，要当前窗口尺寸用 `computeCurrentWindowMetrics()`
- 用它**做资源限定符**（`res/layout-h500dp`）不受影响，继续用

这条不会崩，只会让布局悄悄偏几十 dp，是升级后最难定位的一类问题。

## 预测性返回（targetSdk 36+）

在 Android 16 设备上默认启用返回动画（返回桌面、跨任务、跨 Activity），代价是：

- **`onBackPressed()` 不再被调用**
- **`KeyEvent.KEYCODE_BACK` 不再分发**

拦截返回键做二次确认、关闭抽屉、收起底部弹层的代码会全部失效，而且是静默失效——不崩，就是没反应。

正解是迁移到 `OnBackPressedDispatcher` / `OnBackInvokedCallback`。来不及就先在清单里关掉：

```xml
<application android:enableOnBackInvokedCallback="false">
```

这是过渡手段，迁移仍然要做。

## 大屏忽略方向与尺寸限制（targetSdk 36+）

在最小宽度 ≥ 600dp 的显示屏上，以下声明和调用**全部被忽略**：

- `screenOrientation`（portrait / landscape 及其各种变体）
- `resizableActivity="false"`
- `minAspectRatio` / `maxAspectRatio`
- `setRequestedOrientation()` / `getRequestedOrientation()`

应用直接铺满显示窗口，不再有竖屏黑边兼容模式。例外只有三种：游戏（按 `android:appCategory` 判定）、用户在设备的宽高比设置里显式选择、屏幕小于 sw600dp。

两类连带问题：

1. **布局假设崩塌**——按锁定竖屏设计的界面会被拉伸，动画和绝对定位的元素跑出屏幕
2. **Activity 重建变多**——设备可自由旋转，状态没保存好就会丢。参见 `android-architecture-wiki` 的 `viewmodel-state.md` 区分配置变更和进程死亡

临时停用（单个 Activity 或整个应用）：

```xml
<activity ...>
    <property android:name="android.window.PROPERTY_COMPAT_ALLOW_RESTRICTED_RESIZABILITY" android:value="true" />
</activity>
```

**targetSdk 37 起这个开关失效**，别把它当长期方案。

## 字体行高（targetSdk 35 / 36）

- targetSdk 35：`elegantTextHeight` 默认变 `true`，阿拉伯语、泰语、缅甸语、泰米尔语、印地系等脚本改用行高更大的字体，布局可能被撑开。设 `false` 可恢复
- targetSdk 36：属性被弃用并忽略，设 `false` 也没用

只支持中英文的应用基本无感，做多语言的要过一遍这些语种的布局。

## 全量生效的界面变更（不看 targetSdk）

- Android 16：`announceForAccessibility` 弃用（打断式无障碍播报），改用 `AccessibilityLiveRegion` 等替代方案

## 症状 → 排查

| 症状 | 优先查 |
|---|---|
| 顶部/底部内容被系统栏压住 | targetSdk 35 edge-to-edge，处理 insets |
| 处理了 insets 但状态栏背景变透明不好看 | 用 `statusBars()` / `tappableElement()` 做背景保护，别写死高度 |
| 布局整体偏移几十 dp，说不上哪错了 | targetSdk 35 的 `Configuration` 不再扣系统栏 |
| 返回键无反应，也不崩 | targetSdk 36 预测性返回，`onBackPressed` 不再调用 |
| 平板/折叠屏上强制竖屏失效、界面被拉伸 | targetSdk 36 大屏忽略方向限制 |
| 旋转后用户输入丢失 | 大屏可自由旋转导致重建变多，状态保存没做 |
| 多语言下文本行高变大撑破布局 | `elegantTextHeight`（35 默认 true / 36 强制） |
