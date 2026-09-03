---
name: android-gradle-wiki
description: Android Gradle 构建知识库，覆盖 AGP/Gradle/JDK 版本兼容矩阵、AGP 8 与 9 的破坏性变更、version catalog 与依赖仲裁、KSP 与 kapt、构建变体与签名、R8 缩减与 keep 规则、配置缓存与构建性能。当需要升级 AGP 或 Gradle、改 build 脚本、加或排依赖、处理依赖冲突与重复类、配置混淆规则、排查混淆后崩溃、加构建变体、优化构建速度时使用。
---

# Android Gradle Wiki

查询型知识库。只在**需要确认构建配置或版本行为**时读对应 reference，一次读一个，不要整包拉进上下文。

这个域的反馈周期最长——构建配置写错往往到打包、混淆甚至线上才暴露。**改 build 脚本前先确认版本，不要凭记忆写 DSL**：AGP 8 和 9 各改了一批默认值和 API，凭旧记忆写出来的配置在新版本上要么报错、要么静默失效。

## 版本兼容（AGP 9.4，核实于 2026-09）

| 项 | 要求 |
|---|---|
| 支持的最高 API 级别 | 37 |
| Gradle | 最低且默认 9.6.0 |
| JDK | 最低且默认 17 |
| SDK Build Tools | 36.0.0 |

版本关系是**硬约束链**：AGP 决定 Gradle 下限和 JDK 下限，compileSdk 上限又受 AGP 限制。升级必须整条链一起看，单独升一个必然失败。

## 路由

| 问题 | 读 |
|---|---|
| 升 AGP / Gradle / JDK、升级后报错或 DSL 失效、AGP 8 与 9 改了什么、AGP 10 要准备什么 | [references/versions-upgrade.md](references/versions-upgrade.md) |
| 加依赖、version catalog 怎么写、`implementation` 还是 `api`、版本冲突、重复类、`kapt` 迁 `KSP` | [references/dependencies.md](references/dependencies.md) |
| 加 buildType 或 flavor、变体维度、按变体给不同配置、签名与密钥、动态功能模块 | [references/variants.md](references/variants.md) |
| 混淆后崩溃、`keep` 规则怎么写、R8 完整模式、缺类构建失败、资源被误删、还原堆栈 | [references/r8-shrinking.md](references/r8-shrinking.md) |
| 构建慢、配置缓存开不起来、增量编译失效、内存溢出、CI 上比本地慢 | [references/build-performance.md](references/build-performance.md) |

## 硬规则速查

- **改 build 脚本前先看当前 AGP 版本**（`gradle/libs.versions.toml` 或根 `build.gradle.kts`），再决定写法；AGP 8 和 9 的默认值不同
- **依赖版本统一在 `gradle/libs.versions.toml`**，不要在模块里写死版本号，也不要在两处各写一份
- **不要用 `implementation` 之外的配置除非有理由**：`api` 会把依赖传染给下游、拖慢增量编译，只在下游确实要用到该依赖的类型时才用
- **AGP 8.0+ `BuildConfig` 默认不生成**，要用得显式开 `buildFeatures { buildConfig = true }`
- **AGP 8.0+ 命名空间必须写在模块 build 文件的 `namespace`**，manifest 里的 `package` 属性已经不是配置位置
- **AGP 8.0+ R8 完整模式默认开启**，混淆更激进，反射、序列化、JNI 相关的类必须有 keep 规则
- **AGP 9.0 起 `-keep class A` 不再隐式保留默认构造函数**，需要构造函数就显式写 `-keep class A { <init>(); }`
- **AGP 9.0 内置 Kotlin 支持**，不再需要手动应用 `org.jetbrains.kotlin.android` 插件
- **签名密钥和密码不进版本库**，走 `local.properties` 或环境变量，`signingConfigs` 里只读取不硬编码
- **不在配置阶段做 IO 或取时间戳**（读文件、跑 git 命令、`System.currentTimeMillis()`）——会破坏配置缓存，也让每次构建的输入都不一样
- **新增 `kapt` 之前先查有没有 KSP 版本**，kapt 处于维护模式且要生成 Java 桩，同一模块只要还剩一个 kapt 处理器，桩就还得生成
- 升级一次只动一层，升完确认能构建再动下一层；`Tools > AGP Upgrade Assistant` 能自动改一部分

## 判断标准

改完自问：**清掉所有缓存、在 CI 的干净环境上还能构建出同样的产物吗？** 本地能过不算过——这个域的坑几乎都藏在缓存和环境差异里。

## 扩展

新增 reference 时同步更新路由表。AGP 出新版本后，先更新上面的兼容矩阵和 `versions-upgrade.md`，两处保持一致。
