# 组件、Intent 与代码加载

## 组件导出

`android:exported` 从 targetSdk 31 起，**凡是带 intent-filter 的 activity / service / receiver 必须显式声明**，不写编译就过不去。默认思路是"不确定就 `false`"。

## 运行时注册广播（targetSdk 34+）

必须显式指定导出行为，漏了直接崩：

```kotlin
ContextCompat.registerReceiver(
    context,
    receiver,
    IntentFilter(ACTION_MY_INTERNAL_EVENT),
    ContextCompat.RECEIVER_NOT_EXPORTED,   // 应用内事件一律用这个
)
```

只接收系统广播的接收器例外（可以不传）。但显式传 `RECEIVER_NOT_EXPORTED` 更安全，也不会出错。

应用内广播优先考虑换成 `LocalBroadcastManager` 的替代方案（`Flow`、`SharedFlow`、直接回调）——跨进程需求不存在时，用全局广播本来就是绕远路。

## 隐式 Intent（targetSdk 34+）

**隐式 intent 不能投递到非导出的组件**。应用内跳转如果还在用 action 匹配，会抛 `ActivityNotFoundException`。

```kotlin
// 应用内一律显式
startActivity(Intent(context, DetailActivity::class.java))
```

真需要对外暴露的，把组件设为 `exported="true"` 并明确 intent-filter；同时警惕别人也能拉起它，敏感入口加签名校验或权限保护。

## PendingIntent

targetSdk 31+ 必须指定可变性：`FLAG_IMMUTABLE`（默认选它）或 `FLAG_MUTABLE`（只在系统需要回填数据时，例如通知直接回复、`Slice`）。

## 后台启动 Activity

从 Android 10 起就受限，14、15、17 逐版收紧。核心原则：**没有用户交互就别想把自己弹到前台**。

- targetSdk 34、35 收紧了各类豁免路径
- targetSdk 37：`MODE_BACKGROUND_ACTIVITY_START_ALLOWED` 要迁到 `MODE_BACKGROUND_ACTIVITY_START_ALLOW_IF_VISIBLE`（只在调用方可见时允许），保护范围扩展到 `IntentSender`

需要提醒用户就发通知，让用户点；别试图绕过。

## 通知 trampoline（targetSdk 31+）

用户点通知后，**不能**从 service 或 broadcast receiver 里调 `startActivity()`。通知的 `PendingIntent` 要直接指向目标 Activity，需要预处理的话在 Activity 内部做。

## 更安全的 Intent 匹配

分阶段推进的计划，目前还没强制：

- Android 15：发送侧加了 intent 的 `StrictMode` 检测
- Android 16（targetSdk 36）：接收侧可以**选择启用**严格匹配，清单里加 `android:intentMatchingFlags="enforceIntentFilter"`。启用后，显式 intent 必须匹配目标组件的 intent-filter，且无 action 的 intent 不匹配任何 filter
- 官方说明未来会变成默认行为

被拦截的 intent 会打日志，tag 是 `PackageManager`，消息含 `Intent does not match component's intent filter:` 或 `Access blocked:`。

## 动态代码加载

- targetSdk 34+：动态加载的 DEX / JAR / APK **必须在写入完成后、打开之前设为只读**，否则拒绝加载
- targetSdk 37+：同样的要求扩展到原生库，`System.load()` 加载的 so 不是只读就抛 `UnsatisfiedLinkError`

热修复、插件化、动态下发引擎全都在这条线上。能不动态加载就不要动态加载——代码注入和篡改风险是实打实的。

## 反射与私有 API（targetSdk 37+）

- 反射修改 `static final` 字段抛 `IllegalAccessException`，走 JNI（`SetStaticLongField()` 之类）直接崩溃
- `MessageQueue` 换成无锁实现，反射它私有字段和方法的库会挂

受影响最多的是卡顿监控、消息队列拦截、Hook 框架这类基础库。升级前先盘一遍依赖里有没有这类实现。

## 症状 → 排查

| 症状 | 优先查 |
|---|---|
| `registerReceiver` 处崩溃 | targetSdk 34 要求显式导出标志 |
| 应用内跳转 `ActivityNotFoundException` | targetSdk 34 隐式 intent 不能启动非导出组件，改显式 |
| 通知点了没反应 | trampoline 限制：不能从 service/receiver 里 `startActivity` |
| `PendingIntent` 创建时崩 | 没指定 `FLAG_IMMUTABLE` / `FLAG_MUTABLE` |
| intent 被静默丢弃 | 查 `PackageManager` 日志里的 `Access blocked:` |
| 从后台弹不出界面 | 后台启动 Activity 限制，改用通知 |
| 热修复/插件在新系统失效 | 动态加载的只读要求（34 DEX / 37 so） |
| 监控类库在 Android 17 上崩 | 反射 `static final` 或 `MessageQueue` 私有成员 |
