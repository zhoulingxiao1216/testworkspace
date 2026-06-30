#!/bin/bash
# Hubbuyer 巡检系统执行脚本
# 用于宝塔面板定时任务

# 设置脚本所在目录为工作目录
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# 强制清理代理
unset http_proxy https_proxy HTTP_PROXY HTTPS_PROXY all_proxy ALL_PROXY

# 设置编码
export PYTHONIOENCODING=utf-8
export LANG=zh_CN.UTF-8
export LC_ALL=zh_CN.UTF-8

# 设置 Python 解释器路径（根据实际情况修改）
# 宝塔 Python 项目环境路径
PYTHON_EXEC="/www/server/pyporject_evn/versions/3.8.0/bin/python3"
# 如果上述路径不存在，可以尝试使用系统默认的 python3
# PYTHON_EXEC="python3"

# 显示执行开始信息
echo "=========================================="
echo "Hubbuyer 巡检系统开始执行"
echo "开始执行时间: $(date '+%Y-%m-%d %H:%M:%S')"
echo "工作目录: $(pwd)"
echo "Python 命令: $PYTHON_EXEC"
echo "=========================================="

# 执行主程序
$PYTHON_EXEC -u main.py
EXIT_CODE=$?

# 记录执行结果
echo "=========================================="
if [ $EXIT_CODE -eq 0 ]; then
    echo "执行状态: 成功"
else
    echo "执行状态: 失败 (退出码: $EXIT_CODE)"
fi
echo "执行完成时间: $(date '+%Y-%m-%d %H:%M:%S')"
echo "=========================================="