# 测试平台自建

## 启动命令

在本目录执行：

```powershell
streamlit run app.py
```

访问地址通常为：

```text
http://localhost:8501
```

## 正式库访问约束

正式 PolarDB 配置存放在本地 `.streamlit/secrets.toml`，该文件已被 git 忽略。

安全约束：

- 严禁直接修改正式数据库。
- 只允许执行单条 `SELECT` 语句。
- 代码访问正式库时统一使用 `modules.readonly_db`，不要绕过该模块创建写连接。

## SKU 批量同步

页面路径：`pages/4_sku_bulk_sync.py`

用途：读取贴纸/吊牌批量上传 Excel 中的「贵社SKU」，按「商品番号」调用 Sakura 用户 API 更新后台 SKU。

使用步骤：

1. 在 `sku_accounts.json` 配置管理员 PHPSESSID 与客户 UID。
2. 启动 Streamlit 后进入「SKU 批量同步」。
3. 上传 `.xlsx` 模板，点击「解析并预览」。
4. 可选填写主订单号，用于预览当前 SKU。
5. 确认后点击「确认同步到后台」。

依赖：`pandas`、`openpyxl`（Excel 解析）。

同步日志目录：`sku_sync_logs/`。

详细方案见 `docs/BulkUpload-SKU-sync-test-platform-plan.md`。
