---
name: android-view-wiki
description: Android View 层知识库，覆盖测量布局时序、多态切换、属性动画、ConstraintLayout 约束链、RecyclerView、触摸事件分发、绘制与渲染性能、WindowInsets 与边到边适配、自定义 View/ViewGroup 规范、渲染管线与掉帧原理。当需要写或改自定义 View、做视图切换/动画、调布局位置与约束、处理状态栏导航栏刘海遮挡或键盘遮挡、排查显示不出来/尺寸不对/动画错乱/列表状态错乱/点击无响应/属性不生效/旋转后状态丢失/卡顿掉帧时使用。
---

# Android View Wiki

查询型知识库。只在**需要确认做法**时读对应 reference，一次读一个，不要整包拉进上下文。

## 动手前的方案检查（最重要）

写任何视图切换、动画、自定义布局之前，先回答这三个问题：

1. **这个方案需要哪些运行时尺寸？** 需要 `width`/`height`/`translationY` 基准值等任何测量结果的，都算。
2. **这些尺寸在我要用的那一刻拿得到吗？** `GONE` 的 View 尺寸是 0；刚 `setText`/刚 `VISIBLE` 的 View 尺寸是旧值或 0；`onCreate`/`onViewCreated` 里所有尺寸都是 0。
3. **拿不到的话，有没有不需要尺寸的等价方案？** 通常有，而且更简单。

如果第 2 问答案是"要等布局回调"，**先换方案，不要想办法把尺寸抠出来**。手动 `measure()`、`doOnLayout`、`post{}`、自己缓存高度，这些都是在跟框架的测量流程对抗，是复杂度和 bug 的主要来源。

判断信号：**同一个显示问题修了两次还不对，就不要修第三次，回退方案。**需要写长注释解释"为什么这里不能用 `isLaidOut`"的实现，说明地基有问题。

## 路由

| 问题 | 读 |
|---|---|
| 尺寸拿不到、显示不出来/尺寸不对、多态切换、`onMeasure`/`onLayout`、`wrap_content` 不生效 | [references/measure-layout.md](references/measure-layout.md) |
| 动画错乱/残留、取消与复位、多个动画改同一属性、无限动画、动画与生命周期 | [references/animation.md](references/animation.md) |
| 位置不对、改一个 margin 连带整列移动、`GONE` vs `INVISIBLE`、约束链、层级遮挡 | [references/constraintlayout.md](references/constraintlayout.md) |
| 列表内容错乱/状态串位、刷新闪烁、滚动卡顿、嵌套滑动 | [references/recyclerview.md](references/recyclerview.md) |
| 点击无响应、滑动冲突、事件分发与拦截、点击区域 | [references/touch-event.md](references/touch-event.md) |
| `onDraw` 怎么写、过度绘制、掉帧卡顿、硬件加速、圆角与裁剪 | [references/draw-performance.md](references/draw-performance.md) |
| 被状态栏/导航栏/刘海挡住、键盘遮挡输入框、边到边适配、沉浸式全屏 | [references/window-insets.md](references/window-insets.md) |
| 写自定义 View/ViewGroup、自定义属性不生效、改了字段没刷新、旋转后状态丢失、子 View margin 失效 | [references/custom-view.md](references/custom-view.md) |
| 一帧是怎么产生的、`invalidate`/`requestLayout` 何时执行、掉帧与冻结帧定义、卡顿该往哪查 | [references/render-pipeline.md](references/render-pipeline.md) |

判断不了归哪类时，显示/尺寸问题读 `measure-layout.md`，位置问题读 `constraintlayout.md`，被系统 UI 挡住读 `window-insets.md`。

## 硬规则速查

不用读 reference 就该遵守的：

- **多态切换用可见性互斥（`VISIBLE`/`GONE`）+ `wrap_content`**，让框架自己算高度；不要把两态拼成一列平移换页再手动锁高
- 任何时候不要在 `onCreate`/`onViewCreated`/刚 `setVisibility` 之后立刻读 `width`/`height`，那时是 0 或旧值
- 需要基于尺寸做位移动画时，优先改用**固定 dp 偏移 + alpha**，不依赖内容尺寸
- 作为约束链锚点、或后面还有元素依赖它的 View，隐藏用 `INVISIBLE` 不用 `GONE`，否则整条链会塌
- 动画在 `onDetachedFromWindow` 必须 `cancel()`；无限动画（`repeatCount = INFINITE`）不 cancel 会一直持有 View
- 动画取消后要显式复位被改过的属性（`alpha`/`translationX/Y`/`scale`），否则残留到下次显示
- 同一个属性同时只允许一个动画在跑，多个动画改同一属性要时序错开或合并成 `PropertyValuesHolder`
- `postDelayed` 的 Runnable 要在 `onDetachedFromWindow`/`hide` 里 `removeCallbacks`
- RecyclerView 的 `onBindViewHolder` 必须处理所有分支（if 有 else），复用会带来上一条的残留状态
- 自定义 View 的 `onDraw` 里禁止 `new` 对象（`Paint`/`Rect`/`Path` 提到成员变量）
- 动画只动绘制属性（`translationX/Y`、`alpha`、`rotation`、`scaleX/Y`），不要动 `margin`/`padding`/`layoutParams`——后者每帧触发整棵子树重新测量
- `targetSdk 35` 起窗口默认边到边，系统栏遮挡一律用 `WindowInsetsCompat` 处理；`statusBarColor`、`setDecorFitsSystemWindows`、`SYSTEM_UI_FLAG_*` 已废弃且无效
- 自定义 View 的属性 setter 必须触发刷新：尺寸/位置变了 `requestLayout()`，只有外观变了 `invalidate()`；漏了就是"改了没反应"
- `obtainStyledAttributes` 返回的 `TypedArray` 必须 `use {}` 或 `recycle()`
- 自定义 ViewGroup 想支持子 View 的 `layout_margin`，必须重写 `generateLayoutParams`/`generateDefaultLayoutParams`/`checkLayoutParams`
- 自定义 View 要保留状态必须有 `android:id`，否则 `onSaveInstanceState` 不会被调用

## 判断标准

改完自问：**这段代码有没有在"猜"或"抢"某个尺寸？** 有的话大概率还有更简单的方案。

## 扩展

同类知识库按技术域各建一个目录，保持 `SKILL.md` 路由 + `references/` 细节的结构：

```
<skill 源目录>/
├── kotlin-wiki/
├── android-view-wiki/
│   ├── SKILL.md
│   └── references/
└── <其他技术域>-wiki/
```

新增 reference 时同步更新上面的路由表，否则不会被命中。
