#!/usr/bin/env bash
# 把 PlantUML 源码渲染成 PNG，本地执行，源码不外传。
#
#   puml-render.sh <in.puml> [out.png]   # 文件 → 文件（默认同名 .png），打印产物路径
#   puml-render.sh -                     # stdin → stdout
#
# 依赖 plantuml.jar，默认 ~/.plantuml/plantuml.jar，可用 PLANTUML_JAR 覆盖。
# 不需要 graphviz：新版 PlantUML 找不到 dot 时自动用内置 smetana 布局。
set -euo pipefail

JAR="${PLANTUML_JAR:-$HOME/.plantuml/plantuml.jar}"

if [[ $# -eq 0 || "${1:-}" == "-h" || "${1:-}" == "--help" ]]; then
    sed -n '2,8p' "$0" | sed 's/^# \{0,1\}//'
    exit 2
fi

if [[ ! -f "$JAR" ]]; then
    echo "找不到 plantuml.jar：$JAR" >&2
    echo "装一次：mkdir -p ~/.plantuml && curl -sL -o ~/.plantuml/plantuml.jar \\" >&2
    echo "  https://github.com/plantuml/plantuml/releases/latest/download/plantuml.jar" >&2
    exit 1
fi

# headless 必须显式开。缺了它 java 在无显示环境下静默产出 0 字节 PNG，退出码照样是 0。
JAVA=(java -Djava.awt.headless=true -jar "$JAR" -pipe -tpng -charset UTF-8)

if [[ "$1" == "-" ]]; then
    "${JAVA[@]}"
    exit
fi

src="$1"
[[ -f "$src" ]] || { echo "找不到源文件：$src" >&2; exit 1; }
out="${2:-${src%.puml}.png}"
"${JAVA[@]}" <"$src" >"$out"

# PlantUML 语法出错时也可能静默产出空文件，这里拦一道
if [[ ! -s "$out" ]]; then
    echo "渲染产出 0 字节：检查 $src 的语法（@startuml/@enduml 是否配对、creole 标签是否闭合）" >&2
    exit 1
fi
echo "$out"
