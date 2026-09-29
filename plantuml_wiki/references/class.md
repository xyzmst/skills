# 类图语法

本页每条都在本机渲染读图验证过。完整语法（含本页未收的冷门特性）：https://plantuml.com/zh/class-diagram

## 骨架

```
@startuml
skinparam classAttributeIconSize 0
skinparam shadowing false
hide empty members

package "feature 层" {
  class CallViewModel {
    - repo: CallConfigRepo
    .. 其余成员省略 ..
    + fun start(deadlineMs: Long): Boolean
  }
}
CallViewModel --> CallConfigRepo
@enduml
```

`hide empty members` 让没有成员的类收成一个紧凑单行框，只画关系时必开。

## 元素声明

| 写法 | 渲染 |
|---|---|
| `class Foo` | 绿色 `C` 图标 |
| `interface Foo` | 蓝色 `I` 图标，类名斜体 |
| `abstract class Foo` / `abstract Foo` | 蓝色 `A` 图标，类名斜体 |
| `enum Foo` | 橙色 `E` 图标，枚举值不带可见性前缀 |
| `annotation Foo` | 红棕 `@` 图标 |
| `object Foo` | **无分隔线的框**，是对象图元素，不是类 |

Kotlin 的 `object`（单例）**别用 `object` 关键字**——那是对象图语义，画出来没有成员分区。用 `class PayModule <<object>>`，既保留类的外观又标出了生命周期。

**别名和非字母名**：`class "带 空格 的名字" as Weird`，之后全文只能用 `Weird` 引用。

**泛型**：`interface Repo<K, V>`、`class MemCache<String, Config>`。类名框**右上角出一个小角标** `K, V`，类名本身不带尖括号。成员里的泛型（`StateFlow<UiState>`、`Result<T>`、`List<Peer>`）原样写就行，不会被当 HTML 标签吃掉。

**自定义 spot**：`class Service <<(S,#FF7700) 服务>>` → 橙色圆圈 `S` + `«服务»`。给自定义类型（Delegate、UseCase）换个标记时用。

## 成员

### 分区判定（踩过的坑）

PlantUML 自动把成员分到属性区和方法区，判据和括号有关但不是「有括号就是方法」——`val onTick: (Long) -> Unit` 这种 lambda 类型字段带括号，实测仍正确落在属性区。

**真正会出错的是纯注释行**：单独一行的 `// null 兜 30_000L` 没有括号，被判成属性，排到方法区上面去，看起来像在注释另一个成员。两种解法：

- 注释写在成员**同一行末尾**（推荐，简单）
- 用 `{field}` / `{method}` 显式指定分区，写在行首

```
class A {
  {field} - val onTick: (Long) -> Unit
  {method} + fun start(ms: Long)
}
```

### 可见性与修饰符

`-` private、`#` protected、`~` package private、`+` public。必须配 `skinparam classAttributeIconSize 0` 才显示符号本身，否则渲染成彩色方块图标。

`{abstract}` → 斜体。`{static}` → **下划线**（UML 标准写法）。都可写在行首或行尾。

### 分隔符

`--`（实线）、`..`（虚线）、`==`（粗线）、`__`（下划线）都能当分组线，且**可以带标题**：

```
class CallConfig {
  + val timeoutSec: Int?
  .. 其余成员省略 ..
  .. companion object ..
  + const val DEFAULT_MS = 30_000L
}
```

`.. 其余成员省略 ..` 是折叠无关成员的标准做法，比写 `...` 清楚（`...` 也能渲染，但没有标题语义）。`companion object` 没有专门语法，用带标题的分隔符表达。

## 关系

| 符号 | 含义 | 什么时候用 |
|---|---|---|
| `<\|--` | 继承 | 实线 + 空心三角 |
| `<\|..` | 实现接口 | 虚线 + 空心三角 |
| `*--` | 组合 | 没有整体就没有部分（生命周期绑定） |
| `o--` | 聚合 | 部分可独立存在 |
| `-->` | 依赖 | 持有、调用、observe，**最常用** |
| `..>` | 弱依赖 | 只是用到类型、反射、临时引用 |

`--` 换成 `..` 一律变虚线。**单破折号 `-` 让线变水平，双破折号 `--` 垂直**——这是调布局最轻量的手段。

`extends` / `implements` 关键字等价且更好读：`class ArrayList implements List`、`class Child extends Base`。

**标签与重数**：`Student "0..*" -- "1..*" Course : 选课`，引号里的是端点重数，冒号后是关系名。

**关联类**（关系本身有属性）：先声明关系，再 `(Student, Course) . Enrollment` —— 关系线中点出一个小圆点，虚线连到 `Enrollment`。

## note 四种

```
note top of Foo : 单行类级注释
note left of Foo
  多行类级注释
end note

note left of A::onTick          ' 成员级，精确指向那一行
  这个回调在销毁时要置空
end note

A --> B : observe
note on link                     ' 必须紧跟在关系定义之后
  连线上的注释
end note

note "浮动注释" as N1            ' 浮动，可连多个元素
N1 .. A
```

成员级注释**只支持 `left` / `right`**，不支持 `top` / `bottom`，也不能和 `::` 命名空间分隔符同时用。同名重载要用引号区分：`note right of A::"start(Duration timeout)"`。

**而且 `left` / `right` 只是建议**：目标类在 `package` 里、指定那侧被相邻 package 占满时，布局会把注释甩到反方向，甚至贴着画布边缘（实测 `note right of CallConfigRepository::waitTimeoutMs` 渲染到了左边并顶住 x=0）。它仍然连着正确的成员，只是位置不由你定——**这也是必须看一眼 PNG 的原因之一**。要位置可控就别用成员级注释，改行尾注释或类级 note。

**只写一行才精确**：单行注释的折角尖端正好对准目标成员那一行，指向不含糊。**写两行以上，注释框变高，会视觉盖住上下邻居的成员行**——它仍然逻辑上挂在正确的成员上，但读图的人会分不清是指哪一行，尤其目标成员上下还有其他成员时。成员级注释保持一行；超过一行就搬到行尾注释（同一行末尾）或类级 note。

**坑**：`remove @unlinked` 会连带吃掉 note，两者一起用时先确认没删掉要留的注释。

## package 与 namespace

```
package "feature 层" #DDDDDD {
  class CallViewModel
}
```

新版 `package` 和 `namespace` 已是同义词。分层画依赖方向时用 `package`，连线跨层往上一眼可见。`skinparam packageStyle rectangle` 换成方框样式（默认是带标签的文件夹形）。

类名里带 `.` 会**自动创建包**，`set namespaceSeparator none` 关掉。Android 全限定类名容易误触发这条。

## hide / show / remove

按需裁剪，画大图时有用：

- `hide empty members` — 没成员的类不留空格子（几乎总要开）
- `hide members` / `hide fields` / `hide methods` — 即使定义了也不显示，只看关系时用
- `hide circle` — 去掉类名前的 `C`/`I`/`E` 图标
- `hide stereotype` — 去掉 `«...»`
- `remove @unlinked` / `hide @unlinked` — 清掉没有任何连线的孤立类
- `remove $tag` — 元素上标 `$tag` 后可整批删；配 `restore` 做「只留某一组」

`hide` 留位不画，`remove` 彻底移除。`show` 可以在全局 `hide` 之后开个例外：`hide members` + `show Dummy1 methods`。
