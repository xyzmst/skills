# 渲染管线与掉帧原理

理解一帧是怎么产生的，用来判断"这个卡顿该往哪查"。具体优化手段在 draw-performance.md。

## 一帧的链路

```
硬件 Vsync 信号
  └─ Choreographer#doFrame（主线程，一帧只跑一次）
       ├─ INPUT      分发本帧的触摸事件
       ├─ ANIMATION  跑动画回调（ValueAnimator 的 update）
       └─ TRAVERSAL  ViewRootImpl.performTraversals
            ├─ measure   仅当本帧有 requestLayout
            ├─ layout    同上
            └─ draw      Record View#draw：主线程执行 draw(Canvas)，把绘制命令录进 display list
                            ↓ sync（此阶段主线程被阻塞，等 RenderThread 拷数据/上传纹理）
                         DrawFrame：RenderThread 回放 display list、发 GPU 命令
                            ↓
                         SurfaceFlinger 合成上屏
```

关键结论：

- `requestLayout()` / `invalidate()` 都**不是立即执行**，只是标脏 + 申请下一个 Vsync；同一帧内连续调多次只会合并成一次 traversal
- `requestLayout()` 沿父链一路上传到 `ViewRootImpl`，所以它的代价和树的深度、宽度相关；`invalidate()` 只影响自己的 display list
- 主线程只负责"录命令"，真正的 GPU 提交在 RenderThread；主线程 `draw()` 很快不等于帧不卡

## 帧预算与掉帧定义

| 刷新率 | 每帧预算 |
|---|---|
| 60fps | 16ms |
| 90fps | 11ms |
| 120fps | 8ms |

超预算 1ms 不是"晚 1ms 显示"，而是 **Choreographer 直接丢掉整帧**，用户看到的就是卡顿（jank）。

| 分级 | 单帧耗时 | 用户感受 |
|---|---|---|
| 慢帧 | 16ms ~ 700ms | 滑动发涩、动画不顺 |
| 冻结帧（frozen frame） | 700ms ~ 5s | 界面像卡死、无响应 |
| ANR | > 5s | 系统弹无响应对话框 |

冷启动和页面切换的首帧超 16ms 是正常的（要 inflate + 首次测量绘制），所以慢帧和冻结帧要分开看；但任何帧都不该超 700ms。

## display list：为什么动画只能动绘制属性

硬件加速下绘制命令不是立刻执行，而是录进 display list（`RenderNode`）。没被 `invalidate()` 的 View，系统直接回放上一次录好的 display list，**根本不会再调它的 `draw(Canvas)`**。

由此推出两条实践：

- 改了内部数据就必须 `invalidate()`。不能依赖"父/兄弟脏了顺带把我重绘"——那是软件绘制时代的行为，硬件加速下不成立，而且会随布局改动突然失效
- 改 `alpha` / `translationX/Y/Z` / `rotation` / `scaleX/Y` 只更新 `RenderNode` 的属性，**不需要重录 display list、不触发 measure/layout**；改 `margin` / `padding` / `layoutParams` / 文本内容会触发整棵子树重新测量布局

这就是"动画必须动绘制属性"的底层原因，不是风格偏好。同理，`LAYER_TYPE_HARDWARE` 把 View 整个缓存成 GPU 纹理，动画期间开、结束就关（用法见 draw-performance.md）。

## 布局代价的来源

- `RelativeLayout`、带 `layout_weight` 的 `LinearLayout` 会对子 View 触发**多次** measure/layout，嵌套后深度上呈 O(n²)；只在叶子节点附近用，中间层换 `ConstraintLayout`
- 每帧都在 measure/layout（Systrace 里 `Choreographer#doFrame` 的 Layout 段每帧都很长）= 有代码在用布局属性做动画，或高频路径里改了 `layoutParams`
- 正常情况下 layout 只该在新内容上屏时发生（比如 `RecyclerView` 滑入新条目）

## 主线程"没在跑"的两种情况

Systrace/Perfetto 里主线程不是绿色（运行）而是灰（睡）或蓝（可运行未被调度）时，问题不在渲染：

- **binder / IPC 调用**：Android 上主线程停摆最常见的原因，某些看起来无害的系统调用（如查刷新率）内部就是 binder。抓法：`adb shell am trace-ipc start` → 操作 → `adb shell am trace-ipc stop --dump-file /data/local/tmp/ipc-trace.txt`
- **等锁 / 等其他线程结果**：主线程不该等别的线程，应该由别的线程 post 结果过来
- 另外 GC 频繁（`HeapTaskDaemon` 线程占满）说明高频路径在大量分配对象，查 `onDraw`、`onBindViewHolder`、动画 update 回调

注意有些阻塞是正常的：sync 阶段主线程本来就要等 RenderThread 拷贝数据、上传 Bitmap 纹理。

## RenderThread 侧的贵操作

主线程录得快、RenderThread 执行慢的典型（选型细节见 draw-performance.md，这里只给"为什么贵"）：

- `Canvas.drawPath()`：大 Path 先在 CPU 算好再上传 GPU，逐帧改 Path 就无法缓存。拆成 `drawRect/Circle/Oval/RoundRect/drawLines` 更划算，哪怕 draw 调用次数变多
- Bitmap 首次上屏要上传成纹理（trace 里的 `Texture upload(id) w x h`），几毫秒级。除了按目标尺寸解码，还可以在解码或绑定时调 `Bitmap.prepareToDraw()`（Android 7.0+）提前上传，避开渲染那一帧

## 诊断工具对应表

| 想知道 | 用 |
|---|---|
| 这个页面到底有没有掉帧、掉多少 | `adb shell dumpsys gfxinfo <包名>` |
| 每帧卡在哪个阶段（input/animation/layout/draw/GPU） | 开发者选项 → Profile GPU Rendering；或 Perfetto FrameTimeline |
| 慢帧的具体调用栈 | Perfetto / Systrace（`-a <包名>` 才有 `RecyclerView` 等库内的 trace 段） |
| 主线程被 binder 卡住 | `adb shell am trace-ipc` |
| 线上采集帧耗时 | `FrameMetricsAggregator`，或 `Window.OnFrameMetricsAvailableListener` |

排查顺序：先用 `gfxinfo` 确认是不是真掉帧 → Perfetto 看掉在哪个阶段 → 阶段落在 Layout/Draw 就查布局与 `onDraw`，落在主线程睡眠就查 binder 和锁。

## 症状 → 排查

| 症状 | 优先查 |
|---|---|
| 改了自定义 View 的数据但界面不变 | 漏 `invalidate()`；跨线程改状态漏 `postInvalidate()` |
| 动画偶尔卡一下 | 是否在动布局属性；每帧是否触发 `requestLayout`；主线程是否有 IO/binder |
| 整个滑动都发涩但 `onDraw` 很轻 | 布局层级 + `RelativeLayout`/`weight` 的多次测量；`onBindViewHolder` 耗时 |
| 只有第一次进页面很卡 | 首帧 inflate + 首次测绘，属正常；超 700ms 才算问题，查 `onCreate` 同步初始化 |
| Systrace 里主线程大段灰色 | binder IPC、等锁、GC，不是渲染问题 |
| GPU 段特别长 | 过度绘制、大 Path、`clipPath`、大 Bitmap 上传 |
| 高刷设备上更明显 | 预算从 16ms 变 8ms，原来"刚好够"的逻辑现在超支 |
