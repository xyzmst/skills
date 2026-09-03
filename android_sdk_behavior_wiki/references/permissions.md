# 权限收紧

## 三条纪律

- **声明 ≠ 拥有**：每次用之前检查，用户可以随时在设置里撤销；长期不用的应用会被系统休眠，运行时权限和缓存一并重置
- **能不申请就不申请**：照片选择器、`ACTION_OPEN_DOCUMENT`、系统设备选择器这类系统提供的选择器不需要权限，用户拒绝率是真实成本
- **被拒之后要能降级**：拒绝不是异常路径而是常规路径，功能要有不依赖该权限的可用形态

## 通知

`POST_NOTIFICATIONS`（targetSdk 33+，运行时权限）。没授权的后果不只是普通通知发不出去——**前台服务的通知也不显示**，服务本身照常运行，但用户看不到，容易被误判为"服务没起来"。

`USE_FULL_SCREEN_INTENT`（targetSdk 34+）：全屏 intent 通知只有提供通话和闹钟功能的应用才获准，其他应用 Play 会撤销默认授予。做倒计时、提醒类功能不要依赖它。

## 媒体与存储

| targetSdk | 变化 |
|---|---|
| 33+ | `READ_EXTERNAL_STORAGE` 对媒体失效，拆成 `READ_MEDIA_IMAGES` / `READ_MEDIA_VIDEO` / `READ_MEDIA_AUDIO`。同时请求 images 和 video 只弹一个对话框 |
| 34+ | 用户可以只授权**部分照片**（`READ_MEDIA_VISUAL_USER_SELECTED`），代码必须能处理"只拿到几张" |
| 36+ | 照片选择器里本应用拥有的照片会被预选，用户取消勾选即撤回访问 |

细节和取舍看 storage-media.md。

## 位置

- 请求 `ACCESS_FINE_LOCATION` 时**必须同时请求** `ACCESS_COARSE_LOCATION`（targetSdk 31+），用户可以只给大致位置
- 后台位置 `ACCESS_BACKGROUND_LOCATION` 必须单独、在前台位置已授予之后再请求，不能和前台位置放同一次请求里

## 附近设备

- 蓝牙（targetSdk 31+）：`BLUETOOTH` / `BLUETOOTH_ADMIN` 换成 `BLUETOOTH_SCAN` / `BLUETOOTH_ADVERTISE` / `BLUETOOTH_CONNECT`。换完之后蓝牙操作**不再需要位置权限**——如果确实不用蓝牙推断位置，给扫描权限加 `android:usesPermissionFlags="neverForLocation"`，能省掉位置权限申请
- `BluetoothAdapter` 的调用在 targetSdk 34+ 强制要求 `BLUETOOTH_CONNECT`
- Wi-Fi API（targetSdk 33+）需要 `NEARBY_WIFI_DEVICES`

## 精确闹钟

`SCHEDULE_EXACT_ALARM` 从 Android 12 引入，**在 Android 14+ 设备上对新安装、targetSdk ≥ 33 的应用默认为拒绝**（不再预先授予）；设备从旧版本升级上来时，已经拿到的应用会保留。缺权限调用精确闹钟 API 抛 `SecurityException`。

标准流程：

```kotlin
val alarmManager = context.getSystemService(AlarmManager::class.java)
if (alarmManager.canScheduleExactAlarms()) {
    alarmManager.setExactAndAllowWhileIdle(...)
} else {
    // 引导用户去授权，别静默失败
    context.startActivity(Intent(Settings.ACTION_REQUEST_SCHEDULE_EXACT_ALARM))
}
```

用户授权后系统会发 `AlarmManager.ACTION_SCHEDULE_EXACT_ALARM_PERMISSION_STATE_CHANGED` 广播，监听它来恢复被跳过的调度。

两个省事的出口：日历、闹钟类应用可以声明 `USE_EXACT_ALARM`（安装时授予，但用途不符会被 Play 拒）；用 `OnAlarmListener` 形式的 `setExact` 不需要该权限。

先自问一句：**这个场景真的需要精确闹钟吗？** 多数"定时刷新""延迟上报"用 `WorkManager` 或非精确闹钟就够。

## 健康与身体传感器

targetSdk 36+：`BODY_SENSORS` 和 `BODY_SENSORS_BACKGROUND` 被 `android.permissions.health` 下的细粒度权限取代。

- 心率、血氧、体表温度 → `READ_HEART_RATE` 这类具体权限
- 后台读取 → `READ_HEALTH_DATA_IN_BACKGROUND`
- 影响面包括 `Sensor.TYPE_HEART_RATE`、Wear OS 健康服务、`FOREGROUND_SERVICE_TYPE_HEALTH`
- 手机应用**还必须声明一个展示隐私政策的 Activity**，否则权限会被撤销

## 本地网络

访问局域网设备（mDNS / SSDP 服务发现、投屏、智能家居）原本只要 `INTERNET` 就够。

- Android 16（targetSdk 36）：处于 opt-in 阶段，可用 `adb shell am compat enable RESTRICT_LOCAL_NETWORK <包名>` 提前验证，恢复访问靠 `NEARBY_WIFI_DEVICES`
- targetSdk 37+：**强制**，需要 `ACCESS_LOCAL_NETWORK` 运行时权限（归入 `NEARBY_DEVICES` 权限组，已授过同组权限的用户不会被二次打扰）

范围是所有网络 API：原生 socket、Cronet、OkHttp、WebView 一视同仁，`.local` 域名解析也算。DNS 服务器（53 端口）流量例外。被限制时表现为 socket 错误 `EPERM` / `ECONNABORTED`，不是抛权限异常——**很容易误判成网络故障**。

用系统提供的设备选择器可以完全绕过这个权限。

## 症状 → 排查

| 症状 | 优先查 |
|---|---|
| 前台服务在跑但用户看不到通知 | `POST_NOTIFICATIONS` 未授权（targetSdk 33+） |
| 相册读不到图 / 只读到几张 | 媒体权限已拆分（33+）、部分访问授权（34+） |
| 蓝牙扫描要位置权限，用户觉得莫名其妙 | 换新蓝牙权限并加 `neverForLocation` |
| 精确闹钟不触发、报 `SecurityException` | `SCHEDULE_EXACT_ALARM` 在 Android 14+ 默认拒绝，先 `canScheduleExactAlarms()` |
| 投屏/局域网设备发现失败，socket 报 `EPERM` | 本地网络权限（36 opt-in / 37 强制） |
| 心率读不到 | targetSdk 36 起 `BODY_SENSORS` 被健康细粒度权限取代 |
| 权限昨天还有今天没了 | 应用被休眠重置，或用户在设置里撤销；每次使用前检查 |
