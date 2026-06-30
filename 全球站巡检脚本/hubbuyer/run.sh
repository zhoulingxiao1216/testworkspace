#!/bin/bash
# Hubbuyer 巡检系统执行脚本（宝塔计划任务）
# 部署路径示例: /www/wwwroot/xierun_check_product/hubbuyer/run.sh

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

RUN_USER="${RUN_USER:-www}"

unset http_proxy https_proxy HTTP_PROXY HTTPS_PROXY all_proxy ALL_PROXY

export PYTHONIOENCODING=utf-8
export LANG=zh_CN.UTF-8
export LC_ALL=zh_CN.UTF-8
export PYTHONUNBUFFERED=1
export HUBBUYER_TOKEN_DIR="${SCRIPT_DIR}/token"

PYTHON_CANDIDATES=(
    "/www/server/pyporject_evn/versions/3.8.0/bin/python3"
    "/www/server/python_manager/versions/3.8.0/bin/python3"
    "$(command -v python3 2>/dev/null || true)"
)
PYTHON_EXEC=""
for candidate in "${PYTHON_CANDIDATES[@]}"; do
    if [ -n "$candidate" ] && [ -x "$candidate" ]; then
        PYTHON_EXEC="$candidate"
        break
    fi
done
if [ -z "$PYTHON_EXEC" ]; then
    echo "❌ 未找到可用的 python3，请修改 run.sh 中 PYTHON_CANDIDATES"
    exit 127
fi

mkdir -p logs/all_execution logs/error_summary token reports config/data

chmod -R u+rwX,g+rwX logs token reports config/data 2>/dev/null || true
if [ "$(id -u)" -eq 0 ] && id "$RUN_USER" >/dev/null 2>&1; then
    chown -R "$RUN_USER:$RUN_USER" logs token reports config/data 2>/dev/null || true
fi

LOG_FILE="${SCRIPT_DIR}/logs/cron_execution.log"
mkdir -p "$(dirname "$LOG_FILE")"

echo "==========================================" | tee -a "$LOG_FILE"
echo "Hubbuyer 巡检系统开始执行" | tee -a "$LOG_FILE"
echo "开始时间: $(date '+%Y-%m-%d %H:%M:%S')" | tee -a "$LOG_FILE"
echo "工作目录: $(pwd)" | tee -a "$LOG_FILE"
echo "执行用户: $(id -un) (uid=$(id -u))" | tee -a "$LOG_FILE"
echo "Python: $PYTHON_EXEC" | tee -a "$LOG_FILE"
echo "TOKEN_DIR: $HUBBUYER_TOKEN_DIR" | tee -a "$LOG_FILE"
echo "==========================================" | tee -a "$LOG_FILE"

"$PYTHON_EXEC" -u main.py 2>&1 | tee -a "$LOG_FILE"
EXIT_CODE=${PIPESTATUS[0]}

echo "==========================================" | tee -a "$LOG_FILE"
if [ "$EXIT_CODE" -eq 0 ]; then
    echo "执行状态: 成功" | tee -a "$LOG_FILE"
else
    echo "执行状态: 失败 (退出码: $EXIT_CODE)" | tee -a "$LOG_FILE"
fi
echo "完成时间: $(date '+%Y-%m-%d %H:%M:%S')" | tee -a "$LOG_FILE"
echo "==========================================" | tee -a "$LOG_FILE"

exit "$EXIT_CODE"
