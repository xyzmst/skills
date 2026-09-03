# 属性动画

## 选型

| 场景 | 用 |
|---|---|
| 改 View 的一个属性 | `ViewPropertyAnimator`（`view.animate()`），最简洁 |
| 改 View 的多个属性、要复用/精细控制 | `ObjectAnimator` + `PropertyValuesHolder` |
| 驱动非 View 的值（进度、颜色、自绘参数） | `ValueAnimator` + `addUpdateListener` |
| 多个动画编排 | `AnimatorSet`（`playTogether` / `playSequentially` / `after`） |
| 布局变化自动过渡 | `TransitionManager.beginDelayedTransition(parent)` 后改可见性/约束 |

补间动画（`Animation`/`ViewAnimationUtils` 那套 `android.view.animation`）只改绘制不改真实属性，点击区域不跟着走，新代码不要用。

## 多属性合并

同一个 View 同时改多个属性，合并成一个 animator，不要起多个：

```kotlin
ObjectAnimator.ofPropertyValuesHolder(
    view,
    PropertyValuesHolder.ofFloat(View.TRANSLATION_Y, 12f, 0f),
    PropertyValuesHolder.ofFloat(View.ALPHA, 0f, 1f)
).apply {
    duration = 250
    interpolator = AccelerateDecelerateInterpolator()
    start()
}
```

起多个 animator 改同一个属性会互相覆盖，表现为"动画抖动/跳变"，且取消时只取消了其中一个。

## 取消后 `onAnimationEnd` 照样会调

这是最容易出 bug 的一点：**`cancel()` 会先触发 `onAnimationCancel`，紧接着还会触发 `onAnimationEnd`**。如果 `onAnimationEnd` 里写了"切到下一状态"，取消动画反而会推进状态。

标准防护（用标志位）：

```kotlin
addListener(object : AnimatorListenerAdapter() {
    private var canceled = false

    override fun onAnimationCancel(animation: Animator) {
        canceled = true
    }

    override fun onAnimationEnd(animation: Animator) {
        if (canceled) return
        // 只有正常播完才走这里
    }
})
```

用 `androidx.core.animation.doOnEnd` 也一样有这个问题，它的 lambda 收到的 `isReverse` 参数不区分取消。需要区分就老老实实用上面的写法，或者用 `doOnCancel` 配合标志位。

## 取消要连带复位

动画改过的属性不会自己回去。取消/隐藏时必须显式复位，否则残留到下次显示：

```kotlin
private fun reset() {
    pendingRunnable?.let { removeCallbacks(it) }   // 延迟任务也要清
    pendingRunnable = null
    animator?.cancel()
    animator = null
    view.translationY = 0f
    view.alpha = 1f
    view.scaleX = 1f
    view.scaleY = 1f
}
```

把复位收敛到一个方法里，`show()` 开头和 `hide()` 都调它，比在每个分支里零散复位可靠得多。

## 生命周期

```kotlin
override fun onDetachedFromWindow() {
    pendingRunnable?.let { removeCallbacks(it) }
    animator?.cancel()
    super.onDetachedFromWindow()
}
```

- **无限动画必须 cancel**：`repeatCount = ValueAnimator.INFINITE` 的动画持有 View 引用，不 cancel 会一直跑，Activity/Fragment 销毁后造成泄漏
- `postDelayed` 的 Runnable 同样要 `removeCallbacks`，否则 View 已经不可见了动画还会启动
- Fragment 里的动画在 `onDestroyView` 取消，不要等到 `onDestroy`
- 系统开发者选项里动画时长可以被调成 0，不要让业务逻辑依赖"动画一定会执行一段时间"

## 动画与可见性配合

- **淡出后隐藏**：`alpha` 动画结束后再 `isVisible = false`，不要同时做
- **显示后淡入**：先 `isVisible = true`（此时 `alpha` 应已被复位或设为 0），再启动动画
- `GONE` 的 View 上跑动画不会有任何视觉效果，但动画照样在跑、照样回调
- 两个动画分别改同一 View 的 `alpha`（比如淡入动画和闪烁动画），必须时序错开：淡入结束再启动闪烁，且闪烁启动前先把 `alpha` 复位

## 闪烁 / 呼吸效果

```kotlin
ObjectAnimator.ofFloat(view, View.ALPHA, 1f, 0.35f).apply {
    duration = 500
    repeatMode = ValueAnimator.REVERSE      // 往返，不是 RESTART
    repeatCount = ValueAnimator.INFINITE
    start()
}
```

`RESTART`（默认）会在每轮结束时瞬间跳回起点，看起来是"闪断"；要平滑往返必须用 `REVERSE`。

## 性能

- 动画期间开硬件层可以省掉重复绘制：`view.animate().withLayer()`，或手动 `setLayerType(LAYER_TYPE_HARDWARE, null)` 并在结束后置回 `LAYER_TYPE_NONE`
- 优先动 `translationX/Y`、`alpha`、`scale`、`rotation`——这些只触发重绘不触发重新布局
- 动 `layoutParams.height`/`margin` 会每帧 `requestLayout()`，整棵树重新测量，能避免就避免
- 列表项动画不要用无限动画，滚动复用时容易漏 cancel

## 症状 → 排查

| 症状 | 优先查 |
|---|---|
| 取消动画反而推进了状态 | `cancel()` 后 `onAnimationEnd` 照样回调，用 `canceled` 标志挡住 |
| 属性停在中间值、界面半透明或偏移残留 | 取消时没复位，复位逻辑要收敛到一个方法 |
| 多个动画改同一属性时跳变 | 合并成 `PropertyValuesHolder`，同一属性同时只允许一个动画 |
| 离开页面后动画还在跑、内存泄漏 | `onDetachedFromWindow` 漏了 `cancel()`，`INFINITE` 的必漏 |
| 呼吸效果每轮开头"闪断" | `repeatMode` 用了默认的 `RESTART`，要 `REVERSE` |
| 动画期间明显掉帧 | 动了 `layoutParams`/`margin` 触发每帧重新布局，改用 `translation`/`alpha` |
| 列表滚动后动画错乱 | 列表项用了无限动画且复用时漏 cancel |
| 隐藏动画结束后还占位或提前消失 | 可见性切换时机，见「动画与可见性配合」 |
| 需要按内容尺寸做位移动画但尺寸拿不到 | 方案问题，见 measure-layout.md |
