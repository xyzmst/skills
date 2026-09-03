# 后台执行与前台服务

## 先选对工具

| 场景 | 用什么 |
|---|---|
| 用户可感知、必须立刻持续执行（导航、播放、通话、录音） | 前台服务 + 正确的服务类型 |
| 可延迟、要保证最终完成（同步、上传、清理） | `WorkManager` |
| 用户发起的大文件传输 | 用户发起的数据传输作业（user-initiated data transfer job） |
| 精确到某个时刻触发（闹钟、日程提醒） | `AlarmManager` 精确闹钟（要权限，见 permissions.md） |
| 其他 | 多半什么都不需要，等应用回到前台再做 |

选错的代价从 targetSdk 34 起是硬性的：**前台服务类型对不上用例，就不该用前台服务。**

## 前台服务类型（targetSdk 34+）

必须在清单里声明 `android:foregroundServiceType`，并持有该类型要求的权限，启动时传入对应类型。类型和用例不符会被系统拒绝或后续被 Play 拒审。

Android 14 新增了健康、远程消息等类型，另外保留了简短服务（`shortService`）、特殊用途和系统豁免类型。找不到匹配类型时的正解是迁移到 `WorkManager`，而不是随便挑一个类型糊弄。

## 6 小时上限（targetSdk 35+）

`dataSync` 和 `mediaProcessing` 两种类型，**24 小时内所有同类型服务累计最多运行 6 小时**：

- 到点系统调用 `Service.onTimeout(int, int)`，服务有几秒时间调 `stopSelf()`
- 不停就抛 `RemoteServiceException`，日志形如 `A foreground service of type dataSync did not stop within its timeout`
- 额度耗尽后再启动同类型服务抛 `ForegroundServiceStartNotAllowedException`
- 用户把应用切到前台会**重置**计时器

应对：长时间同步改用 `WorkManager` 或用户发起的数据传输作业；确实要用就实现 `onTimeout()` 优雅收尾并记录断点，下次续传。

提前验证：`adb shell am compat enable FGS_INTRODUCE_TIME_LIMITS <包名>`，配合 `adb shell device_config put activity_manager data_sync_fgs_timeout_duration <毫秒>` 缩短超时。

## 从后台启动前台服务

默认不允许（targetSdk 31+），只有少数豁免。两个逐版收紧的点：

**`BOOT_COMPLETED` 接收器（targetSdk 35+）** 不能启动这些类型的前台服务，否则 `ForegroundServiceStartNotAllowedException`：`dataSync`、`camera`、`mediaPlayback`、`phoneCall`、`mediaProjection`、`microphone`（`microphone` 从 Android 14 起就已限制）。

开机自启做同步的老代码基本都撞这条，改法是开机时只调度 `WorkManager` 任务，不直接起服务。

**`SYSTEM_ALERT_WINDOW` 豁免收窄（targetSdk 35+）**：光有权限不够，必须已经有一个**可见的** `TYPE_APPLICATION_OVERLAY` 窗口。用 `View.getWindowVisibility()` 确认，或重写 `View.onWindowVisibilityChanged()` 跟踪。顺序错了（先起服务再显示悬浮窗）就会抛异常。

## JobScheduler 与 WorkManager

- Android 16 起按**应用待机分桶**收紧常规作业和加急作业的运行时配额，处于顶层状态、与前台服务同时执行也要遵守配额
- `JobInfo#setImportantWhileForeground` 在 Android 16 完全弃用
- 新增"作业被废弃"的停止原因，频繁出现会被系统降频，应该读 stop reason 并据此减少无效调度
- targetSdk 34 起 `JobScheduler` 的回调有更严格的处理时限，`onStartJob`/`onStopJob` 里做耗时操作要挪到异步线程——`WorkManager` 已经帮你封装好了

查待机分桶：`adb shell am get-standby-bucket <包名>`，设置：`adb shell am set-standby-bucket <包名> <bucket>`。

## 定时任务的行为变化

targetSdk 36 起，`scheduleAtFixedRate` 因为进程不在有效生命周期而错过的执行，恢复后**只补执行 1 次**（以前会把错过的全部立即补齐）。依赖"补齐次数"做计数或对账的逻辑会算错。

兼容标志：`STPE_SKIP_MULTIPLE_MISSED_PERIODIC_TASKS`。

## 后台音频（targetSdk 37+）

后台状态下的音频播放、请求音频焦点、改音量都要求有前台服务在跑，且该前台服务需具备"仅在使用时授予"的权限；或者应用持有精确闹钟权限且操作的是 `USAGE_ALARM` 音频流。

## 症状 → 排查

| 症状 | 优先查 |
|---|---|
| `ForegroundServiceStartNotAllowedException` | 后台启动限制：是不是从 `BOOT_COMPLETED` 起的（35+）、悬浮窗是否可见（35+）、6 小时额度是否用尽（35+） |
| `RemoteServiceException: ... did not stop within its timeout` | `dataSync`/`mediaProcessing` 超 6 小时没自己停（35+） |
| 前台服务在 Android 14 设备上起不来 | 类型没声明或类型对应的权限没拿到（34+） |
| 开机自启的同步不执行了 | `BOOT_COMPLETED` 不能启动这些类型的 FGS，改成调度 `WorkManager`（35+） |
| 后台任务执行频率明显变低 | Android 16 的待机分桶配额，先看应用在哪个桶 |
| 周期任务的补偿次数对不上 | targetSdk 36 只补 1 次 |
| 后台播放突然静音/焦点请求失败 | targetSdk 37 的后台音频加固 |
| 精确闹钟不响 | 权限问题，看 permissions.md |
