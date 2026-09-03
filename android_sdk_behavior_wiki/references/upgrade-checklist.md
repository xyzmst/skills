# targetSdk 升级检查清单

按版本列**必须改**的项。升级是累加的：从 33 升到 36，下面 34、35、36 三节全部适用。

每节只列会让应用崩溃、功能失效或被系统拒绝的变更；细节和替代写法看对应主题分册。

## 升级的动作顺序

1. 先升 `compileSdk`，不动 `targetSdk`——只解决编译期问题（弃用 API、`SequencedCollection` 之类签名冲突）
2. 再逐版升 `targetSdk`，一次一版，每版跑完对应清单
3. 每版在**该版本的真机或模拟器**上过一遍核心用例，尤其是权限、后台任务、通知、返回键
4. 想提前验证某条变更，多数变更有兼容框架开关：`adb shell am compat enable <FLAG> <包名>`，不用真的升 targetSdk

## targetSdk 33（Android 13）

- **通知需要运行时权限** `POST_NOTIFICATIONS`。没授权时前台服务通知也不显示
- **媒体权限拆分**：`READ_EXTERNAL_STORAGE` 失效，改用 `READ_MEDIA_IMAGES` / `READ_MEDIA_VIDEO` / `READ_MEDIA_AUDIO`
- **Wi-Fi API 需要** `NEARBY_WIFI_DEVICES` 权限
- 后台读身体传感器需要 `BODY_SENSORS_BACKGROUND`

## targetSdk 34（Android 14）

- **前台服务必须声明类型**，且要有类型对应的权限。用例对不上任何类型的，迁 `WorkManager` 或用户发起的数据传输作业
- **运行时注册的广播接收器必须指定导出行为**：`registerReceiver(..., RECEIVER_EXPORTED)` 或 `RECEIVER_NOT_EXPORTED`。只接收系统广播的接收器例外。漏了会崩
- **隐式 intent 不能投递到非导出组件**，应用内跳转改显式 intent，否则 `ActivityNotFoundException`
- **全屏 intent 通知需要权限** `USE_FULL_SCREEN_INTENT`，新安装的应用只有来电、闹钟类才默认授予
- `BluetoothAdapter` 的调用强制要求 `BLUETOOTH_CONNECT`
- **动态代码加载**的 DEX/JAR/APK 必须先设为只读再加载
- 后台启动 Activity 的限制进一步收紧
- 照片/视频支持**部分访问**授权（`READ_MEDIA_VISUAL_USER_SELECTED`），代码要能处理"只拿到几张"
- 核心库升到 OpenJDK 17，注意正则、`Random`、`UUID` 等行为差异

## targetSdk 35（Android 15）

- **强制 edge-to-edge**：不处理 insets 内容就会被状态栏、导航栏、刘海遮住。可用 `windowOptOutEdgeToEdgeEnforcement` 临时停用（到 targetSdk 36 失效）
- **`Configuration` 不再排除系统栏**。凡是拿 `Configuration` 的宽高做布局计算的地方都要改，用 `WindowMetricsCalculator`、`WindowInsets` 或让 `ViewGroup` 自己算。资源目录限定符（`layout-h500dp`）不受影响
- **`dataSync` 和 `mediaProcessing` 前台服务 24 小时内累计上限 6 小时**，超时触发 `Service.onTimeout()`，几秒内不 `stopSelf()` 就抛 `RemoteServiceException`；额度用尽后再启动抛 `ForegroundServiceStartNotAllowedException`。用户把应用切到前台会重置计时
- **`BOOT_COMPLETED` 接收器不能启动**部分类型的前台服务，否则 `ForegroundServiceStartNotAllowedException`
- **`SYSTEM_ALERT_WINDOW` 的后台启动豁免收窄**：光有权限不够，必须已有一个**可见的** `TYPE_APPLICATION_OVERLAY` 窗口
- **不能再修改免打扰的全局状态**，`setInterruptionFilter` / `setNotificationPolicy` 改为生成隐式 `AutomaticZenRule`
- **禁用 TLS 1.0 / 1.1**
- `elegantTextHeight` 默认变 `true`，阿拉伯语、泰语、缅甸语等脚本行高变大，布局可能被撑开

## targetSdk 36（Android 16）

- **edge-to-edge 的停用开关失效**：`windowOptOutEdgeToEdgeEnforcement` 已弃用，在 Android 16 设备上不再起作用（跑在 Android 15 设备上仍有效）
- **预测性返回默认启用**：`onBackPressed()` 不再被调用，`KeyEvent.KEYCODE_BACK` 不再分发。没迁到 `OnBackInvokedCallback` / `OnBackPressedDispatcher` 的，先在清单 `<application>` 或 `<activity>` 上设 `android:enableOnBackInvokedCallback="false"` 保命
- **大屏忽略方向与尺寸限制**：sw ≥ 600dp 的显示屏上，`screenOrientation`、`resizableActivity`、`minAspectRatio`、`maxAspectRatio`、`setRequestedOrientation()` 全部失效，应用直接铺满窗口。例外：游戏（按 `android:appCategory`）、用户在设置里显式选择、小于 sw600dp 的屏幕。可用 `PROPERTY_COMPAT_ALLOW_RESTRICTED_RESIZABILITY` 临时停用，**targetSdk 37 起该开关失效**
  - 连带影响：设备可旋转 → Activity 重建次数变多 → 状态保存没做好就会丢
- **`BODY_SENSORS` 被细粒度健康权限取代**：改用 `android.permissions.health` 下的 `READ_HEART_RATE` 等，后台用 `READ_HEALTH_DATA_IN_BACKGROUND`。手机应用还必须声明一个展示隐私政策的 Activity，否则权限会被撤销
- `elegantTextHeight` 属性被忽略，设 `false` 也没用
- `scheduleAtFixedRate` 错过的周期任务，恢复后**只补执行 1 次**（以前是全部补齐）
- `MediaStore#getVersion()` 变成每个应用唯一，不要解析它的格式
- 用户在照片选择器里会看到**本应用拥有的照片被预选**，用户可以取消勾选从而撤回访问

## targetSdk 37（Android 17）

- **本地网络访问需要 `ACCESS_LOCAL_NETWORK` 运行时权限**（属 `NEARBY_DEVICES` 权限组）。mDNS/SSDP 发现、投屏、连智能家居设备都受影响；能用系统提供的设备选择器就不必申请
- **反射修改 `static final` 字段抛 `IllegalAccessException`**，走 JNI 改则直接崩溃
- **`MessageQueue` 换成无锁实现**，反射它私有字段/方法的库会挂（各类卡顿监控、消息拦截框架是重灾区）
- **`System.load()` 加载的 so 必须是只读的**，否则 `UnsatisfiedLinkError`
- **标准短信里的验证码延迟 3 小时才可读**，靠读短信自动填验证码的必须改用 SMS Retriever 或 SMS User Consent API
- 后台音频交互（播放、请求焦点、改音量）必须有前台服务，且该服务需具备仅在使用时授予的权限
- 证书透明度默认启用
- 大屏方向/尺寸限制的停用开关彻底失效
- 后台 Activity 启动：`MODE_BACKGROUND_ACTIVITY_START_ALLOWED` 要迁到 `MODE_BACKGROUND_ACTIVITY_START_ALLOW_IF_VISIBLE`

## 不看 targetSdk 也会生效的（按系统版本）

这些跟你的 targetSdk 无关，只要用户设备升级了就会打到：

| 系统版本 | 变更 |
|---|---|
| Android 15 | 原生库需支持 **16 KB 页面大小**；**targetSdk** 低于 24 的 APK 不再允许安装（测试可用 `adb install --bypass-low-target-sdk-block`） |
| Android 16 | `JobScheduler` 按待机分桶收紧配额；`JobInfo#setImportantWhileForeground` 完全弃用；有序广播优先级不再全局；`announceForAccessibility` 弃用；16 KB 兼容模式对话框 |

## 症状 → 排查

| 症状 | 优先查 |
|---|---|
| 升级后一启动就崩在 `registerReceiver` | targetSdk 34 的导出标志，看 components-intents.md |
| 前台服务起不来 / 跑一会被杀 | targetSdk 34 的类型必填、35 的 6 小时上限，看 background-work.md |
| 内容被状态栏或导航栏压住 | targetSdk 35 的 edge-to-edge，看 ui-compat.md |
| 返回键完全没反应 | targetSdk 36 的预测性返回，看 ui-compat.md |
| 锁竖屏在平板上失效 | targetSdk 36 的大屏忽略方向限制，看 ui-compat.md |
| 应用内跳转报 `ActivityNotFoundException` | targetSdk 34 的隐式 intent 限制，看 components-intents.md |
| 相册只读到几张图 | targetSdk 34 的部分媒体访问，看 storage-media.md |
| 卡顿监控/热修复类库在新系统上崩 | targetSdk 37 的 `MessageQueue` 与反射限制 |
| 只在某些设备上出问题 | 先确认是 targetSdk 门控还是系统版本门控，两者排查路径完全不同 |
