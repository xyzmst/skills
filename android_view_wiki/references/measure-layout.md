# 测量、布局与多态切换

## 尺寸什么时候才有

View 的生命周期：构造 → `onAttachedToWindow` → `onMeasure` → `onLayout`（此后 `width`/`height` 才有值）→ `onDraw`。

尺寸为 0 或是旧值的时刻：

| 时刻 | `width`/`height` |
|---|---|
| 构造函数、`onCreate`、`onViewCreated`、`onCreateView` | 0 |
| `GONE` 的 View | 0（不参与测量） |
| 刚 `setVisibility(VISIBLE)`，同一帧内 | 0（还没测量） |
| 刚 `setText` / 改完内容，同一帧内 | 旧值 |
| 刚改完 `layoutParams`，同一帧内 | 旧值 |
| `onSizeChanged`、`doOnLayout`、`onLayout` 之后 | 有效 |

`isLaidOut` 只表示"**曾经**布局过"，不表示当前尺寸是最新的。改完内容立刻读高度，`isLaidOut` 是 true 但拿到的是改之前的值——这是最容易踩的坑。

## 先别急着拿尺寸

需要尺寸才能实现的方案，优先换成不需要尺寸的方案。对照表：

| 想做的事 | 依赖尺寸的做法（避免） | 不依赖尺寸的做法（优先） |
|---|---|---|
| 两态切换 | 拼成一列，`translationY = -第一态高度` 换页，父容器锁高 | 两态叠放，`VISIBLE`/`GONE` 互斥，父容器 `wrap_content` |
| 滑入/滑出动画 | 位移量 = 自身高度 | 位移量 = 固定 dp（12dp 左右）+ alpha 淡入淡出 |
| 展开/收起 | 量出内容高度再做高度动画 | `TransitionManager.beginDelayedTransition` + 改可见性 |
| 居中/对齐另一个 View | 运行时读坐标再 `translationY` | 直接写约束（`layout_constraintTop_toTopOf` 等） |
| 撑满剩余空间 | 算父高度减去兄弟高度 | `0dp` + 约束，或 `layout_weight` |

## 多态切换的标准写法

任意时刻只有一个态可见，容器 `wrap_content` 自动等于当前态高度，全程不需要任何尺寸：

```xml
<!-- 两个态叠在同一位置，容器自身是 FrameLayout -->
<TextView android:id="@+id/page_a" android:layout_width="wrap_content" android:layout_height="wrap_content" />
<LinearLayout android:id="@+id/page_b" android:layout_width="wrap_content" android:layout_height="wrap_content"
    android:visibility="gone" />
```

```kotlin
// A 滑出隐藏 → B 再滑入显示，时序错开，高度切换发生在 A 已不可见时
private fun flipToB() {
    val a = binding.pageA
    ObjectAnimator.ofPropertyValuesHolder(
        a,
        PropertyValuesHolder.ofFloat(View.TRANSLATION_Y, 0f, -a.height.toFloat()), // A 此刻可见，height 有效
        PropertyValuesHolder.ofFloat(View.ALPHA, 1f, 0f)
    ).apply {
        duration = 250
        doOnEnd {
            a.isVisible = false
            showB()   // B 用固定偏移滑入，不需要它的高度
        }
        start()
    }
}
```

要点：

- A 滑出时它是可见且已布局的，`a.height` 有效；B 滑入前是 `GONE`，`height` 为 0，所以 B 不能用自身高度做位移
- 两步错开而不是同时跑，否则中间会有一帧两个都可见，容器高度取两者最大值，出现跳变
- 容器 `clipChildren = true`（默认），A 滑出超出的部分自动被裁掉

## 实在要拿尺寸时

按优先级：

1. **`doOnLayout { }`**（`androidx.core.view`）——已布局过就立即执行，否则等下一次布局。一次性场景用这个
2. **`onSizeChanged(w, h, oldw, oldh)`**——自定义 View 内部，尺寸变化时回调，最可靠
3. **`post { }`**——排到下一帧。能用但语义含糊，不保证那时布局已完成
4. **手动 `measure(widthSpec, heightSpec)`**——最后手段。会绕过父容器的约束，量出来的是"内容自然尺寸"，不等于最终布局尺寸；量完还要注意别污染真实的测量结果

`ViewTreeObserver.OnGlobalLayoutListener` 除非要监听多次变化，否则不用，容易忘记 `remove` 造成反复触发。

## MeasureSpec

`onMeasure` 收到的 spec 由父容器根据自己的约束和子 View 的 `layoutParams` 合成：

| 模式 | 含义 | 典型来源 |
|---|---|---|
| `EXACTLY` | 就是这么大 | `match_parent`、固定 dp |
| `AT_MOST` | 最多这么大，自己决定 | `wrap_content` |
| `UNSPECIFIED` | 随便多大 | `ScrollView`/`RecyclerView` 测量子项时 |

自定义 `onMeasure` 的最小正确写法：

```kotlin
override fun onMeasure(widthMeasureSpec: Int, heightMeasureSpec: Int) {
    super.onMeasure(widthMeasureSpec, heightMeasureSpec)   // 先让子 View 测量
    val w = MeasureSpec.getSize(widthMeasureSpec)
    // 算出自己想要的高度 desiredHeight
    setMeasuredDimension(w, resolveSize(desiredHeight, heightMeasureSpec))  // 必须尊重 spec
}
```

`resolveSize` 会按 spec 模式夹取，别直接 `setMeasuredDimension(w, desiredHeight)` 忽略约束。

## `wrap_content` 不生效的常见原因

- 在 `ScrollView`/`RecyclerView` 里，子项收到 `UNSPECIFIED`，自定义 View 若没处理这个模式会算出 0
- 自定义 `onMeasure` 里没调 `super.onMeasure` 也没手动测量子 View，子 View 尺寸全是 0
- `layoutParams.height` 被代码改成过固定值且没改回来（`params.height = xxx` 是持久的）
- 父容器是 `ConstraintLayout` 且用了 `0dp`，那是 `match_constraint` 不是 `wrap_content`

## 症状 → 排查

| 症状 | 优先查 |
|---|---|
| View 只显示一窄条 / 被压扁 | 高度被代码锁死（`layoutParams.height`），或用了过期/为 0 的测量值 |
| 完全不显示 | 父容器高度为 0；`visibility`；被裁剪（超出父边界 + `clipChildren`）；`alpha=0` |
| 一闪而过 | 有代码把它重新置 `GONE`；或状态流每次发射都重建导致动画重启 |
| 首次显示尺寸不对，第二次正常 | 典型的"第一次拿尺寸时还没布局"，说明方案依赖尺寸，该换 |
| 位置整体偏移 | 约束/margin 问题，读 constraintlayout.md |
