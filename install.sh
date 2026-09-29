#!/usr/bin/env bash
# 把本仓每个 skill 软链到 ~/.agents/skills/<frontmatter name>；可重复执行。
set -euo pipefail

usage() {
  cat <<'EOF'
用法: ./install.sh [--with-cursor-rules]

  默认                   每个含 SKILL.md 的目录 → ~/.agents/skills/<name>
  --with-cursor-rules    另把 cursor_rules/*.mdc → ~/.cursor/rules/（常驻规则，每次会话都注入，按需开启）

目标已存在且不是软链时跳过并提示，不会覆盖。
EOF
}

WITH_RULES=0
case "${1:-}" in
  "") ;;
  --with-cursor-rules) WITH_RULES=1 ;;
  -h|--help) usage; exit 0 ;;
  *) usage >&2; exit 1 ;;
esac

ROOT="$(cd "$(dirname "$0")" && pwd)"

link() {
  local src=$1 dst=$2
  if [ -e "$dst" ] && [ ! -L "$dst" ]; then
    echo "跳过 ${dst}：已存在且不是软链，请手动处理" >&2
    return
  fi
  ln -sfn "$src" "$dst"
  echo "$dst -> $src"
}

SKILLS_DIR="$HOME/.agents/skills"
mkdir -p "$SKILLS_DIR"
for skill_md in "$ROOT"/*/SKILL.md; do
  dir="$(dirname "$skill_md")"
  name="$(sed -n 's/^name:[[:space:]]*//p' "$skill_md" | head -1)"
  if [ -z "$name" ]; then
    echo "跳过 ${dir}：SKILL.md 缺少 name" >&2
    continue
  fi
  link "$dir" "$SKILLS_DIR/$name"
done

if [ "$WITH_RULES" = 1 ]; then
  RULES_DIR="$HOME/.cursor/rules"
  mkdir -p "$RULES_DIR"
  for rule in "$ROOT"/cursor_rules/*.mdc; do
    link "$rule" "$RULES_DIR/$(basename "$rule")"
  done
fi
