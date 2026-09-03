# 触摸事件分发

## 分发链

事件从上往下传，从下往上处理：

```
Activity.dispatchTouchEvent
  └─ ViewGroup.dispatchTouchEvent
       ├─ onInterceptTouchEvent  → 返回 true 则自己截胡，子 View 收到 ACTION_CANCEL
       └─ child.dispatchTouchEvent
            └─ View.onTouchEvent → 返回 true 表示消费
                 （没人消费则逐级回传给父级 onTouchEvent）
```

处理顺序上，`OnTouchListener.onTouch` 先于 `View.onTouchEvent`；`onTouch` 返回 true 会拦掉 `onClick`。

## `ACTION_DOWN` 决定后续

**`ACTION_DOWN` 时返回 `false` 的 View，后续的 `MOVE`/`UP` 一律收不到。** 想要处理滑动就必须先消费 `DOWN`：

```kotlin
override fun onTouchEvent(event: MotionEvent): Boolean {
    when (event.actionMasked) {
        MotionEvent.ACTION_DOWN -> return true   // 先接住，否则没有后续
        MotionEvent.ACTION_MOVE -> { /* ... */ }
        MotionEvent.ACTION_UP -> { /* ... */ }
    }
    return super.onTouchEvent(event)
}
```

`onInterceptTouchEvent` 在 `ACTION_DOWN` 返回 true 会导致所有子 View 永远收不到事件，通常只在 `ACTION_MOVE` 判定为滑动后才拦截。

## 滑动冲突

**外部拦截法**（推荐，逻辑集中在父容器）：父容器在 `onInterceptTouchEvent` 的 `ACTION_MOVE` 里判断方向，属于自己的手势才拦截。

```kotlin
override fun onInterceptTouchEvent(ev: MotionEvent): Boolean {
    return when (ev.actionMasked) {
        MotionEvent.ACTION_DOWN -> {
            downX = ev.x; downY = ev.y
            false                                    // DOWN 绝不拦
        }
        MotionEvent.ACTION_MOVE -> {
            val dx = abs(ev.x - downX)
            val dy = abs(ev.y - downY)
            dy > dx && dy > touchSlop                // 判定为纵向滑动才接管
        }
        else -> false
    }
}
```

`touchSlop` 用 `ViewConfiguration.get(context).scaledTouchSlop`，不要写死阈值。

**内部拦截法**：子 View 在需要时调 `parent.requestDisallowInterceptTouchEvent(true)` 让父级别拦。用于子 View 更清楚何时该独占手势的场景（比如内层横滑控件）。记得在 `ACTION_UP`/`CANCEL` 时置回 `false`。

## 点击无响应排查清单

按这个顺序查：

1. `isClickable` / `isEnabled` 是否为 true（`setOnClickListener` 会自动置 `clickable`，但 `isEnabled=false` 仍然不响应）
2. `visibility` 是不是 `INVISIBLE`/`GONE`（这两种都不接收事件）
3. `alpha` 是不是 0（能收到事件，但用户看不见，容易误判）
4. 是否**超出了父容器边界**——`clipChildren="false"` 只让它画得出来，**触摸区域依然被父容器裁掉**，超出部分点不到
5. 父容器是否拦截了（`onInterceptTouchEvent`）
6. 上面是否盖了一个透明的、消费事件的 View（全屏遮罩、`elevation` 更高的容器）
7. 是否用了补间动画（`Animation`）移动位置——真实点击区域没跟着动，属性动画才会

## 扩大点击区域

小图标点击区域不足时，优先加 padding；不能改布局时用 `TouchDelegate`：

```kotlin
parent.post {
    val rect = Rect()
    child.getHitRect(rect)
    val extra = 12.dp
    rect.inset(-extra, -extra)
    parent.touchDelegate = TouchDelegate(rect, child)
}
```

限制：一个父容器只能有一个 `TouchDelegate`（多个要自己合并），且代理区域不能超出父容器自身。

## 多点触控

用 `actionMasked` 而不是 `action`（`action` 里含 pointer index，多指时判断会错）：

```kotlin
when (event.actionMasked) {
    MotionEvent.ACTION_POINTER_DOWN -> { /* 第二根手指按下 */ }
    MotionEvent.ACTION_POINTER_UP -> { /* 某根手指抬起 */ }
}
val pointerId = event.getPointerId(event.actionIndex)  // 跨事件追踪用 id，不用 index
```

手势识别优先用现成的 `GestureDetector`（点击/长按/滑动/快滑）和 `ScaleGestureDetector`（缩放），不要手写。

## 防连点

一个 View 上重复触发的场景（提交、跳转、支付），统一用项目里的 `NoDoubleClickListener` 之类的封装，不要每处自己记时间戳。

## 症状 → 排查

| 症状 | 优先查 |
|---|---|
| 完全点不到 | 上面 7 条清单，重点是超出父边界和透明遮罩 |
| 能点但滑不动 | `ACTION_DOWN` 时返回了 false |
| 滑动被外层抢走 | 父容器拦截，用 `requestDisallowInterceptTouchEvent` |
| 子 View 突然收到 `ACTION_CANCEL` | 父容器中途拦截了 |
| 多指操作时错乱 | 用了 `action` 而不是 `actionMasked`；或用 index 追踪手指 |
