# 依赖管理

## Version catalog

版本统一声明在 `gradle/libs.versions.toml`，模块里只引用别名：

```toml
[versions]
agp = "9.4.0"
kotlin = "2.2.10"
retrofit = "2.11.0"

[libraries]
retrofit = { module = "com.squareup.retrofit2:retrofit", version.ref = "retrofit" }
retrofit-gson = { module = "com.squareup.retrofit2:converter-gson", version.ref = "retrofit" }
okhttp-bom = { module = "com.squareup.okhttp3:okhttp-bom", version = "4.12.0" }

[bundles]
retrofit = ["retrofit", "retrofit-gson"]

[plugins]
android-application = { id = "com.android.application", version.ref = "agp" }
```

```kotlin
dependencies {
    implementation(libs.retrofit)
    implementation(libs.bundles.retrofit)      // 一组一起引
    implementation(platform(libs.okhttp.bom))  // BOM 用 platform() 包一层
}
```

三条约定：

- 别名里的 `-` 在代码里是 `.`（`retrofit-gson` → `libs.retrofit.gson`）
- 同一个库的多个 artifact 共用一个 `version.ref`，避免升级时漏掉一个导致版本错配
- **不要在模块里写死版本号**，也不要 catalog 和模块各写一份——两处不一致时排查成本极高

## 依赖配置怎么选

| 配置 | 语义 | 什么时候用 |
|---|---|---|
| `implementation` | 只自己用，不传染给下游 | **默认选它** |
| `api` | 传染给下游，下游能直接用这个库的类型 | 仅当你的公开 API 签名里出现了该库的类型 |
| `compileOnly` | 只编译期需要，不打进包 | 注解、`@Provided` 类型的 SDK |
| `runtimeOnly` | 只运行期需要 | 日志实现、驱动 |
| `ksp` / `kapt` | 注解处理器 | 见下文 |
| `testImplementation` / `androidTestImplementation` | 只测试用 | 测试库 |

滥用 `api` 的代价是增量编译失效：`api` 依赖变了，所有下游模块都要重编。判据很简单——**下游模块的代码里是否需要 import 这个库？** 不需要就用 `implementation`。

## KSP 与 kapt

kapt 处于**维护模式**。它的工作方式是从 Kotlin 文件生成 Java 桩再交给 Java 注解处理器，生成桩很贵，对构建速度影响很大。KSP 直接分析 Kotlin 代码，官方给的数据是快至多 2 倍。

迁移可以逐模块、逐库进行，kapt 和 KSP 能在同一项目共存。但有个关键点：**只要模块里还剩一个 kapt 处理器，这个模块就还得生成桩**——性能收益要等该模块的 kapt 彻底清零才拿得到。所以迁移要按模块收口，不要每个模块都留一个。

```kotlin
plugins {
    alias(libs.plugins.ksp)
}

dependencies {
    ksp(libs.room.compiler)       // 原来是 kapt(libs.room.compiler)
}
```

新加处理器之前先查它有没有 KSP 版本，别再往 kapt 上堆。

AGP 9 起，KSP 版本会被自动对齐到与内置 KGP 匹配的版本，不用也不该手动锁一个更低的。

## 版本冲突与仲裁

Gradle 默认取**最高版本**，多数时候这是对的。需要干预的情况：

**统一一族库的版本** —— 用 BOM，别逐个写版本：

```kotlin
implementation(platform(libs.okhttp.bom))
implementation("com.squareup.okhttp3:okhttp")   // 版本由 BOM 决定
```

**强制某个版本** —— 用 constraints，它比 `resolutionStrategy.force` 温和，会参与冲突解析而不是硬盖：

```kotlin
dependencies {
    constraints {
        implementation("com.squareup.okio:okio:3.9.0") {
            because("3.8 以下有已知的 GC 抖动问题")
        }
    }
}
```

写 `because` 不是形式主义——半年后没人记得为什么锁这个版本，没写原因的约束只会被人删掉再踩一次。

**排掉传递依赖** —— 精确排，不要一把梭：

```kotlin
implementation(libs.some.sdk) {
    exclude(group = "com.google.code.gson")   // 换成项目统一的 gson 版本
}
```

**重复类（Duplicate class）** —— 通常是同一个库换了坐标（`support` → `androidx`、`jcenter` 时代的旧坐标），或两个 SDK 各自内嵌了同一个库。先用依赖树定位来源，再决定排哪一边：

```bash
./gradlew :app:dependencies --configuration releaseRuntimeClasspath
./gradlew :app:dependencyInsight --configuration releaseRuntimeClasspath --dependency okio
```

`dependencyInsight` 会直接告诉你某个版本是**谁**要求的、为什么赢了，比人肉翻依赖树快得多。

## 症状 → 排查

| 症状 | 优先查 |
|---|---|
| `Duplicate class ... found in modules` | 同一库两个坐标或被内嵌两份，用 `dependencies` 定位后 `exclude` |
| `NoSuchMethodError` / `NoClassDefFoundError` 只在 release 出现 | 版本仲裁选了不兼容的版本，用 `dependencyInsight` 看谁拉高的；也可能是混淆问题 |
| 改一个模块导致全项目重编 | `api` 用多了，改回 `implementation` |
| 升级某个库后另一个库崩 | 传递依赖被拉高，用 constraints 锁并写清 `because` |
| 构建慢且大量 `kapt` 任务 | 迁 KSP，注意一个模块要清零才有收益 |
| catalog 里改了版本但没生效 | 模块里写死了版本号覆盖了别名 |
| 同一库在不同模块版本不一致 | 缺 BOM 或缺 `version.ref` 统一 |
