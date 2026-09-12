# 颜色、文字格式与样式

本页每条都在本机渲染读图验证过。颜色名清单：https://plantuml.com/zh/color ，creole 完整语法：https://plantuml.com/zh/creole

## creole 文字标记

成员、label、note、`title`、`legend` 里都能用：

| 写法 | 效果 |
|---|---|
| `<b>x</b>` | 粗体 |
| `<i>x</i>` | 斜体 |
| `<u>x</u>` | 下划线 |
| `--x--` 或 `<s>x</s>` | 删除线（两种都有效） |
| `<color:green>x</color>` / `<color:#FF7700>x</color>` | 文字颜色，颜色名或十六进制 |
| `<size:18>x</size>` | 字号 |

**类名里不能包 `<color:...>`**——`class <color:green>Foo</color>` 直接语法错。整类着色只能用背景色（见下）。

## 改动 diff 三色记法（本仓约定）

照业界 diff 惯例（MagicDraw 那套），不自造符号：

```
class CallConfigRepo {
  - api: CallConfigApi
  .. 其余成员省略 ..
  <color:green>+ fun normalizeTimeout(sec: Int?): Long  // 唯一归一化点</color>
  <color:blue>- private var waitTimeoutMs: Long  // 改为从 repo 取</color>
  <color:red>--const val WAIT_TIMEOUT_MS = 30_000L--</color>
}
class NewDelegate #LightGreen      ' 整类新增
class OldHelper #Pink              ' 整类删除
A -[#green]-> B : 新增关系
C -[#red,dashed]-> D : 摘掉或违规
legend right
  <color:green>绿 = 新增</color>
  <color:blue>蓝 = 改动</color>
  <color:red>红 + 删除线 = 删除</color>
  绿底 = 整类新增, 粉底 = 整类删除
endlegend
```

无标记的成员是列出来作对照的既有成员。整类删除只能靠底色 + 图例说明，类名加不了删除线。判据和完整记法在 `change-plan` 的「改动类图」那条。

## 类的颜色与边框

三种写法，从简到繁：

```
class A #LightGreen                                  ' 只改背景
class B #palegreen ##[dashed]green                   ' 背景 + 边框样式和颜色
class C #back:lightblue;line:green;line.bold;text:red ' 背景 / 边框 / 边框粗细 / 类名文字色
class D #red-green                                    ' 渐变背景
```

渐变的分隔符 `|` `/` `\` `-` 决定渐变方向。

## 线的颜色与样式

两种语法都有效，按需要的粒度选：

```
A -[#red,dashed,thickness=3]-> B          ' 方括号式：色 + 线型 + 粗细
A --> B #line:red;line.bold;text:red      ' 单行样式式：还能单独指定 label 文字色
```

线型可选 `bold` `dashed` `dotted` `hidden` `plain`。**要让两个类之间的正向边和反向边都画出来，必须让它们样式不同**——样式相同会被合并成一条。

## title 与 legend

```
title <b>标题</b> 可以带 <color:red>creole</color>
legend right
  任意多行，同样支持 creole
endlegend
```

`legend` 的位置可选 `left` / `right` / `center` / `top` / `bottom`，渲染进 PNG 里跟图一起出，图例必须写在图上而不是聊天里——图存下来之后聊天记录就找不到了。

## skinparam 常用

| 参数 | 作用 |
|---|---|
| `skinparam classAttributeIconSize 0` | 关掉可见性的彩色方块图标，显示 `+ - # ~` 符号本身。**几乎总要开** |
| `skinparam shadowing false` | 关阴影，图更干净 |
| `skinparam packageStyle rectangle` | `package` 从文件夹形换成方框 |
| `skinparam groupInheritance N` | 继承箭头从 N 个子类起合并成一个箭头头，sealed 多子类时有用 |
| `skinparam backgroundColor X` | 图整体背景 |

按 stereotype 批量定样式：

```
skinparam class {
  BackgroundColor PaleGreen
  BorderColor<<新增>> Tomato
}
```

注意 `BackgroundColor_<<x>>` 这种**下划线紧贴 stereotype** 的写法会让所有 skinparam 被静默忽略，官方已知 issue。
