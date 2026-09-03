# 结果回传与组件间通信

## Activity Result API

取代 `startActivityForResult()` / `onActivityResult()`。核心价值是把**结果回调**和**发起调用**解耦，所以它对注册时机有硬要求。

```kotlin
class EditFragment : Fragment(R.layout.fragment_edit) {

    // 直接作为成员初始化——register 可以在 Fragment 创建完成前安全调用
    private val pickImage = registerForActivityResult(
        ActivityResultContracts.GetContent()
    ) { uri: Uri? ->
        uri ?: return@registerForActivityResult
        viewModel.onImagePicked(uri)
    }

    private val requestPermission = registerForActivityResult(
        ActivityResultContracts.RequestPermission()
    ) { granted ->
        viewModel.onPermissionResult(granted)
    }

    private fun onPickClicked() {
        pickImage.launch("image/*")
    }
}
```

### 三条硬要求

**一、必须无条件注册。** 进程和 Activity 被重建时需要这个回调来接收结果，所以**每次创建都要注册**，即使发起逻辑依赖用户输入或业务判断：

```kotlin
// ❌ 条件注册：重建后条件不成立，结果永远收不到
if (needPickImage) {
    pickImage = registerForActivityResult(...) { }
}
```

**二、多个启动器的注册顺序必须每次相同。** 结果是按注册顺序分发的，顺序变了结果会进错回调。所以不要把 `register` 放在条件分支或循环里。

**三、注册可以早，启动不能早。** `registerForActivityResult()` 在 Fragment/Activity 创建完成前调用是安全的（这就是能写成成员变量初始化的原因），但 `Lifecycle` 到达 `CREATED` 之前不能 `launch()`。

### 进程死亡

**`launch()` 与结果回调之间，进程和 Activity 可能被销毁**（尤其是相机、系统相册这类重量级页面）。这意味着：

- 处理结果需要的额外上下文（"这张图要替换第几个位置"）**必须自己保存和恢复**，不能只放在字段里
- 存法走 `SavedStateHandle` 或 `onSaveInstanceState`，见 `activity-lifecycle.md`

这是 Activity Result API 最容易漏的一条：本地测试基本不会触发，线上在低内存设备上稳定复现。

### 在非 Activity/Fragment 的类里接收结果

`ComponentActivity` 和 `Fragment` 实现了 `ActivityResultCaller`，其他类可以直接用 `ActivityResultRegistry`。**优先用接受 `LifecycleOwner` 的重载**——它会在生命周期销毁时自动移除启动器；拿不到 `LifecycleOwner` 时必须手动 `unregister()`。

### 测试

`registerForActivityResult()` 有个重载可以传入自己的 `ActivityResultRegistry`，用来测试结果处理逻辑而不真的启动页面。测试用的 registry 需要实现 `onLaunch()`，在里面直接调 `dispatchResult()` 给出预设结果。

## Fragment 之间怎么通信

官方给两个选项，按数据性质选：

| 选项 | 适用 |
|---|---|
| **共享 `ViewModel`** | 需要持续共享的数据、自定义类型 |
| **Fragment Result API** | 能放进 `Bundle` 的**一次性结果** |

`setTargetFragment()` 已弃用，不要再用。

### Fragment Result API

```kotlin
// 接收方（在 onCreate 或 onViewCreated 注册）
setFragmentResultListener(REQUEST_KEY) { _, bundle ->
    val picked = bundle.getString(KEY_PICKED)
    viewModel.onPicked(picked)
}

// 发送方
setFragmentResult(REQUEST_KEY, bundleOf(KEY_PICKED to value))
```

投递规则（`fragment` 1.3.0 起，`FragmentManager` 实现 `FragmentResultOwner`）：

- 结果存在 `FragmentManager` 里，**接收方到达 `STARTED` 才投递**；设置结果时接收方已是 `STARTED` 则立即回调
- **一个 key 只有一个监听器和一个结果**。监听器还没到 `STARTED` 时重复 `setFragmentResult()`，待投递的结果会被最新的替换
- 监听器收到之后结果**被清除**，不会重复投递
- 返回栈上的 Fragment 要等被弹出并到达 `STARTED` 才收到结果

**监听和设置必须在同一个 `FragmentManager` 上**——这是"结果收不到"最常见的原因。父子 Fragment 用的是不同的 manager（父层是 `parentFragmentManager`，子层是 `childFragmentManager`），跨层级发收不到。

### 共享 ViewModel 的作用域

**作用域选错就拿不到同一个实例**，这是共享失败的唯一原因：

```kotlin
// Activity 作用域：同一 Activity 下的所有 Fragment 共享
private val sharedViewModel: ItemViewModel by activityViewModels()

// 父 Fragment 作用域：父子 Fragment 之间共享
private val sharedViewModel: ItemViewModel by viewModels({ requireParentFragment() })

// 自己的作用域：不共享
private val viewModel: DetailViewModel by viewModels()
```

用 Navigation 时还可以把作用域限定到某个目的地的 `NavBackStackEntry`，让 `ViewModel` 随该目的地出栈而清除——比 Activity 作用域更精确。

**注意 Activity 作用域的寿命**：`ViewModel` 会一直存活到它所属的 `ViewModelStoreOwner` 永久消失。单 Activity 架构下，Activity 作用域的 `ViewModel` 本质上是单例——首次实例化之后，后续获取永远返回同一个实例和同一份旧数据。用它存"每次进页面应该重置"的状态，就会看到上次的残留。

## 症状 → 排查

| 症状 | 优先查 |
|---|---|
| 结果回调收不到 | 条件注册了，或多个启动器注册顺序不固定 |
| 从相机/相册回来后崩溃或丢上下文 | 进程被杀，额外状态没走 `SavedStateHandle` |
| `launch()` 抛异常说生命周期不对 | 在 `CREATED` 之前调用了 `launch()` |
| 两个 Fragment 拿到不同的 `ViewModel` | 作用域选错，需要 `activityViewModels()` 或指定父 Fragment |
| 重进页面看到上次的旧数据 | Activity 作用域的 `ViewModel` 是单例级寿命，改用更窄的作用域 |
| Fragment 结果收不到 | 发送方和接收方不在同一个 `FragmentManager` 层级 |
| 结果回调里 `binding` 空指针 | 见 `fragment-lifecycle.md` |
