# 交互状态机：多角色、外部事件与倒计时

`ui-layer.md` 讲的是单向页面（加载 → 成功 / 失败）。这里讲另一类：**双方参与、有 IM/推送驱动、有倒计时**的交互（邀请-接受、连麦、小游戏、抢单）。判据：状态会被「对方的动作」或「时间到了」改变，而不只是被本方点击和接口响应改变——满足就读这篇。

例子取自 1v1 猜拳真心话：结构初版就对了，逻辑缺陷却有十来个，几乎全落在下面几条规则上。

## 先理逻辑，再建模

phase 从「角色 × 帧」表里来（每个角色从入口到收口每一帧看到什么、怎么进来、怎么退出），不从设计稿来——设计稿只画主干。表和三条场景演算（正常、失败或超时、乱序）的填法见 `requirement-frames` skill。表没闭合前不定 phase。

## 状态的形状

```kotlin
sealed class GamePhase { object Idle : GamePhase(); object Inviting : GamePhase(); /* ... */ }

data class GameRound(val inviteId: String, val result: String? = null, val question: Question? = null)

data class GameUiState(
    val phase: GamePhase = GamePhase.Idle,
    val round: GameRound? = null,        // 跨多个 phase 存活的本局数据
    val isPanelVisible: Boolean = false, // 与 phase 正交
    val remainingSeconds: Int = 0,
)
```

- **phase 不带参数**。`inviteId` 从邀请一直活到出题，放进 sealed 子类的话每次转移都要手动搬运，漏搬一次数据就丢了。数据放 `round`，phase 只做标记。
- **正交维度不进 phase**。「面板关了」不是一个阶段：关面板只改 `isPanelVisible`，倒计时和 IM 照常推进。把它做成 phase，就会冒出「关面板等于拒绝吗」这种本不存在的问题。
- `when (phase)` 必须穷举、不写 `else`，新增 phase 时编译器逼你处理每个渲染点。

## 按生命周期给状态分组（最重要）

**凡是影响下一次转移的值都是状态**，不管它进没进 `StateFlow`。倒计时截止时间、请求序号、早到消息的暂存，都是状态。它们最容易出错，因为不在 UiState 里，没人审。

判据一句：**一个值该跟着什么一起诞生、一起死，它就住在什么对象里。**

| 生命周期 | 例子 | 住在哪 |
|---|---|---|
| 会话级（整通电话） | entry 配置、气泡计时、局建立前早到的消息 | ViewModel 字段 |
| 局级（一局游戏） | 邀请/题目截止时间、换题序号、局内早到的消息 | 一个内部对象，新局整体替换 |
| 界面要看的 | phase、本局展示数据、剩余秒数 | `UiState` |

局级值散成 ViewModel 字段时，每个「新一局」入口都得手动重置一遍：

```kotlin
changeQuestionSeq++      // startInvite()、applyIncomingInvite()、resetToEntry() 三处各写一遍
questionDeadline = 0L
pendingQuestion = null
```

这是靠约定维持正确性：再加一个局级变量就要记得改三处。收进一个对象，结构上就漏不了：

```kotlin
private class RoundSession(val inviteId: String) {
    var inviteDeadline = 0L
    var questionDeadline = 0L
    var changeQuestionSeq = 0
    var pendingQuestion: ImBean? = null
}
private var session: RoundSession? = null   // 新局：session = RoundSession(id)
```

自检：ViewModel 里每个 `private var` 都要能答出属于哪一组；答不出，或者某个局级值在多处被手动归零，就是放错了。

## 谁写状态

- **ViewModel 决定下一个 phase，Repository 只返回服务端说了什么**（bean、`Result`、IM 事件流）。Repository 的返回类型里不许出现 phase 或 UiState 类型，可以直接 `grep` 检查。
- 所有 UiState 更新走一个写入函数（如 `setState(reason) { it.copy(...) }`），带原因打日志。状态从哪变的，看日志就知道。
- 用户说「逻辑放 Repository」或「VM 太重」时，按上面那条判据判断，不要照字面整块搬家。这次先把逻辑搬进 Repository，又被要求搬回来，就是没有判据导致的来回过冲。

## 计时

- 用截止时间（`SystemClock.elapsedRealtime()` + 时长），一个 1 秒 ticker 统一检查，不要每个倒计时各开一个 Job。
- **每个倒计时写清起点事件**：请求发起、响应到达、状态进入还是用户点击。这次的气泡时机前后有三种说法（字段注释写「通话开始后」、口头先说「接口回来」、最后定为「请求发起」），不钉死起点，就会实现成错的那个。
- **截止时间只在进入该阶段时写一次**。换题、刷新这类阶段内操作不重写它，否则一直点就能把倒计时无限续上。
- **一次性触发先消费再执行**：到点后先把截止时间清零，再调用动作。反过来的话，动作失败或提前返回时截止时间还是过期状态，ticker 会每秒重进一次，变成无限重试。
- 剩余秒数到 0 时不发「0s」，直接转到下一状态的文案。
- 每个等待态都要有出边（超时、对方事件或本方操作之一）；只能等对方消息的状态，要说清消息丢了怎么办。

## 外部事件（IM / 推送）

事件可能早到、迟到、重复，而且不一定和本地接口响应的顺序一致。四条规则：

1. **按 id 匹配本局**。不是本局的消息记日志后丢弃。
2. **早到的消息先暂存，等目标状态建立时再消费**。例子：结果动画还没播完，题目 IM 就到了，直接丢弃的话动画结束后就永远等不到题目。暂存要随它所属的生命周期一起清理（见上面的分组）。
3. **迟到的本地响应用序号丢弃**。发请求时 `seq = ++requestSeq`，响应回来时比对，不相等就丢。新局、换题、重新发起都要让序号失效。
4. **「哪些 phase 能被新事件顶掉」写成白名单并给理由**。判据是本方在当前 phase 还有没有主动出路：只能被动等对方的状态（例如等题目）必须能被对方的新邀请顶掉，否则消息一丢就只能挂断；本方正在操作的状态（例如正在出题）不能被抢。

## 验证：状态 × 事件矩阵

行是 phase，列是事件（用户操作、每种 IM、每个倒计时到点、接口成功或失败）。每格写下一状态和副作用；「忽略」和「不可达」也必须写理由。**空格就是漏洞。**状态图只画想到的转移，看起来永远完整；矩阵是逐格展开，没想到的格子会留白。这次反向填 108 格，当场挖出 5 个多轮自检都没抓到的缺陷。

编码前正向填一遍；实现后再把每格映射到具体方法，映射不上的格子要么是死代码，要么是漏处理。

## 症状 → 排查

| 症状 | 优先查 |
|---|---|
| 倒计时停在 0 不动 | 这一侧有没有写入截止时间；到点分支有没有真的转移 phase |
| 某个接口每秒被调一次 | 一次性触发没有先消费（截止时间没清零） |
| 点某个按钮倒计时被重置 | 截止时间的写入点不止一处 |
| 第二局出现上一局的残留 | 局级值散在 ViewModel 字段里靠手动重置，改成按局整体替换 |
| 某条 IM 偶发没反应 | 到达时 phase 不匹配被丢弃，缺暂存 |
| 一方永久卡在等待态 | 等待态没有出边，或不在「可被顶掉」的白名单里 |
| 同时操作时两端结果不一致 | 本地响应和对方 IM 的先后没定规则，迟到响应没用序号丢弃 |
| 状态在 VM 和 Repository 两处被改 | Repository 在决定 phase，把判断收回 ViewModel |
