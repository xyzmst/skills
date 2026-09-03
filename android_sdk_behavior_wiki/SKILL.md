---
name: android-sdk-behavior-wiki
description: Android targetSdk 升级与版本行为变更知识库，覆盖 API 33-37 的权限收紧、前台服务类型与超时、后台启动限制、隐式 intent 与组件导出、分区存储与媒体权限、edge-to-edge 与预测性返回、大屏自适应强制。当需要升 targetSdk、判断某个 API 在当前 targetSdk 下还能不能用、排查 ForegroundServiceStartNotAllowedException / SecurityException / ActivityNotFoundException / 权限被拒 / 升级后界面被系统栏遮挡 / 返回键失效时使用。
---

# Android SDK Behavior Wiki

查询型知识库。只在**需要确认某个版本的限制**时读对应 reference，一次读一个，不要整包拉进上下文。

这个域的唯一致命错误是**版本号记错**——把 Android 14 的限制说成 15、把 targetSdk 才生效的说成全量生效。拿不准就读 reference 核对，不要凭印象回答。

## 版本对照

| Android | API 级别 |
|---|---|
| 13 | 33 |
| 14 | 34 |
| 15 | 35 |
| 16 | 36 |
| 17 | 37 |

Google Play 要求（核实于 2026-09）：新应用和应用更新必须 targetSdk ≥ 36；Wear OS / Automotive ≥ 35；TV / XR ≥ 34。targetSdk ≤ 34 的应用，在系统版本高于其 targetSdk 的设备上对新用户不可用。

## 两类变更，先分清

- **仅影响 targetSdk ≥ N 的应用**：不升 targetSdk 就不生效，是升级时的改造清单
- **影响所有应用**（只要跑在该系统版本上）：不升 targetSdk 也会被打到，改不改由不得你

判断一条限制属于哪类，直接决定"现在要不要改"。reference 里每条都标了。

## 路由

| 问题 | 读 |
|---|---|
| 要升 targetSdk，这一版必须改什么、按什么顺序做 | [references/upgrade-checklist.md](references/upgrade-checklist.md) |
| 权限被拒、要申请哪个权限、旧权限被拆分或替换、通知/媒体/位置/附近设备/健康/本地网络 | [references/permissions.md](references/permissions.md) |
| 前台服务起不来、服务被超时杀掉、后台任务不执行、开机广播、闹钟、JobScheduler 配额 | [references/background-work.md](references/background-work.md) |
| `ActivityNotFoundException`、隐式 intent 失效、组件导出、动态注册广播崩溃、`PendingIntent`、后台启 Activity、动态加载代码 | [references/components-intents.md](references/components-intents.md) |
| 读写文件失败、访问相册、媒体权限只给了部分照片、照片选择器、`MediaStore` | [references/storage-media.md](references/storage-media.md) |
| 升级后界面被状态栏/导航栏遮挡、返回键回调不触发、大屏上强制横屏失效、字体行高变了 | [references/ui-compat.md](references/ui-compat.md) |

排查异常时按异常名找：`ForegroundServiceStartNotAllowedException` 和 `RemoteServiceException` 看 `background-work.md`，`ActivityNotFoundException` 和 `SecurityException`（导出/intent 相关）看 `components-intents.md`。

## 硬规则速查

- **升 targetSdk 是逐版累加的**：从 33 升到 36，34、35、36 三版的 targetSdk 变更全部同时生效，不能只看最新那版
- targetSdk 34+ 的**前台服务必须声明类型**（`android:foregroundServiceType` + 对应权限），类型对不上用例就别用前台服务，迁 `WorkManager` 或用户发起的数据传输作业
- targetSdk 34+ **运行时注册广播接收器必须显式传** `RECEIVER_EXPORTED` 或 `RECEIVER_NOT_EXPORTED`，只收系统广播的除外，漏了直接崩
- targetSdk 34+ **隐式 intent 不能启动非导出组件**，应用内组件一律用显式 intent
- targetSdk 35+ **默认 edge-to-edge**，必须自己处理 insets；targetSdk 36 起连临时停用开关都没了
- targetSdk 36+ **预测性返回默认开启**，`onBackPressed()` 不再被调用、`KEYCODE_BACK` 不再分发，没迁移就先在清单里关掉
- targetSdk 36+ 大屏（sw ≥ 600dp）**忽略** `screenOrientation`、`resizableActivity`、`minAspectRatio`/`maxAspectRatio` 和 `setRequestedOrientation()`，锁竖屏的假设会失效
- targetSdk 35+ `dataSync` / `mediaProcessing` 前台服务**24 小时内累计只能跑 6 小时**
- 声明了权限不等于拿到权限：运行时权限每次用前都要检查，用户可以随时撤销，长期不用的应用还会被休眠重置
- 新增权限先问"能不能不要"：能用系统选择器（照片选择器、设备选择器、`ACTION_OPEN_DOCUMENT`）就别申请权限，用户拒绝率是真实成本
- 临时停用开关（`windowOptOutEdgeToEdgeEnforcement`、`enableOnBackInvokedCallback=false`、`PROPERTY_COMPAT_ALLOW_RESTRICTED_RESIZABILITY`）都是**过渡手段**，官方逐版收回，只能用来赶发版，不能当长期方案

## 判断标准

改完自问：**这个行为在最低支持版本到最新版本之间，每一档都试过吗？** 这个域的坑几乎全是"在我的机器上是好的"。

## 扩展

新增 reference 时同步更新上面的路由表。新版本发布后，先更新 `upgrade-checklist.md` 增加一节，再把条目分发到对应主题分册，两处保持一致。
