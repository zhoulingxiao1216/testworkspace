#!/bin/bash
# 一次性修复 hubbuyer 目录权限（在服务器 SSH 中执行）
# 用法: sudo bash scripts/fix_permissions.sh

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
RUN_USER="${RUN_USER:-www}"

echo "项目目录: $SCRIPT_DIR"
echo "目标用户: $RUN_USER"

mkdir -p \
    "$SCRIPT_DIR/logs/all_execution" \
    "$SCRIPT_DIR/logs/error_summary" \
    "$SCRIPT_DIR/token" \
    "$SCRIPT_DIR/reports" \
    "$SCRIPT_DIR/config/data"

chmod +x "$SCRIPT_DIR/run.sh" 2>/dev/null || true
chmod -R u+rwX,g+rwX \
    "$SCRIPT_DIR/logs" \
    "$SCRIPT_DIR/token" \
    "$SCRIPT_DIR/reports" \
    "$SCRIPT_DIR/config/data"

if id "$RUN_USER" >/dev/null 2>&1; then
    chown -R "$RUN_USER:$RUN_USER" \
        "$SCRIPT_DIR/logs" \
        "$SCRIPT_DIR/token" \
        "$SCRIPT_DIR/reports" \
        "$SCRIPT_DIR/config/data"
    echo "✅ 已将 logs/token/reports/config/data 归属设为 $RUN_USER"
else
    echo "⚠️ 用户 $RUN_USER 不存在，请修改 RUN_USER 后重试"
    exit 1
fi

# 若 current_tokens.json 曾被 root 创建导致 www 无法写入，删除后由巡检重建
if [ -f "$SCRIPT_DIR/token/current_tokens.json" ] && [ ! -w "$SCRIPT_DIR/token/current_tokens.json" ]; then
    rm -f "$SCRIPT_DIR/token/current_tokens.json"
    echo "✅ 已删除不可写的 current_tokens.json，下次登录检查会重建"
fi

echo "完成。请确认宝塔计划任务执行用户为: $RUN_USER"
