#!/usr/bin/env python3
"""打印布局 XML 的约束拓扑：容器树、纵向锚点、反向依赖、静态告警。

用途是在改布局之前拿到「谁挂谁、谁挤谁、跨没跨容器」，替代通读整个 XML。

    layout-chain.py <layout.xml>              # 全文件
    layout-chain.py <layout.xml> --id tips_layout   # 只看这个 id 及其依赖方
"""
import sys
import os
import re
import xml.etree.ElementTree as ET

A = "{http://schemas.android.com/apk/res/android}"
APP = "{http://schemas.android.com/apk/res-auto}"

CONTAINERS = ("Layout", "ViewGroup", "RecyclerView", "ViewPager", "ScrollView",
              "CardView", "Flow", "ViewStub")

# 纵向锚点属性 -> (自己哪条边, 对方哪条边)
VERT = {
    "layout_constraintTop_toTopOf": ("T", "top"),
    "layout_constraintTop_toBottomOf": ("T", "bottom"),
    "layout_constraintBottom_toTopOf": ("B", "top"),
    "layout_constraintBottom_toBottomOf": ("B", "bottom"),
}
HORIZ = {
    "layout_constraintStart_toStartOf": ("S", "start"),
    "layout_constraintStart_toEndOf": ("S", "end"),
    "layout_constraintEnd_toStartOf": ("E", "start"),
    "layout_constraintEnd_toEndOf": ("E", "end"),
    "layout_constraintLeft_toLeftOf": ("S", "start"),
    "layout_constraintLeft_toRightOf": ("S", "end"),
    "layout_constraintRight_toLeftOf": ("E", "start"),
    "layout_constraintRight_toRightOf": ("E", "end"),
}

HARDCODE_DP = 40  # 直接约束到 parent 且 margin 超过这个值，提示位置是写死的


def short(tag):
    """去掉 {namespace} 前缀和包名前缀，只留末段。"""
    return tag.rsplit("}", 1)[-1].rsplit(".", 1)[-1]


def ref_id(v):
    if not v:
        return None
    if v in ("parent", "@id/parent"):
        return "parent"
    m = re.match(r"@\+?id/(.+)$", v)
    return m.group(1) if m else v


def get(el, name):
    for ns in (APP, A):
        v = el.get(ns + name)
        if v is not None:
            return v
    return el.get(name)


def dp(v):
    if not v:
        return 0
    m = re.match(r"(-?[\d.]+)dp", v)
    return float(m.group(1)) if m else 0


def walk(el, parent_tag, depth, out):
    """out: list of (depth, tag, id, parent_tag, element)"""
    for child in el:
        if not isinstance(child.tag, str):
            continue
        tag = short(child.tag)
        out.append((depth, tag, ref_id(get(child, "id")), parent_tag, child))
        walk(child, tag, depth + 1, out)


def is_container(tag):
    return any(k in tag for k in CONTAINERS) or tag in ("View",) is False and tag.endswith("Layout")


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return 2
    path = sys.argv[1]
    only = None
    if "--id" in sys.argv:
        only = ref_id(sys.argv[sys.argv.index("--id") + 1])
    if not os.path.exists(path):
        print("找不到文件: " + path, file=sys.stderr)
        return 1

    root = ET.parse(path).getroot()
    root_tag = short(root.tag)
    nodes = [(0, root_tag, ref_id(get(root, "id")), None, root)]
    walk(root, root_tag, 1, nodes)

    print("# " + os.path.basename(path))

    # --- 容器树：跨没跨容器只能在这里看出来 ---
    print("\n## 容器树")
    for depth, tag, vid, _p, _el in nodes:
        if "Layout" in tag or "Group" in tag or "View" in tag and tag != "View":
            if any(k in tag for k in CONTAINERS):
                print("  " * depth + tag + ("  #" + vid if vid else ""))

    # --- 纵向/横向锚点 ---
    print("\n## 锚点（同一个 ConstraintLayout 内才互相生效）")
    rows = []
    for depth, tag, vid, ptag, el in nodes[1:]:
        anchors = []
        for attr, (side, other) in list(VERT.items()) + list(HORIZ.items()):
            tgt = ref_id(get(el, attr))
            if tgt:
                anchors.append("%s->%s.%s" % (side, tgt, other))
        if not anchors:
            continue
        mt, mb = dp(get(el, "layout_marginTop")), dp(get(el, "layout_marginBottom"))
        mar = []
        if mt:
            mar.append("mT=%g" % mt)
        if mb:
            mar.append("mB=%g" % mb)
        vis = get(el, "visibility") or "visible"
        rows.append((vid or "(无 id)", tag, ptag, anchors, mar, vis))

    for vid, tag, ptag, anchors, mar, vis in rows:
        if only and vid != only:
            continue
        print("- %s [%s] 宿主=%s" % (vid, tag, ptag))
        print("    " + " ".join(anchors) + ("  " + " ".join(mar) if mar else "") +
              ("  vis=" + vis if vis != "visible" else ""))

    # --- 反向依赖：谁拿它当锚点。改 visibility 之前必看 ---
    print("\n## 反向依赖（有人依赖 → 它是锚点，只能 INVISIBLE 不能 GONE）")
    dep = {}
    for _d, _t, vid, _p, el in nodes[1:]:
        for attr in list(VERT) + list(HORIZ):
            tgt = ref_id(get(el, attr))
            if tgt and tgt != "parent":
                dep.setdefault(tgt, []).append((vid or "(无 id)", attr))
    if not dep:
        print("  （无）")
    for tgt in sorted(dep):
        if only and tgt != only:
            continue
        for src, attr in dep[tgt]:
            print("  %s ← %s 的 %s" % (tgt, src, attr))

    # --- 静态告警 ---
    print("\n## 告警")
    warn = 0
    for _d, tag, vid, ptag, el in nodes[1:]:
        if ptag and "ConstraintLayout" not in ptag:
            bad = [k for k in el.keys() if "layout_constraint" in k]
            if bad:
                warn += 1
                print("  [无效属性] %s 的宿主是 %s，这些 layout_constraint* 不生效：%s"
                      % (vid or tag, ptag, ", ".join(short(b) for b in bad[:4])))
        for attr, (side, _o) in VERT.items():
            if ref_id(get(el, attr)) == "parent":
                m = dp(get(el, "layout_marginTop" if side == "T" else "layout_marginBottom"))
                if m >= HARDCODE_DP:
                    warn += 1
                    print("  [位置写死] %s 的 %s 边直接约束到 parent 且 margin=%gdp"
                          "——没挂链，相邻元素高度一变就错位" % (vid or tag, side, m))
    if not warn:
        print("  （无）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
