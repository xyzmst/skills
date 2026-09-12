---
name: plantuml-wiki
description: PlantUML 语法与本地渲染知识库，覆盖该用哪种图的判据、类图完整关系符号与成员分区、creole 文字格式与三色 diff 记法、类与线的样式、布局失控时的干预手段（引擎差异/方向/together/hide-remove）、以及一批只有渲染过才知道的静默失败。当需要写 .puml 源码、画改动类图或时序状态图、渲染出来的图布局糊了或元素漂浮、成员跑错分区、颜色注释图例不生效、渲染出 0 字节或报 dot 不存在时使用。
---

# PlantUML Wiki

查询型知识库。只在**需要确认写法**时读对应 reference，一次读一个，不要整包拉进上下文。

## 渲染（先让图出来）

```bash
S=~/.agents/skills/plantuml-wiki/scripts/puml-render.sh
$S <in.puml> [out.png]    # 文件 → 文件，打印产物路径
$S -                      # stdin → stdout
```

jar 默认在 `~/.plantuml/plantuml.jar`，`PLANTUML_JAR` 可覆盖，脚本找不到会打出安装命令。**本地渲染，源码不外传**——别把业务类名字段名发去 plantuml.com。

**渲染完必须自己看一眼 PNG。** 这不是谨慎，是这个工具的三种失败**全都不报错**：

- 缺 `-Djava.awt.headless=true` → 输出 **0 字节 PNG，退出码 0**，stderr 全空（脚本已封好并拦空文件）
- 语法错误 → 照样出一张图，只是图上写着 `ERROR` 和行号
- 成员跑错分区、反向边被合并、颜色没生效 → 完全静默，退出 0，图也正常大小

`-testdot` 报 `Dot executable does not exist` / `only sequence diagrams will be generated` 是**误报**：没装 graphviz，类图照样正常出，新版会自动落到内置的 smetana 引擎。别为这条提示去装 graphviz。

## 该用哪种图

先答「这张图要回答什么问题」，答不出就别画——图是给人拍板用的，不是装饰。

| 要回答的问题 | 用 | 备注 |
|---|---|---|
| 这东西住在哪、和谁什么关系 | 类图 | 归属决策，本仓主力场景，见 `change-plan` 的「改动类图」 |
| 谁调谁、什么顺序、谁在等谁 | 时序图 | 唯一能表达**时间**的图；死锁和竞态只在这儿看得见 |
| 状态怎么迁移、什么事件触发、有没有漏分支 | 状态图 | 状态机、播放器、通话态 |
| 流程的分支与并发 | 活动图 | 有判断和并行时才用，线性流程用列表 |
| 模块依赖方向 | 组件图 | 类图加 `package` 通常就够，别为分层单独画一张 |

**类图画不了的**：调用顺序、时间、并发交错。想表达「A 之后才能 B」就该换时序图，硬塞进类图会变成一堆没有语义的箭头。

## 路由

| 问题 | 读 |
|---|---|
| 关系符号该用哪个（`<|--` / `*--` / `o--` / `-->` / `..>`）、成员写在属性区还是方法区、可见性与 `{static}` `{abstract}`、泛型、stereotype 与 spot、`package` 与 `namespace`、四种 note、`hide`/`show`/`remove`、关联类 | [references/class.md](references/class.md) |
| 颜色和字体怎么加、creole 能用哪些标记（粗体/删除线/color/img）、三色 diff 记法、类与线的样式语法、渐变、`legend`、主题 | [references/style.md](references/style.md) |
| 图糊了/元素漂浮/箭头绕远/两条边叠在一起、方向控制、`together`、`hidden` 链接、继承箭头合并、大图分页、两个布局引擎的差异 | [references/layout.md](references/layout.md) |

## 硬规则速查

不用读 reference 就该遵守的：

- **固定头三行**：`skinparam classAttributeIconSize 0`（关掉 UML 图标，可见性回归 `+ - #`）、`hide empty members`（没成员的类不留空格子）、`skinparam shadowing false`
- **注释写在成员同一行的末尾**。单独一行的注释没有括号，会被判成属性排到属性区去——真要单独成行就加 `{method}` / `{field}` 显式指定分区
- **类名里不能包 `<color:...>`**，直接语法错；整类着色用背景色 `class Foo #LightGreen`
- **两条样式相同的反向边会被合并成一条**，只剩一个箭头。反向依赖、摘掉的关系要靠线型或颜色区分：`-[#red,dashed]->`
- **`remove @unlinked` 会连带吃掉 note**，清孤立类之前先确认图上没有要保留的注释
- 成员按目标语言原样写全（类型、可空、默认值、返回类型），别为了迁就渲染器写出非法签名——`waitTimeoutMs: var Long` 这种是错的
- 中文不用额外配置，脚本已带 `-charset UTF-8`
- 方向别乱调（`-left->`、`-up->`）。官方明说 Graphviz 通常无需调整，手动定方向是在和布局引擎对抗，先试 `together` 和调整声明顺序

## 覆盖边界

`references/` 里每一条都在本机渲染读图验证过。**时序图、状态图、活动图目前只有上面的选图判据，没有语法 reference**——等真用到时按同样的标准补（先实测再写），而不是先抄一份没验证的语法表。需要现查：[类图](https://plantuml.com/zh/class-diagram)、[时序图](https://plantuml.com/zh/sequence-diagram)、[状态图](https://plantuml.com/zh/state-diagram)、[活动图](https://plantuml.com/zh/activity-diagram-beta)、[creole](https://plantuml.com/zh/creole)、[颜色名](https://plantuml.com/zh/color)。

官方中文文档有不少页标着「This translation need to be updated」，和实际行为冲突时**以渲染结果为准**——`-testdot` 那条误报就是例子。
