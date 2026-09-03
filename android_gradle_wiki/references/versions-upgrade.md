# 版本兼容与升级

## 兼容矩阵（AGP 9.4，核实于 2026-09）

| 项 | 最低 | 默认 |
|---|---|---|
| Gradle | 9.6.0 | 9.6.0 |
| JDK | 17 | 17 |
| SDK Build Tools | 36.0.0 | 36.0.0 |
| 支持的最高 API 级别 | — | 37 |

历史下限，判断老项目能不能原地升的时候用：AGP 8.0 起要求 **JDK 17**（这是很多老项目卡住的第一道坎）。

## 升级顺序

一次只动一层，每层升完先确认能构建：

1. **JDK** —— 不满足 AGP 要求的话，后面全免谈
2. **Gradle** —— 改 `gradle/wrapper/gradle-wrapper.properties`，用 `./gradlew wrapper --gradle-version=X` 而不是手改后忘了同步校验和
3. **AGP** —— 改 version catalog 里的版本，跑一次完整构建，处理弃用警告
4. **KGP / KSP** —— AGP 9 起内置 Kotlin，多数情况不用自己声明
5. **compileSdk → targetSdk** —— 这属于另一个域，看 `android-sdk-behavior-wiki`

`Tools > AGP Upgrade Assistant` 能自动完成一部分改写，但它不改你自己写的 keep 规则和自定义插件代码。

## AGP 8.0 的破坏性变更

老项目从 7.x 升上来必然全部撞到：

- **必须在模块级 build 文件里声明 `namespace`**，不能再依赖 manifest 的 `package` 属性（`namespace` DSL 从 AGP 7.3 起可用）
- **`BuildConfig` 默认不再生成** —— 要用就显式开：

```kotlin
android {
    buildFeatures {
        buildConfig = true
    }
}
```

- **AIDL 和 RenderScript 默认关闭**，同样要显式开（这两个标志在 AGP 9.0 已移除，RenderScript 该考虑迁走了）
- **R8 完整模式默认开启**（`android.enableR8.fullMode`），优化更激进，对反射的假设更严格
- **缺少类会直接让 R8 构建失败**（以前只是警告），解决办法是补上缺失的库，或加 `-dontwarn` 规则
- **R 类默认生成非最终字段**，且默认使用**非传递 R 类**（每个模块的 R 只含自己的资源）。老代码里跨模块引用 `R.xxx` 的地方会编译不过，用 `Refactor > Migrate to Non-transitive R Classes` 迁移
- **需要 JDK 17**
- 默认使用新的资源缩减器实现
- 不再默认创建 `SoftwareComponent`，只为用发布 DSL 配置过的变体创建

## AGP 9.0 的破坏性变更

- **内置 Kotlin 支持并默认启用**：不用再应用 `org.jetbrains.kotlin.android` / `kotlin-android` 插件。AGP 9.0 对 KGP 有运行时依赖（2.2.10 起），版本低于它会被自动提升；KSP 同理会被对齐到匹配版本
- **`-keep class A` 不再隐式保留默认构造函数**。以前它等价于 `-keep class A { <init>(); }`，现在不是了——**反射 `newInstance()` 创建实例的地方会在运行时崩**，必须显式写出构造函数。这是升 9.0 最容易漏、且只在运行时暴露的一条
- **`getDefaultProguardFile()` 只支持 `proguard-android-optimize.txt`**，不再支持 `proguard-android.txt`（后者带 `-dontoptimize`，等于白白关掉优化）
- **默认 Java 源/目标版本从 8 提升到 11**
- **`targetSdk` 的默认值改为跟随 `compileSdk`**（以前跟随 `minSdk`）——没显式声明 `targetSdk` 的模块行为会变，一律显式写出来
- **keep 规则不再作用于编译器合成的 companion 方法**，与"keep 规则不适用于编译器合成成员"这条总原则对齐
- `minSdk < 24` 且用接口的 default/static/private 方法、并靠 keep 规则保留接口方法的用例**不再支持**，需要先脱糖成类文件
- 旧 DSL 在 `android` 块内被标记弃用；没启用 newDsl 的项目会看到弃用警告
- 新增 R8 选项 `-processkotlinnullchecks`，取值 `keep` / `remove_message` / `remove`，用来控制怎么处理 Kotlin 编译器插入的空检查
- 设备端测试默认改用 `androidx.test.runner.AndroidJUnitRunner`

**已移除的能力**（不是弃用，是没了）：

- 嵌入式 Wear OS 应用支持（`wearApp` 配置），Play 也不再支持
- 按屏幕密度拆分 APK（`DensitySplit`），改用 App Bundle
- `CommonExtension` 的类型参数化——写过自定义 Gradle 插件的要重构，块方法从 `CommonExtension` 移到 `ApplicationExtension` / `LibraryExtension` / `DynamicFeatureExtension` / `TestExtension`
- `Variant.minSdkVersion`（改用 `minSdk`）、`FeaturePlugin` / `FeatureExtension`、`LanguageSplitOptions`

## AGP 10 的预告（现在就该准备）

- **所有项目必须使用新 Variant API**。想逐步迁移，可以在 `gradle.properties` 里按模块临时停用：

```properties
android.newDsl.optOut=:example-lib1
```

- **动态功能模块与 app 模块的变体维度必须严格 1:1 对等**。AGP 9.4 已经在检查，默认只报警告；可以提前用 `android.enforceDynamicFeatureVariantMatching=true` 升级为构建错误，AGP 10 起默认强制、维度不匹配直接构建失败

## 症状 → 排查

| 症状 | 优先查 |
|---|---|
| 升级后报找不到 `namespace` / manifest package 冲突 | AGP 8.0 的 namespace 要求 |
| `BuildConfig` 找不到符号 | AGP 8.0 默认不生成，显式开 `buildConfig = true` |
| 混淆包运行时 `InstantiationException` / 反射创建实例失败 | AGP 9.0 的 keep 不再含默认构造函数，显式写 `{ <init>(); }` |
| R8 报缺少类导致构建失败 | AGP 8.0 起从警告变失败，补库或 `-dontwarn` |
| 跨模块引用 `R.xxx` 编译不过 | AGP 8.0 默认非传递 R 类，走迁移重构 |
| Gradle 报 JDK 版本过低 | AGP 8.0+ 要求 JDK 17 |
| 自定义 Gradle 插件在 AGP 9 上编译不过 | `CommonExtension` 参数化被移除，块方法要换到具体 Extension |
| 没改代码但 targetSdk 行为变了 | AGP 9.0 起 targetSdk 默认跟随 compileSdk，显式声明 |
| 动态功能模块构建告警提示维度不匹配 | AGP 9.4 的 1:1 变体对等检查，AGP 10 会变致命 |
| 优化似乎完全没生效、包大小没变 | 可能用了 `proguard-android.txt`（含 `-dontoptimize`） |
