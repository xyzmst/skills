# 构建性能

## 先测再优化

不要凭感觉优化。先看时间花在哪个阶段：

```bash
./gradlew assembleDebug --profile     # 生成 HTML 报告，含各阶段耗时
./gradlew assembleDebug --scan        # 更详细，需要接受上传条款
```

三个阶段的优化方向完全不同：

- **配置阶段慢**（Configuring projects 占比高）→ 开配置缓存、把 build 脚本里的逻辑挪进任务
- **执行阶段慢** → 看具体任务，通常是 dexing、kapt、资源处理
- **每次都全量重编** → 增量编译被破坏了，往下看

Android Studio 的 Build Analyzer 在 AGP 8.0+ 会按类别（资源 / Kotlin / dexing）分组排序，比逐个任务看更快定位。

## 配置缓存

让 Gradle 记住任务图，后续构建跳过整个配置阶段。收益在多模块项目上很明显。

```properties
# gradle.properties
org.gradle.configuration-cache=true
```

启用后第一次构建输出 `Calculating task graph as no configuration cache is available for tasks`，之后应该看到 `Reusing configuration cache`。**看不到第二句就说明缓存每次都失效**，等于没开。

失效的常见原因，也是写 build 脚本的硬约束：

- 在配置阶段读文件、跑外部命令（`git rev-parse`）、取时间戳（`System.currentTimeMillis()`）
- 在任务的执行逻辑里引用 `Project` 对象
- 第三方插件不兼容（用 Build Analyzer 检查兼容性）

正确做法是把这些逻辑包进任务，或用 `Provider` 延迟到执行阶段求值。顺带一提，取时间戳塞进 `BuildConfig` 还有第二个害处：每次构建的输入都不同，构建缓存也一起失效。

## 构建缓存与并行

```properties
org.gradle.caching=true      # 复用任务输出，跨构建甚至跨机器（配远程缓存）
org.gradle.parallel=true     # 模块间并行执行
```

并行的收益取决于模块图的形状：所有模块都依赖同一个巨型 `common` 模块时，并行度上不去。这种情况要先拆模块——把 `common` 按职责拆开，让互不依赖的模块能真正并行。

## R 类相关（AGP 8.0+ 已是默认）

- **非传递 R 类**：每个模块的 R 只含自己的资源，不再把依赖的资源引用一起拉进来。老项目用 `Refactor > Migrate to Non-transitive R Classes` 迁移
- **非常量 R 字段**：提高 Java 增量编译效率，也让资源缩减更精确

这两项都是默认行为，不需要配置，但**老项目升级时必须完成迁移**，否则跨模块引用 `R.xxx` 会编译不过。

## JVM 内存

```properties
org.gradle.jvmargs=-Xmx4g -XX:MaxMetaspaceSize=1g -XX:+HeapDumpOnOutOfMemoryError -XX:+UseParallelGC
```

三个要点：

- 改 `org.gradle.jvmargs` 时**必须显式设 `-XX:MaxMetaspaceSize`**，否则可能触发 Gradle 守护进程消失的问题（Gradle issue 19750）
- JDK 9+ 默认用 G1，官方建议试试并行 GC（`-XX:+UseParallelGC`）看是否更快——这个要实测，不同项目结论不同
- `-Xmx` 不是越大越好，超过物理内存会引发交换，比小堆更慢

## 其他

- **debug 变体关掉不必要的处理**：AGP 3.0+ 已默认对 debug 关闭 PNG 压缩
- **debug 不要开混淆**：`isMinifyEnabled = false`，混淆是发版才做的事
- **把代码模块化**：只重编改动的模块、输出可缓存、并行度更高。这是长期收益最大的一项，也最费功夫
- **kapt 迁 KSP**：kapt 要生成 Java 桩，是构建时间大户，见 dependencies.md

## 症状 → 排查

| 症状 | 优先查 |
|---|---|
| 每次构建都重跑配置阶段 | 配置缓存没开，或每次失效（脚本里有 IO、时间戳、外部命令） |
| 输出总是 `Calculating task graph...` | 配置缓存持续失效，逐项排查配置阶段的副作用 |
| 改一行代码全项目重编 | `api` 依赖用多了，或模块划分导致所有模块依赖同一个巨型模块 |
| CI 比本地慢很多 | CI 上构建缓存没配、每次干净环境，考虑远程构建缓存 |
| 构建时 OOM 或守护进程消失 | `org.gradle.jvmargs` 没设 `MaxMetaspaceSize` |
| 大量时间花在 kapt 任务 | 迁 KSP，且要把模块里的 kapt 清零才有收益 |
| 并行开了但没变快 | 模块图是星型的，先拆公共模块 |
| debug 构建也很慢 | 检查有没有误开混淆、资源压缩 |
