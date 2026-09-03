# R8 缩减与 keep 规则

## R8 做三件事

- **代码缩减**：从入口点（manifest 里的组件等）出发建引用图，删掉图外的代码
- **逻辑优化**：内联、去分支、重写代码
- **混淆**：把类名方法名缩短成 `a.b.a`

三件事共用一个前提：**R8 靠静态引用图判断"能不能到达"**。凡是运行时才决定的访问路径——反射、序列化、JNI、XML 里写的类名——都在图外，会被当成无用代码删掉或改名。keep 规则的唯一作用就是把这些路径补进图里。

## 默认值（AGP 8.0+）

- **完整模式默认开启**（`android.enableR8.fullMode`）。它对"代码不会用反射"的假设更强，优化更激进，代价是需要更多 keep 规则。可以用 `android.enableR8.fullMode=false` 退出，但那是短期止血手段
- **缺少类会让构建失败**（AGP 8.0 起从警告变失败）。修法是补上缺失的库，或对确认用不到的部分加 `-dontwarn`
- **默认规则等价于 `proguard-android-optimize.txt`**。AGP 9.0 起 `getDefaultProguardFile()` 只支持这一个文件，不再支持 `proguard-android.txt`——后者内含 `-dontoptimize`，用了等于白关优化
- AGP 8.12.0 起有**优化型资源缩减**：资源被纳入同一张引用图，代码和资源一起判断可达性。好处是删得更干净，代价是"只被反射引用的资源"也会被删
- 新 `optimization {}` DSL 下，优化型资源缩减始终启用，默认 Android keep 规则改为按需停用；R8 还会默认重新封装类（不需要再写 `-repackageclasses`）

## keep 规则怎么写

**先划清什么必须 keep**：

| 场景 | 为什么会被删/改名 |
|---|---|
| 反射创建实例、反射调方法 | 引用图里没有这条边 |
| JSON 序列化的数据类 | Gson/Moshi 靠字段名反射，改名后字段对不上 |
| JNI 调用的类和方法 | native 侧按名字查找 |
| XML 里写类名的自定义 View、`Fragment` | 由 `LayoutInflater` 反射构造 |
| `Parcelable` 的 `CREATOR` | 框架按固定名字反射取字段 |
| 枚举的 `values()` / `valueOf()` | 序列化和反射会用 |

**AGP 9.0 起最容易踩的一条**：`-keep class A` **不再隐式保留默认构造函数**。以前它等价于 `-keep class A { <init>(); }`，现在不是。反射 `newInstance()` 的地方会在运行时崩，而且只在 release 包暴露：

```proguard
# AGP 9.0 起必须显式写出构造函数
-keep class com.example.model.** { <init>(); }

# 数据类要连字段一起保留
-keepclassmembers class com.example.model.** {
    <init>(...);
    <fields>;
}
```

同一条原则的另一面：**keep 规则不作用于编译器合成的成员**。AGP 9.0 起 companion 方法也归入这一类，别指望 keep 外层类就能连带保住合成成员。

**规则要窄**。`-keep class com.example.** { *; }` 能让崩溃消失，但它同时关掉了整个包的优化和混淆——包变大、代码可读、优化收益归零。写规则的顺序应该是：先精确到类和成员，实在定位不到再放宽。官方提供了 R8 配置分析器来找出最宽泛、最妨碍优化的规则，值得定期跑一次清理历史遗留。

**空检查处理**（AGP 9.0 新增）：`-processkotlinnullchecks` 取 `keep` / `remove_message` / `remove`，控制 Kotlin 编译器插入的空检查是保留、去掉消息还是整个去掉。想再压一点包体积可以用，但去掉后线上崩溃的信息量也会减少。

## 排查混淆后崩溃

1. **拿到未混淆的堆栈**：用构建产物里的 `mapping.txt` 还原

```bash
$ANDROID_HOME/tools/proguard/bin/retrace.sh mapping.txt stacktrace.txt
```

`mapping.txt` 每次构建都会变，**发版时必须归档**，否则线上堆栈永远还原不了。

2. **看崩在什么操作上**：`ClassNotFoundException` / `NoSuchMethodException` / `InstantiationException` 基本都是 keep 缺失；字段值全 null 通常是序列化字段被改名
3. **验证假设**：临时加一条精确 keep 规则，确认崩溃消失后再收窄成最小规则集
4. **区分是不是混淆问题**：`android.enableR8.fullMode=false` 或临时关 `isMinifyEnabled` 能定位，但只用来定位，别留在代码里

## 症状 → 排查

| 症状 | 优先查 |
|---|---|
| release 崩、debug 正常 | 混淆问题，先用 `mapping.txt` 还原堆栈 |
| `InstantiationException` / 反射建实例失败 | AGP 9.0 起 keep 不含默认构造函数，显式写 `{ <init>(); }` |
| JSON 解析出来字段全是 null | 数据类字段被改名，`-keepclassmembers` 保留 `<fields>` |
| 自定义 View 在 release 上 inflate 失败 | XML 里的类名靠反射，需要 keep |
| JNI 报找不到方法 | native 按名字查，keep 对应类和方法 |
| 构建报缺少类失败 | AGP 8.0 起从警告变失败，补库或 `-dontwarn` |
| 图片/字符串资源在 release 里丢了 | 优化型资源缩减把只被反射引用的资源删了 |
| 包体积没有下降 | 可能用了含 `-dontoptimize` 的 `proguard-android.txt`，或 keep 规则过宽 |
| 线上堆栈还原不了 | `mapping.txt` 没随版本归档 |
