# 网域层与用例

网域层是**可选**的，位于 UI 层和数据层之间，封装可复用的业务逻辑。

注意：这里的"网域层"是 Android 官方架构里的定义，和 Clean Architecture 里的 domain 层名字相同但含义有差异，不要拿另一套的规矩往这里套。

## 该不该加

只有这两种情况才加：

1. **多个 `ViewModel` 复用同一段与数据层交互的业务逻辑**
2. **某个 `ViewModel` 的业务逻辑复杂到需要拆解**

不该加的情况更要记住：

- 只是把 Repository 的调用**转发一层**，没有任何额外逻辑——纯增复杂度，零收益
- 逻辑只有一个 `ViewModel` 用，而且不复杂
- 需要的是**合并多个数据源的查询**，而 `Room` 本身能用一条关联查询搞定——这时候建一个 `NewsWithAuthorsRepository` 比建用例更合适，让数据库去做它擅长的事

策略：**按需添加**。如果某个项目里 UI 层几乎所有数据访问都已经走用例了，那统一都走用例也合理（一致性本身有价值）；但不要为了"架构完整"从零铺一层。

## 用例的形态

命名：**动词原形 + 名词 + UseCase**（`FormatDateUseCase`、`GetLatestNewsWithAuthorsUseCase`、`MakePaymentUseCase`）。

```kotlin
class GetLatestNewsWithAuthorsUseCase @Inject constructor(
    private val newsRepository: NewsRepository,
    private val authorsRepository: AuthorsRepository,
    private val defaultDispatcher: CoroutineDispatcher = Dispatchers.Default,
) {
    suspend operator fun invoke(): List<ArticleWithAuthor> =
        withContext(defaultDispatcher) {
            newsRepository.fetchLatestNews().map { article ->
                ArticleWithAuthor(article, authorsRepository.getAuthor(article.authorId))
            }
        }
}

// 调用处像函数一样用
val articles = getLatestNewsWithAuthors()
```

四条约束：

- **只负责一件事**。一个用例一个功能，需要多个动作就拆多个用例
- **不持有可变数据**。可变状态归 UI 层或数据层。因为无状态，所以每次作为依赖传递都可以直接创建新实例，不需要限定作用域
- **没有自己的生命周期**，受调用方约束。所以能被 `ViewModel`、`Service`、`Application`、以及 TV/Wear 的界面层复用
- **必须主线程安全**，自己负责切线程。但切之前先想清楚：这个重计算是不是更该放数据层？如果结果需要跨屏幕缓存复用，放数据层更好

`operator fun invoke()` 不限签名，可以有任意参数和返回类型，也可以重载。

## 用例依赖用例

正常且常见，网域层内出现多层用例不是味道问题：

```kotlin
class GetFormattedDateUseCase @Inject constructor(
    private val formatDateUseCase: FormatDateUseCase,
) { /* ... */ }
```

依赖方向仍然是单向：用例 → 用例 → Repository。用例**不能**依赖 `ViewModel` 或任何 UI 层类型。

## 别用 Util 类代替

同样的逻辑塞进 `XxxUtils` 的静态方法虽然能跑，但不推荐：Util 类难被发现、功能难被检索，而且用例可以通过基类共享线程处理和错误处理这类通用能力，团队规模大时差别明显。

## 症状 → 排查

| 症状 | 优先查 |
|---|---|
| 用例里只有一行 `return repository.xxx()` | 该删掉，直接让 `ViewModel` 调 Repository |
| 用例里存了字段、缓存了结果 | 用例不该有可变状态，缓存下沉到数据层 |
| 用例需要 `Context` 或 `ViewModel` | 依赖方向错了，这段逻辑放错层 |
| 多个 `ViewModel` 里有同一段业务逻辑复制粘贴 | 正是该抽用例的场景 |
| 用例里 `withContext` 做大列表映射，但多个屏幕都要用 | 结果需要复用，放数据层做并缓存 |
| 要合并两张表的数据，写了个用例 | `Room` 关联查询 + 一个 Repository 更合适 |
