#【shell脚本】
#!/bin/bash
# Sakuradk3 巡检系统执行脚本

# 进入项目目录
cd /www/wwwroot/xierun_check_product/sakuradk3 || exit 1

# 强制清理代理
unset http_proxy https_proxy HTTP_PROXY HTTPS_PROXY all_proxy ALL_PROXY

# 设置编码
export PYTHONIOENCODING=utf-8
export LANG=zh_CN.UTF-8
export LC_ALL=zh_CN.UTF-8

# 激活宝塔 Python 项目环境（和终端中一样的方式）
# 不再依赖失效的 source 激活环境，直接指定 Python 真身路径
PYTHON_EXEC="/www/server/pyporject_evn/versions/3.8.0/bin/python3"

# 此时应该显示 (hubbuyer) 前缀，使用激活环境中的 Python
$PYTHON_EXEC -u main.py
EXIT_CODE=$?

# 记录执行时间
echo "执行完成时间: $(date '+%Y-%m-%d %H:%M:%S')"