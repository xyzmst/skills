# 启动模式与任务返回栈

## 四种启动模式

| 模式 | 行为 |
|---|---|
| `standard` | 默认。每次都新建实例，同一任务可以有多个实例，不同任务也可以各有实例 |
| `singleTop` | **只有实例正好在栈顶时**复用，走 `onNewIntent()`；不在栈顶照样新建 |
| `singleTask` | 在任务根位置创建，或复用同亲和性任务里已有的实例；复用时走 `onNewIntent()`，并**销毁其上所有 Activity** |
| `singleInstance` | 同 `singleTask`，且该 Activity 永远是其任务中唯一成员；由它启动的 Activity 都进别的任务 |

还有 `singleInstancePerTask`：只能作为任务根 Activity，配合 `FLAG_ACTIVITY_MULTIPLE_TASK` 或 `FLAG_ACTIVITY_NEW_DOCUMENT` 时可以在多个任务里各有一个实例。

### singleTop 的关键细节

栈是 `A-B-C-D`（D 在顶）：

- 再来一个 D 的 intent，D 是 `standard` → 栈变 `A-B-C-D-D`
- 再来一个 D 的 intent，D 是 `singleTop` → 现有 D 收到 `onNewIntent()`，栈仍是 `A-B-C-D`
- 来一个 **B** 的 intent，即使 B 是 `singleTop` → 仍然新建，栈变 `A-B-C-D-B`（因为 B 不在栈顶）

"设了 `singleTop` 还是出现了两个实例"基本都是这个原因。

### singleTask 会清栈

栈是 `A-B-C`，A 是 `singleTask`，此时来一个 A 的 intent：A 的现有实例收到 `onNewIntent()`，**B 和 C 被销毁**，栈变成只剩 A。

这个"清掉上层"的副作用经常是意料之外的——用它做首页时，从任何深层页面跳回首页会把中间页面全部销毁。

另外 `singleTask` 的 Activity 在**别的任务**里已存在时，整个那个任务会被移到前台，连带它自己的返回栈。

## 启动模式还是 Intent flag

**优先用 flag。** 启动模式写在清单里，是该 Activity 的全局行为，所有入口都受影响；flag 只作用于单次调用。

对应关系：

| flag | 等价于 |
|---|---|
| `FLAG_ACTIVITY_SINGLE_TOP` | `singleTop` |
| `FLAG_ACTIVITY_NEW_TASK` | 近似 `singleTask` |
| `FLAG_ACTIVITY_CLEAR_TOP` | 无对应模式——目标已在当前任务中时，销毁其上所有 Activity，intent 交给它的 `onNewIntent()` |

常见组合 `FLAG_ACTIVITY_CLEAR_TOP or FLAG_ACTIVITY_SINGLE_TOP`：回到已有的目标页并清掉上层，且不重建它。这是"点通知回到某页"的标准做法，比给该页设 `singleTask` 副作用小得多。

## onNewIntent 必须处理

复用实例时不走 `onCreate`，intent 从 `onNewIntent()` 来。只在 `onCreate` 里解析 intent 参数，会导致复用时**参数还是上一次的**：

```kotlin
override fun onCreate(savedInstanceState: Bundle?) {
    super.onCreate(savedInstanceState)
    handleIntent(intent)
}

override fun onNewIntent(intent: Intent) {
    super.onNewIntent(intent)
    setIntent(intent)        // 不调的话后续 getIntent() 拿到的还是旧的
    handleIntent(intent)
}
```

`setIntent(intent)` 容易漏。漏了之后当场看不出问题，等到别处调 `getIntent()` 时拿到过期数据。

还有一条交互差异：新建实例时用户可以按返回回到上一个 Activity；但**复用实例处理新 intent 时，用户无法通过返回回到这个实例在收到新 intent 之前的状态**——那个状态已经被覆盖了。需要可回退就不要复用。

## 单 Activity 架构

一个 Activity 承载所有页面，页面切换走 Navigation 的 Fragment 目的地。好处是不用再和启动模式、任务亲和性搏斗，返回栈由 `FragmentManager` 和 `NavController` 管理。

这种架构下启动模式只对唯一那个 Activity 有意义，外部入口（通知、深链、分享）统一由它接收再分发到目的地。深链去重要靠 `launchSingleTop`，见 `android-architecture-wiki` 的 `events.md`。

## setResult 的时机

```kotlin
setResult(RESULT_OK, Intent().putExtra(KEY_ID, id))
finish()
```

`setResult()` 必须在 `finish()` **之前**调用。用户按返回键退出时不会经过你的代码，所以默认结果是 `RESULT_CANCELED`——调用方必须处理这种情况，不能假设一定拿到 `RESULT_OK`。

## 症状 → 排查

| 症状 | 优先查 |
|---|---|
| 设了 `singleTop` 还是出现多个实例 | 目标不在栈顶时 `singleTop` 不生效，改用 `CLEAR_TOP` 组合 |
| 跳回首页后中间页面全没了 | `singleTask` 会销毁其上所有 Activity |
| 复用实例后参数是上一次的 | 只在 `onCreate` 解析了 intent，要在 `onNewIntent` 处理 |
| `getIntent()` 拿到过期数据 | `onNewIntent` 里漏了 `setIntent(intent)` |
| 从通知点进来返回栈很奇怪 | 检查 flag 组合，通常应为 `CLEAR_TOP or SINGLE_TOP` |
| 启动某页时整个别的任务被带到前台 | 目标是 `singleTask`/`singleInstance` 且在其他任务中已存在 |
| 调用方收到 `RESULT_CANCELED` | 用户按返回退出，或 `setResult` 写在了 `finish()` 之后 |
