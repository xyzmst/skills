# ConstraintLayout 与布局位置

## 改 margin 之前先理清约束链

`ConstraintLayout` 里一串首尾相接的 View 是**依赖链**：改动其中一个的 `margin`，所有挂在它上面的元素会整体跟着移动。

```xml
<!-- 从下往上：D 贴底，C 挂 D，B 挂 C，A 挂 B -->
<View android:id="@+id/d" app:layout_constraintBottom_toBottomOf="parent" android:layout_marginBottom="90dp" />
<View android:id="@+id/c" app:layout_constraintBottom_toTopOf="@id/d" />
<View android:id="@+id/b" app:layout_constraintBottom_toTopOf="@id/c" />
```

把 `d` 的 `marginBottom` 从 90dp 改成 180dp，`c` 和 `b` 会一起上移 90dp。只想动其中一个时，**先让它脱离链、独立约束到父容器**，再调它自己的 margin：

```xml
<!-- c 独立贴底，不再跟着 d 走 -->
<View android:id="@+id/c" app:layout_constraintBottom_toBottomOf="parent" android:layout_marginBottom="90dp" />
```

动手前先把链画出来（谁挂谁），比改完看效果再返工快得多。

## `GONE` 会让链塌掉

链上某个 View 置 `GONE` 后，它的尺寸变 0，**依赖它的元素会移动到它的位置**，整条链塌一截。

- **作为链锚点、或后面还有元素依赖它的 View，隐藏用 `INVISIBLE`**，占位保留，链不动
- 确实要让它腾出空间时才用 `GONE`
- 需要"`GONE` 之后用另一个 margin"，用 `layout_goneMarginBottom` / `goneMarginTop` 等：

```xml
<View app:layout_constraintBottom_toTopOf="@id/c"
    android:layout_marginBottom="8dp"
    app:layout_goneMarginBottom="20dp" />   <!-- c 为 GONE 时改用 20dp -->
```

同一个 View 在不同代码路径里一会儿 `GONE` 一会儿 `INVISIBLE`，是位置抖动的常见来源。统一好。

## 尺寸

| 写法 | 含义 |
|---|---|
| `0dp` | `match_constraint`，撑满两侧约束之间。**不是 0** |
| `wrap_content` | 内容尺寸，但仍受约束挤压（可加 `app:layout_constrainedWidth="true"` 让它真的被约束限制） |
| `match_parent` | 在 ConstraintLayout 里不推荐，用 `0dp` + 约束到 parent |

`0dp` 配合 `layout_constraintWidth_percent`、`layout_constraintDimensionRatio="16:9"`、`layout_constraintWidth_max` 可以做百分比/等比/上限。

## 链（chain）

两个及以上 View 用约束互相首尾指向，形成链，由链头的 `layout_constraintHorizontal_chainStyle` 控制分布：

- `spread`（默认）：剩余空间均分到每个间隙
- `spread_inside`：两端贴边，中间均分
- `packed`：整体聚拢，配合 `bias` 调整整体位置

单个 View 两侧都有约束时，`layout_constraintHorizontal_bias`（0~1）控制它在两个约束之间的偏向，默认 0.5 居中。

## 辅助组件

| 组件 | 用途 |
|---|---|
| `Guideline` | 按 dp（`begin`/`end`）或百分比（`percent`）的参考线 |
| `Barrier` | 取一组 View 的最边缘作为屏障，用于"跟随最长的那个"，比链更适合内容不定长的场景 |
| `Group` | 批量控制一组 View 的 `visibility`（只管可见性，不影响布局） |
| `Flow` | 虚拟流式布局，多个 View 自动换行排列 |
| `Placeholder` | 运行时把某个 View 挪到占位处 |

一组 View 要一起显示/隐藏，用 `Group` 比逐个 `setVisibility` 干净。

## 遮挡与绘制顺序

同层级重叠时，**后声明的 View 画在上面**。要改变：

- 把 View 挪到 XML 最后（最稳，无运行时开销）
- `android:elevation`（API 21+，会带阴影）
- `android:translationZ`（不带默认阴影语义）
- `bringToFront()`——会重排子 View 顺序并触发父容器 `requestLayout()`，**每次调用都有开销，不要在频繁执行的路径里调**

XML 顺序、`elevation`、`bringToFront()` 三者混用会互相干扰，选一种。已经放在 XML 最后的 View 不需要再 `bringToFront()`。

## 裁剪

- `clipChildren="false"`：允许子 View 绘制超出自己边界（做溢出动画、阴影时需要）。**注意：只影响绘制，不影响触摸**——超出父边界的部分点不到
- `clipToPadding="false"`：内容可以画进 padding 区域，常用于 RecyclerView 首尾留白且能滚进去
- 要生效通常需要**从目标 View 一路到根容器**都设 `false`

## 约束是容器内的资源

`layout_constraint*` 只在**直接父容器是 `ConstraintLayout`** 时有效：写在 `FrameLayout` 子 View 上不生效（常见于从 ConstraintLayout 搬迁后残留），跨两个不同布局文件的 View 之间也无法互相约束。

所以「新 View 放哪个布局」先于「它的位置怎么写」：要和它争同一块占位空间的元素在哪个容器，它就得进那个容器。放到公共层图省事，位置就只能写死 dp 去猜——而对方高度通常是内容驱动的（文案折行、多态切换），固定 dp 永远对不齐。

同一个 View 有两个独立的层级问题，只答一个不算答完：**谁盖谁**（z 序，跨容器也能靠 XML 顺序 / `elevation` 解决）和**谁挤谁**（占位，只能靠同容器内的约束链解决）。

## 症状 → 排查

| 症状 | 优先查 |
|---|---|
| 新 View 与既有元素重叠，调 margin 怎么调都对不齐 | 两者是否在同一个 `ConstraintLayout` 内；不在就挂不上约束，先改归属再谈位置 |
| 写了 `layout_constraint*` 完全没反应 | 直接父容器是不是 `ConstraintLayout`（`FrameLayout` 里的这些属性是死代码） |
| 改了一个元素的 margin，别的也跟着动 | 约束链依赖，把它拆成独立约束 |
| 隐藏某个 View 后其他元素跳动 | 该 View 是链锚点，`GONE` 改成 `INVISIBLE` |
| 位置和预期差一截，且随内容长度变化 | 位置依赖了兄弟 View 的高度，改成独立的固定 margin |
| 被别的 View 盖住 | 声明顺序 / `elevation`；别叠加多种手段 |
| 溢出部分显示不全 | 链路上某层 `clipChildren` 没关 |
| 溢出部分能看到但点不到 | 触摸不受 `clipChildren` 影响，改布局结构或用 `TouchDelegate` |
| 约束写了但没生效 | 少写了对向约束（只有 top 没有 bottom 时 bias 不起作用）；或 id 引用错层级 |
