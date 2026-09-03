# 存储与媒体访问

## 先问要不要权限

访问文件的默认路径应该是**不申请权限**：

| 需求 | 无权限方案 |
|---|---|
| 让用户选图片/视频 | 照片选择器（`ACTION_PICK_IMAGES` / `PickVisualMedia`） |
| 让用户选任意文件 | `ACTION_OPEN_DOCUMENT` |
| 让用户选保存位置 | `ACTION_CREATE_DOCUMENT` |
| 应用自己的文件 | 应用专属目录，任何版本都不需要权限 |
| 往相册写自己拍的照片 | `MediaStore` 插入，不需要写权限 |

只有"要在**没有用户逐次选择**的前提下批量读取媒体库"才真正需要媒体权限，比如相册类、播放器类应用。

## 媒体权限的演进

| targetSdk | 变化 |
|---|---|
| 33+ | `READ_EXTERNAL_STORAGE` 对媒体不再生效，拆成 `READ_MEDIA_IMAGES` / `READ_MEDIA_VIDEO` / `READ_MEDIA_AUDIO`。同时请求 images 和 video 只会弹一个对话框 |
| 34+ | 用户可以选择**只授权部分照片**，对应 `READ_MEDIA_VISUAL_USER_SELECTED` |
| 36+ | 照片选择器中，本应用拥有的照片会被**预选**；用户取消勾选即撤回对这些照片的访问 |

部分访问是最容易写错的一条：用户点了"选择照片"而不是"全部允许"时，`READ_MEDIA_IMAGES` 是**被拒绝**的状态，但 `READ_MEDIA_VISUAL_USER_SELECTED` 被授予。只判断前者会得出"用户拒绝了"的错误结论。

三态判断：

```kotlin
val fullAccess = ContextCompat.checkSelfPermission(context, READ_MEDIA_IMAGES) == PERMISSION_GRANTED
val partialAccess = Build.VERSION.SDK_INT >= 34 &&
    ContextCompat.checkSelfPermission(context, READ_MEDIA_VISUAL_USER_SELECTED) == PERMISSION_GRANTED

when {
    fullAccess -> 查询全部媒体()
    partialAccess -> 查询已授权的那部分() // 还要给入口让用户追加选择
    else -> 引导授权或降级()
}
```

部分访问下应该提供"管理已选照片"的入口再次拉起选择器，而不是反复弹权限框——用户已经做过选择，再弹只会更烦。

## 分区存储

- 应用专属目录（`context.filesDir`、`getExternalFilesDir()`）随时可用，卸载时清理
- 共享媒体走 `MediaStore`，非媒体文件走 SAF（`ACTION_OPEN_DOCUMENT`）
- 直接拼 `/sdcard/xxx` 路径已经行不通，遗留代码里的绝对路径要改
- `MANAGE_EXTERNAL_STORAGE`（所有文件访问权限）会被 Play 严格审核，除非是文件管理器、备份工具这类核心功能，否则申请了大概率过不了审

## MediaStore

targetSdk 36+：`MediaStore#getVersion()` 变成**每个应用唯一**，去掉了可用于设备指纹的信息。不要解析它的格式，也不要拿它跨应用比对——只把它当成"变了就重新同步"的黑盒标记。

## 症状 → 排查

| 症状 | 优先查 |
|---|---|
| 读不到相册，权限判断显示被拒 | targetSdk 34 的部分访问，漏判 `READ_MEDIA_VISUAL_USER_SELECTED` |
| 在 Android 13 设备上读不到媒体 | 还在用 `READ_EXTERNAL_STORAGE`，改细分权限 |
| 用绝对路径读写失败 | 分区存储，改 `MediaStore` 或 SAF |
| 相册里明明有图但查不到 | 只授权了部分照片，只能查到那部分 |
| 反复弹权限框用户投诉 | 部分访问状态下应给"管理已选"入口而不是再次请求权限 |
| Play 审核卡在存储权限 | `MANAGE_EXTERNAL_STORAGE` 用途不符，换选择器方案 |
| 缓存的媒体版本判断失效 | targetSdk 36 起 `getVersion()` 每应用唯一，别解析格式 |
