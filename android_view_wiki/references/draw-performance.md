# 绘制与渲染性能

## `onDraw` 铁律

**`onDraw` 里禁止创建对象。**它每帧都可能被调用，`new Paint()` / `new Rect()` / `new Path()` 会制造大量垃圾，触发 GC 造成掉帧。

```kotlin
// 提到成员，复用
private val paint = Paint(Paint.ANTI_ALIAS_FLAG).apply {
    color = Color.WHITE
    style = Paint.Style.FILL
}
private val rect = RectF()

override fun onDraw(canvas: Canvas) {
    rect.set(0f, 0f, width.toFloat(), height.toFloat())   // 复用实例，只改值
    canvas.drawRoundRect(rect, radius, radius, paint)
}
```

同样不要在 `onDraw` 里做字符串拼接、集合操作、`measureText` 之类可以缓存的计算。

## `invalidate` vs `requestLayout`

| 调用 | 触发 | 什么时候用 |
|---|---|---|
| `invalidate()` | 只重绘（`onDraw`） | 只有外观变了 |
| `requestLayout()` | 重新测量 + 布局 + 绘制，**影响整棵树** | 尺寸/位置变了 |

改 `layoutParams`、`margin`、文本内容会隐式触发 `requestLayout`。高频路径（倒计时、进度更新）里如果每次都触发重新布局，是常见的性能问题——先判断值有没有真的变：

```kotlin
private fun lockHeight(h: Int) {
    val params = layoutParams ?: return
    if (params.height == h) return    // 没变就别动，避免每秒一次重排
    params.height = h
    layoutParams = params
}
```

非 UI 线程要重绘用 `postInvalidate()`。

## 圆角与裁剪

按性能从好到差：

1. **`background` 用 `shape` drawable**——最省，能满足就用它
2. **`ViewOutlineProvider` + `clipToOutline = true`**——GPU 友好，但只支持统一圆角矩形/圆形
3. **`BitmapShader`**——图片圆角用这个，`Glide` 的 `RoundedCorners` 也是这个路子
4. **`canvas.clipPath()`**——任意形状，但开销大且早期版本抗锯齿差，尽量避免
5. **`PorterDuffXfermode` + 离屏缓冲**——最贵，需要 `saveLayer`，非必要不用

## 过度绘制

同一像素被画多次就是过度绘制。开发者选项里"调试 GPU 过度绘制"，蓝色 1 层可接受，绿色 2 层留意，红色以上必须改。

常见来源和处理：

- 主题里已有背景，布局根节点又设了一层 → 去掉根节点的 `background`，或在 Activity 里 `window.setBackgroundDrawable(null)`
- 层层嵌套都设了背景色 → 只保留最上面那层
- 大面积透明 View 叠加 → 能合并就合并
- 自定义 View 画了被遮住的区域 → `canvas.clipRect` 先裁掉不可见部分

## 布局层级

- 层级越深，measure/layout 的耗时越接近指数增长（每层嵌套都可能触发子树二次测量）
- `LinearLayout` 用了 `layout_weight` 会**测量两遍**，嵌套多层时代价很高 → 换 `ConstraintLayout`
- `RelativeLayout` 天然测量两遍
- `ConstraintLayout` 扁平化优先，但它本身在层级很浅时反而比 `LinearLayout` 慢一点，简单场景不必强上
- `<merge>` 消除自定义 View 里多余的根容器；`<ViewStub>` 延迟加载不常显示的部分
- 用 Layout Inspector 看实际层级，不要凭 XML 猜

## 硬件加速

默认开启（API 14+）。注意：

- 部分 `Canvas` API 在硬件加速下不支持或行为不同（`clipPath` 早期版本、`drawTextOnPath`、部分 `Xfermode`），必要时对单个 View `setLayerType(LAYER_TYPE_SOFTWARE, null)`
- `LAYER_TYPE_HARDWARE` 会把 View 缓存成纹理，适合动画期间开、结束后关；**长期开着会占显存**
- 纹理有尺寸上限（通常 2048~4096px），超大 Bitmap 会渲染失败显示空白

## 卡顿排查

1. 先确认是掉帧还是主线程阻塞——`Choreographer.FrameCallback` 或 Systrace/Perfetto 看
2. 主线程阻塞：查 IO、数据库、`SharedPreferences.commit`、大 JSON 解析、主线程网络回调
3. 渲染慢：查过度绘制、层级、`onDraw` 里的对象创建、Bitmap 尺寸
4. 频繁 GC：查高频路径里的对象创建（`onDraw`、`onBindViewHolder`、动画 update 回调）
5. 布局抖动：查是不是有代码在每帧触发 `requestLayout`

Bitmap 是内存和渲染的首要嫌疑：加载时按目标尺寸采样，不要把 4000×3000 的图塞进 100dp 的 ImageView。

## 症状 → 排查

| 症状 | 优先查 |
|---|---|
| 滑动掉帧 | 过度绘制、层级深度、`onBindViewHolder` 耗时 |
| 首帧慢/白屏 | 布局层级、`onCreate` 里的同步初始化、主题背景 |
| 动画不流畅 | 是否在动 `layoutParams` 而不是 `translation`；是否没开硬件层 |
| 内存涨得快 | Bitmap 没采样；`LAYER_TYPE_HARDWARE` 长期开着；无限动画没 cancel |
| 自定义 View 画着画着变卡 | `onDraw` 里创建对象 |
