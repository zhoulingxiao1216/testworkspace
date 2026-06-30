# 宝塔部署检查清单

## 📋 部署前检查项

### 1. 环境要求
- [ ] Python 3.8+ 已安装
- [ ] 确认 Python 解释器路径（`which python3` 或 `which python`）
- [ ] 确认系统编码支持 UTF-8

### 2. 文件权限设置
```bash
# 给 run.sh 添加执行权限
chmod +x run.sh

# 确保以下目录有写入权限
chmod -R 755 logs/
chmod -R 755 token/
chmod -R 755 reports/
```

### 3. 依赖安装
```bash
# 进入项目目录
cd /path/to/hubbuyer

# 安装依赖（建议使用虚拟环境）
pip3 install -r requirements.txt

# 或使用虚拟环境（推荐）
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 4. 配置文件检查
- [ ] 检查 `config/settings.py` 中的 `ENV_TYPE` 设置（prod/test/dev）
- [ ] 检查 `config/api/prod.py`（或对应环境的配置文件）中的 API 地址
- [ ] 检查 `config/data/login_data.py` 中的账号配置
- [ ] 检查 `config/settings.py` 中的企业微信 Webhook 地址

### 5. 目录结构检查
确保以下目录存在且可写：
```
hubbuyer/
├── logs/
│   ├── all_execution/     # 全量执行日志
│   └── error_summary/     # 错误汇总日志
├── token/                  # Token 存储目录
├── reports/                # 报告存储目录
└── config/
    ├── data/              # 数据配置文件
    └── rules/             # 规则配置文件
```

## 🔧 宝塔计划任务配置

### 方式一：使用 Shell 脚本（推荐）

1. **创建计划任务**
   - 任务类型：Shell 脚本
   - 任务名称：全球站巡检系统
   - 执行周期：根据需求设置（如：每天 08:00）

2. **脚本内容**
   ```bash
   /path/to/hubbuyer/run.sh
   ```
   或使用完整路径：
   ```bash
   cd /path/to/hubbuyer && /path/to/hubbuyer/run.sh
   ```

3. **日志输出（可选）**
   如果需要单独记录计划任务执行日志，可以在宝塔计划任务中设置：
   ```bash
   /path/to/hubbuyer/run.sh >> /path/to/hubbuyer/logs/cron_execution.log 2>&1
   ```

### 方式二：直接执行 Python

如果不想使用 Shell 脚本，可以直接执行：

```bash
cd /path/to/hubbuyer && /usr/bin/python3 main.py
```

**注意**：需要确保：
- Python 路径正确
- 工作目录正确
- 编码环境变量已设置

## ⚙️ 重要配置修改

### 1. 修改 run.sh 中的 Python 路径

如果系统 Python 路径不是 `python3`，需要修改 `run.sh` 第 15 行：

```bash
# 查找 Python 路径
which python3
# 或
which python

# 然后修改 run.sh
PYTHON_CMD="/usr/bin/python3"  # 使用完整路径
```

### 2. 使用虚拟环境（推荐）

如果使用虚拟环境，修改 `run.sh` 第 10-11 行：

```bash
# 取消注释并修改路径
source /path/to/hubbuyer/venv/bin/activate
```

### 3. 超时设置调整

如果任务执行时间较长，可能需要调整超时：

- **子脚本超时**：`core/runner.py` 第 38 行，默认 45 秒
- **API 请求超时**：各 API 脚本中，默认 15-25 秒

## 🐛 常见问题排查

### 1. 权限问题
```bash
# 检查文件权限
ls -la run.sh
ls -la logs/ token/ reports/

# 修复权限
chmod +x run.sh
chmod -R 755 logs/ token/ reports/
```

### 2. Python 路径问题
```bash
# 检查 Python 版本和路径
python3 --version
which python3

# 如果找不到，尝试
python --version
which python
```

### 3. 编码问题
如果出现中文乱码，检查：
- 系统编码：`locale`
- Python 编码：`python3 -c "import sys; print(sys.stdout.encoding)"`
- 确保 `run.sh` 中设置了编码环境变量

### 4. 依赖缺失
```bash
# 检查依赖是否安装
pip3 list | grep requests
pip3 list | grep urllib3

# 重新安装
pip3 install -r requirements.txt
```

### 5. 路径问题
确保所有路径都是绝对路径或相对于项目根目录：
- 代码中已使用 `os.path.abspath(__file__)` 动态获取路径
- 确保在项目根目录执行脚本

### 6. 日志文件过大
定期清理日志文件（可选，添加到计划任务）：
```bash
# 清理 30 天前的日志
find /path/to/hubbuyer/logs -name "*.log" -mtime +30 -delete
```

## 📊 监控建议

1. **检查执行日志**
   - 查看 `logs/cron_execution.log`（如果启用）
   - 查看 `logs/all_execution/` 目录下的执行日志
   - 查看 `logs/error_summary/` 目录下的错误日志

2. **检查报告生成**
   - 查看 `reports/` 目录下是否正常生成报告

3. **检查企业微信通知**
   - 确认 Webhook 地址正确
   - 确认网络可以访问企业微信 API

## ✅ 部署验证

部署完成后，手动执行一次验证：

```bash
cd /path/to/hubbuyer
./run.sh
```

检查：
- [ ] 脚本正常执行
- [ ] 日志正常生成
- [ ] 报告正常生成
- [ ] 企业微信通知正常发送（如果有错误）

## 📝 注意事项

1. **时区设置**：确保服务器时区正确，报告中的时间戳会使用系统时区

2. **网络连接**：确保服务器可以访问目标 API 地址

3. **资源限制**：如果任务较多，注意服务器资源使用情况

4. **备份配置**：部署前备份重要配置文件

5. **测试环境**：建议先在测试环境验证，再部署到生产环境





🚀 Hubbuyer 巡检系统部署与环境兼容性指南
本指南用于解决由于服务器环境变更、Git 重新拉取或宝塔 Python 项目管理器路径变动导致的运行异常。

1. 核心环境配置 (run.sh)
由于宝塔环境路径可能存在非标准拼写（如 pyporject_evn），执行脚本必须指向 Python 解释器的“真身”路径。

执行脚本路径: /www/wwwroot/xierun_check_product/hubbuyer/run.sh

Python 关键路径: /www/server/pyporject_evn/versions/3.8.0/bin/python3

配置要点:

脚本内通过 PYTHON_EXEC 变量锁定解释器，不依赖 source 激活虚环境。

执行前须确保权限正确：chown -R www:www /www/wwwroot/xierun_check_product/hubbuyer。

2. 代码兼容性规范 (重要)
为了兼容宝塔底层可能存在的旧版 subprocess 模块，core/runner.py 必须遵循以下写法，严禁使用 Python 3.7+ 的简写参数：

禁止使用: capture_output=True（会导致 __init__ 参数异常）。

禁止使用: text=True（部分环境无法识别）。

必须使用:

Python
process = subprocess.run(
    cmd, 
    stdout=subprocess.PIPE,     # 显式重定向输出
    stderr=subprocess.PIPE,     # 显式重定向错误
    universal_newlines=True,    # 代替 text=True 的老牌兼容参数
    encoding='utf-8', 
    ...
)
3. 自动化部署流程
当你从 Git 重新下载项目到新环境时，请按此顺序操作：

拉取代码: git clone 或 git pull。

同步修复版代码: 确保 core/runner.py 包含上述兼容性修改并已提交至仓库。

配置计划任务:

任务类型：Shell 脚本。

执行周期：按需设置。

脚本内容：直接调用项目内的 run.sh。

执行用户: 必须选择 www。

安装依赖 (仅需一次): 如遇缺库，运行：/www/server/pyporject_evn/versions/3.8.0/bin/python3 -m pip install -r requirements.txt。

4. 故障排查
若日志显示 Runner内部异常：检查 runner.py 是否被 Git 覆盖回了旧版 capture_output 写法。

若日志显示 Permission denied：重新执行 chown -R www:www。




#【shell脚本】

#!/bin/bash
# hubbuyer 巡检系统执行脚本

# 进入项目目录
cd /www/wwwroot/xierun_check_product/hubbuyer || exit 1

# 强制清理代理
unset http_proxy https_proxy HTTP_PROXY HTTPS_PROXY all_proxy ALL_PROXY

# 设置编码
export PYTHONIOENCODING=utf-8
export LANG=zh_CN.UTF-8
export LC_ALL=zh_CN.UTF-8
# 禁用 Python 输出缓冲，确保实时输出到日志
export PYTHONUNBUFFERED=1

# 激活宝塔 Python 项目环境（和终端中一样的方式）
# 不再依赖失效的 source 激活环境，直接指定 Python 真身路径
PYTHON_EXEC="/www/server/pyporject_evn/versions/3.8.0/bin/python3"

# 记录执行开始时间
echo "=========================================="
echo "Hubbuyer 巡检系统开始执行"
echo "执行开始时间: $(date '+%Y-%m-%d %H:%M:%S')"
echo "工作目录: $(pwd)"
echo "Python 命令: python"
echo "=========================================="

# 此时应该显示 (hubbuyer) 前缀，使用激活环境中的 Python
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

exit $EXIT_CODE