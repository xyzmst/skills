# 布局失控时怎么办

官方自己承认「achieving good layout with PlantUML is sometimes non-trivial」。本页按症状组织，每条都在本机渲染读图验证过（标注了未验证的除外）。

**先试最轻的手段**：调整声明顺序、`--` 换 `-`、`together`。手动指定方向是最后手段，官方明说 Graphviz 通常无需调整——手动定方向是在和布局引擎对抗。

## 布局引擎

| 引擎 | 启用 | 特点 |
|---|---|---|
| Graphviz | 默认 | 依赖外部 `dot` 程序 |
| Smetana | `!pragma layout smetana` 或 `-Playout=smetana` | 内置 Java 实现，箭头更直 |
| ELK | `!pragma layout elk` | 只支持正交布局，不支持全部特性 |
| VizJs | `-graphvizdot vizjs` | 节点铺得更开，图更大 |

**本机没装 graphviz，类图走的是自动落到的 smetana，出图正常。** `-testdot` 会报 `Dot executable does not exist` / `only sequence diagrams will be generated`，那是误报，别为它去装 graphviz。

官方称两个引擎对 `package` 嵌套的元素声明顺序要求**相反**：Graphviz 是「先嵌套元素后简单元素」，Smetana 反过来「先简单元素后嵌套元素」。**本机无 graphviz，这条没法对比验证**——如果同一份源码在别人机器上布局不同，先怀疑这里。

## 症状与手段

### 两条边叠成了一条，只剩一个箭头

同一对元素之间样式相同的两条边会被合并。让线型或颜色不同就分开画：`A --> B` 配 `B -[#red,dashed]-> A`。**违反依赖方向的反向边就是这么在图上消失的。**

### 有的类孤零零漂在角上

没有任何连线的类，布局引擎无处安放。`remove @unlinked` 清掉，或者 `hide @unlinked` 留位不画。

**坑**：`remove @unlinked` 会连带吃掉 note——图上的注释莫名消失时先查这条。

只想让两个无关的类挨着放，用 `together` + 隐藏连线：

```
together {
  class T1
  class T2
}
T1 -[hidden]- T2
```

`-[hidden]-` 建立一条不可见的约束，元素被拉到一起但线不画。注意它**算一条连线**，所以被 `-[hidden]-` 连起来的类不会被 `remove @unlinked` 清掉。

### 继承箭头一大把，指向同一个父类

`skinparam groupInheritance 3` —— 从 3 个子类起把空心三角合并成一个。sealed class 有多个子类型时图会干净很多。数字就是合并阈值。

### 图太宽 / 层次方向不对

```
left to right direction     ' 整图横向（默认 top to bottom）
A -left-> B                 ' 单条边定方向，可缩写 -l-> -r-> -u-> -d->
A - B                       ' 单破折号 = 水平，双破折号 -- = 垂直
```

**实测的反直觉行为**：方向关键字是**相对图的流向**的，不是绝对方位。加了 `left to right direction` 之后，`-down->` 实际把目标放到右上、`-right->` 放到下方、`-up->` 放到左边——整体旋转了 90 度。两者混用基本一定会得到意外结果，**要么只用全局方向，要么只用单条方向**。

### 类框里有一堆空格子

`hide empty members`。没有成员的类会收成紧凑单行框，只画关系的图必开。

### 只想看关系不想看成员

`hide members`（或 `hide fields` / `hide methods`）即使定义了也不显示。`show Foo methods` 可以在全局隐藏之后开单个例外。

## 未验证

`scale`（整图缩放）、`page HxV`（大图拆成多页）本机没测过，需要时先渲染确认再用。
