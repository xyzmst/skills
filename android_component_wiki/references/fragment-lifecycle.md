# Fragment 与 View 的两套生命周期

## 核心事实：Fragment 比它的 View 活得久

这是 Fragment 几乎所有诡异 bug 的根源。一个 Fragment 实例可以经历**多轮** View 的创建和销毁：

```
onAttach
onCreate                     ← Fragment 实例创建，只一次
  onCreateView               ← View 生命周期开始
  onViewCreated
  onStart / onResume
  onPause / onStop
  onDestroyView              ← View 销毁，但 Fragment 实例还活着
  onCreateView               ← 回退栈返回时，同一个实例再来一轮
  onViewCreated
  ...
onDestroy                    ← Fragment 实例销毁
onDetach
```

触发第二轮的典型场景：Fragment 被 `replace()` 且加入了返回栈，用户按返回键回来。此时 `onCreate` 不会再调，`onCreateView` 会。

由此推出两条硬规则。

## 一、View 相关的一律用 viewLifecycleOwner

```kotlin
// ❌ 用 this：Fragment 的生命周期，第二轮 onViewCreated 会再注册一次
//    第一次注册的观察者还活着，且持有已销毁的 View
viewModel.items.observe(this) { render(it) }

// ✅ 用 viewLifecycleOwner：随 View 销毁自动解除
viewModel.items.observe(viewLifecycleOwner) { render(it) }
```

用 `this` 的后果是**观察者累积**：回退栈来回几次，同一个回调注册了 N 份，每份都持有一个已销毁的 View——表现为回调执行多次、更新到看不见的 View 上，或者直接空指针。

`Flow` 的收集写法（`viewLifecycleOwner.lifecycleScope` + `repeatOnLifecycle`）见 `android-architecture-wiki` 的 `viewmodel-state.md`。

## 二、ViewBinding 必须在 onDestroyView 置空

```kotlin
class ItemListFragment : Fragment(R.layout.fragment_item_list) {

    private var _binding: FragmentItemListBinding? = null
    private val binding get() = _binding!!

    override fun onViewCreated(view: View, savedInstanceState: Bundle?) {
        _binding = FragmentItemListBinding.bind(view)
        // ...
    }

    override fun onDestroyView() {
        super.onDestroyView()
        _binding = null      // 漏了这行就是持有已销毁 View 的泄漏
    }
}
```

不置空的后果有两种，都很难查：View 树泄漏；以及回退栈返回后 `binding` 指向上一轮已销毁的 View，改属性没有任何效果。

`binding get() = _binding!!` 这个写法本身要求**只在 View 存在期间访问**。如果有异步回调可能在 `onDestroyView` 之后到达，那里不能直接用 `binding`——要么用 `viewLifecycleOwner` 把回调绑定到 View 生命周期上（首选），要么访问前判空。

## Fragment 的状态恢复

Fragment 有自己的 `onSaveInstanceState(Bundle)`，语义和 Activity 一致，同样只放最小输入。

`arguments` 里的 `Bundle` 会被系统保留并在重建时还原，所以**参数一律走 `arguments`，不要写带参构造函数**：

```kotlin
// ❌ 系统重建时只调无参构造，itemId 永久丢失
class DetailFragment(private val itemId: String) : Fragment()

// ✅
class DetailFragment : Fragment(R.layout.fragment_detail) {
    private val itemId: String by lazy { requireArguments().getString(KEY_ID)!! }

    companion object {
        private const val KEY_ID = "item_id"
        fun newInstance(itemId: String) = DetailFragment().apply {
            arguments = bundleOf(KEY_ID to itemId)
        }
    }
}
```

用 Navigation 的话 Safe Args 会生成类型安全的参数封装，比手写 `Bundle` 键更可靠。

需要自定义构造依赖时（比如注入），用 `FragmentFactory` 而不是带参构造。

## onDestroyView 与 onDestroy 分别清什么

| 清理对象 | 位置 |
|---|---|
| `binding`、适配器、动画、View 上的监听器、`Handler` 的 `postDelayed` | `onDestroyView` |
| 与 View 无关的资源（连接、注册到全局的回调） | `onDestroy` |

放错位置的典型后果：动画放在 `onDestroy` 取消，回退栈返回时上一轮的动画还在跑，操作的是已销毁的 View。

## 症状 → 排查

| 症状 | 优先查 |
|---|---|
| `binding` 空指针，尤其在异步回调里 | 回调在 `onDestroyView` 之后到达，绑到 `viewLifecycleOwner` 或判空 |
| 回退栈返回后界面不更新、改属性无效 | `binding` 没置空，指向上一轮已销毁的 View |
| 观察者回调执行多次 | 用了 `this` 而不是 `viewLifecycleOwner` |
| 内存泄漏指向 Fragment 的 View | `onDestroyView` 里漏了置空或漏了解绑 |
| 重建后参数变 null | 用了带参构造函数，改走 `arguments` |
| 回退返回后动画错乱 | 动画取消放在了 `onDestroy` 而非 `onDestroyView` |
| `onCreate` 里的初始化在返回后没重跑 | 那是设计如此——第二轮只走 `onCreateView`，View 相关初始化要放 `onViewCreated` |
