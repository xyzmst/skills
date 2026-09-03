# RecyclerView

## 复用带来的状态残留

`onBindViewHolder` 拿到的 `holder` 大概率是别的 item 用过的，**上一条的所有状态都还在**：可见性、选中态、`translationY`、动画、`Glide` 请求、监听器。

铁律：**`onBindViewHolder` 里每个条件分支都要有 else，把状态显式设回去。**

```kotlin
// 错：不满足条件时保留了上一条的 VISIBLE
if (item.hasBadge) holder.badge.isVisible = true

// 对
holder.badge.isVisible = item.hasBadge
holder.itemView.alpha = 1f          // 上一条可能跑过动画
holder.animator?.cancel()           // 上一条可能还在动
```

图片必须走带生命周期的加载并显式设置占位/清理，否则滚动时会出现"先显示上一张再刷新"的闪图。

## 位置获取

```kotlin
// ViewHolder 里
val pos = bindingAdapterPosition
if (pos == RecyclerView.NO_POSITION) return   // 必须判，动画/删除过程中会是 -1
```

- `bindingAdapterPosition`：当前 ViewHolder 在**它自己的 adapter** 里的位置，日常用这个
- `absoluteAdapterPosition`：在 `ConcatAdapter` 合并后的全局位置
- 不要在 `onBindViewHolder` 里捕获 `position` 参数到点击回调里——数据变化后就过期了，一律在回调触发时现取

**监听器在 `onCreateViewHolder` 里设一次**，不要在 `onBindViewHolder` 里反复 `setOnClickListener`（每次绑定 new 一个对象，滚动时产生大量垃圾）。

## 刷新

| 场景 | 用 |
|---|---|
| 整体数据变化 | `ListAdapter` / `DiffUtil`，自动算差异并带动画 |
| 单项内容变化 | `notifyItemChanged(pos, payload)` + 在 `onBindViewHolder(holder, pos, payloads)` 里只更新变化部分 |
| 增删 | `notifyItemInserted` / `notifyItemRemoved`（保留动画） |
| 兜底 | `notifyDataSetChanged()`——丢失所有动画和滚动位置，会重新绑定全部可见项，尽量不用 |

`ListAdapter` 的 `submitList` 是异步 diff 的，连续调用会以最后一次为准；需要在 diff 完成后做事用 `submitList(list) { ... }` 的回调。

`DiffUtil` 的 `areItemsTheSame` 比 id，`areContentsTheSame` 比内容。用 `data class` 时 `areContentsTheSame` 可以直接 `oldItem == newItem`，但要确保类里没有每次都变的字段（时间戳之类）。

## 局部刷新闪烁

`notifyItemChanged` 默认会播放 change 动画（淡出淡入），表现为闪烁。两种解法：

```kotlin
// 用 payload 走局部绑定，不重建整个 item
notifyItemChanged(pos, PAYLOAD_COUNTDOWN)

// 或直接关掉 change 动画
(recyclerView.itemAnimator as? SimpleItemAnimator)?.supportsChangeAnimations = false
```

倒计时之类每秒刷新的场景，一定要用 payload，否则每秒重建一次 item。

## 性能

- `setHasFixedSize(true)`：item 尺寸不随内容变时开，省掉 `requestLayout`
- `setHasStableIds(true)` + `getItemId`：让复用更稳定，配合 diff 效果更好
- 多个同结构 RecyclerView 共享 `RecycledViewPool`
- item 布局层级压平，嵌套超过 3~4 层就该合并
- 避免嵌套滚动同方向的 RecyclerView；确实要嵌套时用 `ConcatAdapter` 打平成一个列表
- 横向 RecyclerView 嵌在纵向里：给内层 `setRecycledViewPool` + `setInitialPrefetchItemCount`
- 不要在 `onBindViewHolder` 里做耗时操作（IO、复杂计算、`inflate`）

## 嵌套滑动

- 内层不想滚动、只想跟随外层：`isNestedScrollingEnabled = false`
- `NestedScrollView` 里放 RecyclerView 会让 RecyclerView 一次性铺开全部 item，**完全失去复用**。用 `ConcatAdapter` 或多 ViewType 替代
- 自定义嵌套滑动实现 `NestedScrollingChild3`/`Parent3` 接口，不要自己拦截事件硬做

## 症状 → 排查

| 症状 | 优先查 |
|---|---|
| 滚动后内容错乱/串位 | `onBindViewHolder` 分支没写全，状态没复位 |
| 点击点到了别的 item | 回调里用了捕获的旧 `position`，改成现取 `bindingAdapterPosition` |
| 刷新时闪烁 | change 动画，用 payload 或关掉 `supportsChangeAnimations` |
| 滚动卡顿 | `onBindViewHolder` 有耗时操作；item 层级太深；图片没压缩 |
| 列表很长时首屏很慢 | 被塞进了 `NestedScrollView`，复用失效 |
| 数据变了但界面没变 | `ListAdapter` 收到的是同一个 list 实例（原地修改），必须提交新 list |
