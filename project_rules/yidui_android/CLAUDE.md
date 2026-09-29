# CLAUDE.md

伊对 Android 仓库的事实与硬门槛。只写本仓特有的东西；通用 Kotlin / Android 写法不在这里，流程规则见全局规则 `post-change-gpt-review`。

## 项目

- 社交 / 直播 App，带多个马甲包。主分支 `master`，马甲包分支 `vest`。
- 构建：`./gradlew assembleArm64Debug` / `assembleArm64Release`；单模块 `./gradlew :feature:live:live-base:build`，单测 `./gradlew :core:rtc:rtc:test`。需要 `env.gradle` 里的内部 Maven 凭据（`ldapUsername` / `ldapPassword`），不要输出。
- 版本：AGP 8.6.1、Kotlin 2.0.21、Gradle 8.7，以 `gradle/libs.versions.toml` 为准；Maven 仓库配置在 `settings.gradle`。
- 打包：测试包 https://devops.miliantech.com/admin/package/package_test/create ，正式包 https://devops.miliantech.com/admin/package/package/create 。

## 模块与分层

```
app/        # 壳、全局生命周期、Router 编排；最终页面常在 app/src/main/java/com/yidui/ui/<domain>/
feature/    # 业务（auth/home/live/moment/message/member/...）
data/       # 领域数据（live/message/pay/abtest/...）
core/       # 公共（uikit/rtc/notification/...）
dev-tools/  # 内部调试
```

- `feature:<domain>` 只依赖自己的 `data:<domain>`、core 和其他 feature 的公开 API；`data` 只依赖 core 和 SDK；`core` 不依赖 feature。
- 新 feature 目录：`di/`、`api/`、`repository/`、`viewmodel/`、`ui/` 或 `view/`、`bean/` 或 `model/`；`datasource/` 只在多数据源合并或本地缓存时加。
- 按业务词找模块、判断代码落点，用 `yidui-architecture` skill。

## 新代码与老代码

- 新代码：MVVM（`Activity/Fragment → ViewModel → Repository → Api`）、协程 + Flow、Koin。默认一个 UI `StateFlow`；一次性事件可以用 `SharedFlow`（本仓例外，只用于丢了无害的通知）。新代码不用 LiveData / RxJava。
- 老代码：MVP + LiveData / RxJava / 回调，改什么跟什么；除非整体重构，不往老模块里塞新架构。
- 跟随周边的是格式（缩进、空行、命名、成员顺序、日志格式），不是架构决策和缺陷：加不加类、放哪一层每次自己判断；抄隔壁实现前先确认它本身没问题（形同虚设的 flag、缺失的 try-catch、没日志的失败分支）。
- 成员顺序：companion / 常量 → 字段（public → private）→ 生命周期方法 → public → internal → protected → private 方法。

## 本仓基础设施

- **DI**：业务模块用 Koin，定义在 `di/<Module>.kt`，注册进 `AppDelegate.startKoin()`；App 壳和基础设施用 Hilt（`App.kt` 的 `@HiltAndroidApp`，基类容器 `@AndroidEntryPoint`）。
- **网络**：新接口返回 `UniDeferredCall<T>`；Repository 方法一律 `suspend`，`await()` / `awaitData()` 后判 `response.success()`，异常在 try-catch 里 `Logger.exp`，返回业务对象（可空）或 `Boolean`。老模块的 `retrofit2.Call` + `enqueue()` 保持原样。
- **日志**：只用 `com.mltech.base.log.Logger`（`v/d/i/w/e`；异常用 `Logger.exp(TAG, e, msg)`；需要落库排查的加 `save = true`），不用 `android.util.Log`。
- **路由**：跨模块跳转用 `com.mltech.router`（`@Route` + `@RouteQuery`，`Router.build(path).with(k, v).navigate(context)`），路径常量放 `RouterPath`；不用显式 Intent 跳别的 feature。
- **UI**：只用 ViewBinding，不用 `findViewById` / Kotlin Synthetics；公共控件在 `core/uikit`。
- **其他**：图片 Glide（`ImageLoaderModule`）；Room（`AppDatabase`）+ MMKV；Agora 封装在 `core/rtc/rtc`；网易云信在 `data/message`；神策 `SensorsStatUtils`；APM `ApmService` / Volcengine / `MiCrash`。
- **全局初始化**只放在 `AppDelegate` / `AppLifecycle`，不散在 Activity 里。
- **安全**：不打印密码、明文 token、完整证件号；敏感信息脱敏；临时调试日志提交前删掉。

## Hard Gates（动手前必须满足，不满足就停）

这些门槛来自真实返工，优先于「看起来更标准的 MVVM / 更完整的 UI」。

1. **仓内锚点先于范例**
   - 动手前必须读并点名本仓已有的同类文件（例如接 IM 先读隔壁的 `*IMRepository`），回复里写清「我跟的是哪个文件」。
   - 禁止只凭通用 wiki / 标准 sample 搭结构。本仓同类实现和通用范例冲突时，以本仓为准。

2. **类与层有上限，默认做减法**
   - 一个小玩法 / 子功能默认：`Api` + `Repository`（或独立 `IMRepository`）+ `ViewModel` + `Fragment/View` + `State/Bean`。
   - **禁止默认加** DataSource、UseCase、多层包装 Flow、把 UI 文案再建模成独立状态类。
   - Repository 只调接口；IM Repository 只监听与解析；ViewModel 才写状态机。判据：谁决定下一个 phase 谁就是 ViewModel，Repository 只回答「服务端说了什么」，它的返回类型里不出现 UiState / phase 类型。用户指令和这条判据冲突时先指出冲突，不照字面执行。ViewModel 臃肿时按 `android-architecture-wiki` 的 `interaction-state.md` 把私有变量按生命周期分组收拢（局级值收进一个对象、新局整体替换），不搬层。

3. **设计稿 → XML 按 `android-view-wiki` 的 `design-to-xml.md`**（参考图 → 分块表 → 尺寸语义 → 资产清单 → 按块交付；没有设计稿的 UI 不先做）。本仓事实：
   - 现有页面布局是 XML + ConstraintLayout + ViewBinding。
   - 可拖拽的悬浮块用 `com.mltech.core.uikit.view.UiKitSlideFloatView` 整块包住。
   - Figma 走 Framelink MCP，导出图先放 `.figma-out/`（不入库），确认后按导出倍率放进对应 `drawable-*dpi`。

4. **UI 按块验收**：本仓默认不编译，每块写完请用户截图，对照同一个 Figma node，过了再写下一块。

5. **分段交付，检查点过了再往下**
   - 禁止入口 + IM + 动画 + 结果页一次铺开。按可独立验证的片交付（例如：入口 → 邀请/接受 → 结果动画 → 真心话）。
   - 每片先验证状态转换与 UI，再进入下一片；片内发现架构跑偏，先收回来再继续。白名单与对账按 `change-plan`。

6. **复杂状态需求走 C 档**
   - 多角色、IM、状态机需求走 `change-plan` 的三步核心（理逻辑 → 定状态 → MVVM 骨架）和两次批准；流程细节只在那里，本文件不复述。
   - 仓内约定（只写在这里）：构造注入进 ViewModel 的 Repository 抽接口，命名 `I*Repository + *Repository`（如 `ILoveRoomGameRepository`），Koin 按接口注册；ViewModel 与 `*IMRepository` 用具体类。抽不抽接口看有没有真实替换点，不看「是不是一层」。
