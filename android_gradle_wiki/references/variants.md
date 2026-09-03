# 构建变体与签名

## buildType 与 flavor 的分工

- **buildType** 管"怎么构建"：调试还是发布、要不要混淆、要不要可调试
- **flavor** 管"构建哪个产品"：免费版/付费版、不同渠道、不同环境

变体 = buildType × 所有 flavor 维度的笛卡尔积。维度一多变体数量爆炸（3 个维度各 3 个值就是 27 × buildType），加维度前先算一下。

```kotlin
android {
    flavorDimensions += listOf("tier", "env")

    productFlavors {
        create("free")    { dimension = "tier" }
        create("paid")    { dimension = "tier" }
        create("staging") { dimension = "env" }
        create("prod")    { dimension = "env" }
    }
}
```

**每个 flavor 必须归属一个维度**，漏了会直接构建失败。维度的声明顺序决定优先级：靠前的维度覆盖靠后的。

## 按变体给不同配置

优先用**源集目录**而不是在脚本里写 if：

```
src/main/            所有变体共享
src/free/            free flavor 专属
src/prod/            prod flavor 专属
src/freeProd/        组合专属
src/debug/           debug buildType 专属
```

资源和 manifest 会按源集合并（专属覆盖 `main`），代码文件则是**同名类不能在 `main` 和变体源集里同时存在**——变体源集里放的是 `main` 里没有的实现，不是覆盖。

需要按变体给常量时用 `buildConfigField`（记得 AGP 8.0+ 要先开 `buildConfig = true`）：

```kotlin
android {
    buildFeatures { buildConfig = true }

    buildTypes {
        release {
            buildConfigField("String", "API_BASE", "\"https://api.example.com\"")
        }
        debug {
            buildConfigField("String", "API_BASE", "\"https://staging.example.com\"")
        }
    }
}
```

注意字符串值要带转义引号——少写一层引号会生成不能编译的常量。

## 签名与密钥

**密钥库口令绝不进版本库。** 从 `local.properties`（已 gitignore）或环境变量读：

```kotlin
val keystoreProps = Properties().apply {
    val f = rootProject.file("local.properties")
    if (f.exists()) f.inputStream().use { load(it) }
}

android {
    signingConfigs {
        create("release") {
            storeFile = keystoreProps["storeFile"]?.let { file(it.toString()) }
            storePassword = keystoreProps["storePassword"] as String?
            keyPassword = keystoreProps["keyPassword"] as String?
            keyAlias = keystoreProps["keyAlias"] as String?
        }
    }
    buildTypes {
        release {
            signingConfig = signingConfigs.getByName("release")
        }
    }
}
```

两个容易出事的点：CI 上文件不存在时要能优雅退化（上面用 `if (f.exists())`，否则本地能构建、CI 直接崩）；不要把 release 签名配给 debug 变体，否则调试包和线上包同签名，测试环境的问题会污染正式数据。

## 变体感知依赖

模块间依赖会自动按变体匹配：app 的 `freeDebug` 会去找 library 的 `freeDebug`。库模块没有对应变体时构建失败，两种解法——给库补上同名维度，或用 `matchingFallbacks` 指定回退：

```kotlin
productFlavors {
    create("staging") {
        dimension = "env"
        matchingFallbacks += listOf("debug", "release")
    }
}
```

**动态功能模块要求更严**：AGP 9.4 起会检查 app 模块和动态功能模块的变体维度是否严格 1:1，缺失、多余、不匹配都报警告；`android.enforceDynamicFeatureVariantMatching=true` 可以提前把警告升级为错误，AGP 10 起默认强制、直接构建失败。

## 少建变体的理由

每个变体都要单独编译、混淆、打包，变体数量直接乘构建时间和 CI 时长。能用运行时配置（配置中心、环境切换页）解决的，不要用变体解决——尤其是"给测试同学一个能切环境的包"这类需求，一个 debug 变体加切换入口比十个渠道变体划算得多。

## 症状 → 排查

| 症状 | 优先查 |
|---|---|
| `flavor must have a dimension` | 有 flavor 没归维度 |
| 模块依赖报找不到匹配变体 | 库模块缺同名变体，补维度或加 `matchingFallbacks` |
| `buildConfigField` 生成的代码编译不过 | 字符串值少了转义引号 |
| `BuildConfig` 类不存在 | AGP 8.0+ 需显式 `buildConfig = true` |
| 变体源集里的类和 main 冲突 | 同名类不能两处都有，变体源集只放 main 里没有的 |
| CI 上签名失败、本地正常 | 密钥文件或环境变量在 CI 不存在，加存在性判断 |
| 构建时间随需求线性变长 | 变体数量爆炸，考虑用运行时配置替代 |
| 动态功能模块告警维度不匹配 | AGP 9.4 的 1:1 检查，AGP 10 会致命 |
