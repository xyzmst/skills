# 自定义 View 与自定义 ViewGroup

测量相关看 measure-layout.md，`onDraw` 性能看 draw-performance.md。这里只讲一个自定义组件"写完整"需要哪些部件。

## 骨架

```kotlin
class RatingBarView @JvmOverloads constructor(
    context: Context,
    attrs: AttributeSet? = null,
    defStyleAttr: Int = 0,
) : View(context, attrs, defStyleAttr) {

    private val paint = Paint(Paint.ANTI_ALIAS_FLAG)   // 成员，不在 onDraw 里创建

    init {
        context.obtainStyledAttributes(attrs, R.styleable.RatingBarView, defStyleAttr, 0).use {
            starCount = it.getInt(R.styleable.RatingBarView_starCount, 5)
            starColor = it.getColor(R.styleable.RatingBarView_starColor, Color.YELLOW)
        }
    }
}
```

要点：

- `@JvmOverloads` 的三参构造是底线：只写 `(Context)` 一个构造，XML 里用不了；少了 `AttributeSet` 那个，布局预览也起不来
- `use {}`（`androidx.core.content.res`）自动 `recycle()`；手写 `try/finally { recycle() }` 也行，但**绝不能不回收**，`TypedArray` 是共享池对象
- 不要直接读 `AttributeSet`：那样拿不到资源引用（`@dimen/xx` 不会被解析）也不套用 style，必须过 `obtainStyledAttributes`

## 自定义属性

`res/values/attrs.xml`，`declare-styleable` 的 name 按约定**等于类名**（很多 IDE 的补全依赖这个约定）：

```xml
<resources>
    <declare-styleable name="RatingBarView">
        <attr name="starCount" format="integer" />
        <attr name="starColor" format="color" />
        <attr name="labelPosition" format="enum">
            <enum name="left" value="0" />
            <enum name="right" value="1" />
        </attr>
    </declare-styleable>
</resources>
```

XML 里用 `res-auto` 命名空间，标签写全限定类名：

```xml
<LinearLayout xmlns:android="http://schemas.android.com/apk/res/android"
    xmlns:app="http://schemas.android.com/apk/res-auto">
    <com.example.widget.RatingBarView
        app:starCount="5"
        app:starColor="@color/gold" />
</LinearLayout>
```

内部类要写成 `com.example.widget.RatingBarView$StarView`。

## 属性 setter 必须触发刷新

XML 属性只在初始化时读一次，任何会影响显示的状态都要配一个 setter，并在里面主动申请刷新——**漏掉是自定义 View 最典型的"改了没反应"来源**：

```kotlin
var starCount: Int = 5
    set(value) {
        if (field == value) return   // 挡住重复赋值，避免每帧触发重排
        field = value
        requestLayout()              // 尺寸/位置会变
        invalidate()                 // 外观会变
    }

var starColor: Int = Color.YELLOW
    set(value) {
        if (field == value) return
        field = value
        invalidate()                 // 只影响外观，不要 requestLayout
    }
```

判断标准：**尺寸或位置变了 → `requestLayout()`；只有外观变了 → `invalidate()`。** 硬件加速下不 `invalidate()` 就不会重新执行 `draw(Canvas)`，也不能指望"别的 View 脏了顺带把我重绘"（那种偶然生效的写法会随着布局改动突然失效）。

非 UI 线程改状态用 `postInvalidate()`。

## 尺寸相关的回调

| 需求 | 用 |
|---|---|
| 尺寸确定后算一次几何（半径、圆心、路径） | `onSizeChanged(w, h, oldw, oldh)` |
| 尺寸变化时重算缓存的 `Path`/渐变 | `onSizeChanged`，不要放 `onDraw` |
| 依附/脱离窗口时启停动画、注册/注销监听 | `onAttachedToWindow` / `onDetachedFromWindow` |

`onDetachedFromWindow` 里必须 `animator.cancel()` + `removeCallbacks(runnable)`，细节见 animation.md。

## 状态保存与恢复

旋转、进程重启后要保留自身状态（进度、展开态、选中项）的自定义 View，自己实现存取：

```kotlin
override fun onSaveInstanceState(): Parcelable =
    Bundle().apply {
        putParcelable(KEY_SUPER, super.onSaveInstanceState())
        putInt(KEY_PROGRESS, progress)
    }

override fun onRestoreInstanceState(state: Parcelable?) {
    val bundle = state as? Bundle ?: return super.onRestoreInstanceState(state)
    progress = bundle.getInt(KEY_PROGRESS)
    super.onRestoreInstanceState(BundleCompat.getParcelable(bundle, KEY_SUPER, Parcelable::class.java))
}
```

三个硬条件：

- **XML 里必须有 `android:id`**，没 id 的 View 不参与状态保存，这是"状态莫名丢失"的第一嫌疑
- 同一层级里多个同 id 实例（比如代码动态添加的多份）状态会互相串，要么给不同 id，要么 `isSaveEnabled = false` 由外部托管
- 恢复顺序：先取出自己的字段，`super.onRestoreInstanceState` 传回 super 那份，别把整个 `Bundle` 传给 super

## 自定义 ViewGroup

```kotlin
class VerticalStackLayout @JvmOverloads constructor(
    context: Context, attrs: AttributeSet? = null, defStyleAttr: Int = 0,
) : ViewGroup(context, attrs, defStyleAttr) {

    override fun onMeasure(widthMeasureSpec: Int, heightMeasureSpec: Int) {
        var usedHeight = 0
        var maxWidth = 0
        children.forEach { child ->
            if (child.isGone) return@forEach
            measureChildWithMargins(child, widthMeasureSpec, 0, heightMeasureSpec, usedHeight)
            val lp = child.layoutParams as MarginLayoutParams
            usedHeight += child.measuredHeight + lp.topMargin + lp.bottomMargin
            maxWidth = maxOf(maxWidth, child.measuredWidth + lp.leftMargin + lp.rightMargin)
        }
        setMeasuredDimension(
            resolveSize(maxWidth + paddingLeft + paddingRight, widthMeasureSpec),
            resolveSize(usedHeight + paddingTop + paddingBottom, heightMeasureSpec),
        )
    }

    override fun onLayout(changed: Boolean, l: Int, t: Int, r: Int, b: Int) {
        var top = paddingTop
        children.forEach { child ->
            if (child.isGone) return@forEach
            val lp = child.layoutParams as MarginLayoutParams
            val left = paddingLeft + lp.leftMargin
            child.layout(left, top + lp.topMargin, left + child.measuredWidth, top + lp.topMargin + child.measuredHeight)
            top += child.measuredHeight + lp.topMargin + lp.bottomMargin
        }
    }

    // 不重写这三个，XML 里的 layout_margin 会被直接忽略
    override fun generateLayoutParams(attrs: AttributeSet?) = MarginLayoutParams(context, attrs)
    override fun generateDefaultLayoutParams() =
        MarginLayoutParams(LayoutParams.WRAP_CONTENT, LayoutParams.WRAP_CONTENT)
    override fun checkLayoutParams(p: LayoutParams?) = p is MarginLayoutParams
}
```

要点：

- 想支持 `layout_margin` 就必须重写 `generateLayoutParams` / `generateDefaultLayoutParams` / `checkLayoutParams` 返回 `MarginLayoutParams`，否则 margin 静默失效
- `GONE` 的子 View 要在 measure 和 layout 两处都跳过，只跳一处会留出空洞或位置错位
- `measureChildWithMargins` 的后两个参数是"已被占用的宽/高"，传对了子 View 才能拿到正确的剩余空间
- `setMeasuredDimension` 一律经 `resolveSize`，尊重父容器给的 spec
- 需要子 View 携带自定义布局参数（权重、对齐方式）时，继承 `MarginLayoutParams` 自建 `LayoutParams` 并在 `generateLayoutParams` 里解析

## 无障碍

对外发布或长期维护的组件补上：内容语义用 `contentDescription`；状态变化用 `sendAccessibilityEvent(AccessibilityEvent.TYPE_VIEW_SELECTED)` 之类通知；可点击区域保证 48dp。纯装饰性 View 设 `importantForAccessibility="no"`。

## 症状 → 排查

| 症状 | 优先查 |
|---|---|
| XML 里加不上，`inflate` 崩 | 缺 `(Context, AttributeSet)` 构造；类名没写全限定；内部类没用 `$` |
| 自定义属性读不到 / 一直是默认值 | `declare-styleable` 名字和 `R.styleable.xx` 不匹配；用了 `android:` 命名空间而不是 `app:`；直接读 `AttributeSet` 没过 `obtainStyledAttributes` |
| 属性里写 `@dimen/xx` 不生效 | 直接读 `AttributeSet`，资源引用没被解析 |
| 改了字段界面没变 | setter 里漏了 `invalidate()`；尺寸变了只 `invalidate()` 没 `requestLayout()` |
| 时不时 OOM / 卡顿变严重 | `TypedArray` 没 `recycle()`；`onDraw` 里创建对象 |
| 旋转后状态丢失 | 没写 `onSaveInstanceState`；或 View 没设 `android:id` |
| 多个实例状态互相串 | 同 id 多实例，改 id 或关掉自身保存 |
| 子 View 的 margin 完全没效果 | 自定义 ViewGroup 没重写 `generateLayoutParams` |
| 隐藏子 View 后留下空洞 | measure/layout 只跳过了一处 `GONE` |
| 放进 `ScrollView` 后高度变 0 | `onMeasure` 没处理 `UNSPECIFIED`，见 measure-layout.md |
