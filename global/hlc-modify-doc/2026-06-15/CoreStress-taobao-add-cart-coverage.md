# 变更日志

- 日期：2026-06-15
- 修改文件：全球站压测脚本/Performance/core_stress.py
- 修改类型：修改
- 描述：加购链路去掉 break、双来源均压测，并修复淘宝关键词搜索结果 item 提取，使淘宝详情/加购可被覆盖。

## 变更摘要

### 变更点 1：_request_add_cart 去掉 break，1688/淘宝均尝试加购
- 变更原因：原逻辑 shuffle 后第一个来源（多为 1688）成功即 break，导致 `商品详情_taobao` / `商品加购_taobao` 从未出现在压测明细。
- 变更方式：
  - 动态加购时对 `1688`、`taobao` 两个来源**均**调用 `_build_dynamic_add_cart_payload` + `_post_add_cart`，不再 break。
  - 抽取 `_post_add_cart(source, payload)` 复用单次加购 POST 与 Locust 上报。
  - 仅当两个来源动态均失败时，才回退静态 payload（随机选一来源）。

### 变更点 2：淘宝搜索结果 item-id 多字段提取
- 变更原因：`_extract_search_items` 仅认 `item_id`，淘宝列表项可能使用 `num_iid` / `itemId` 等字段，导致搜索成功但解析为空、无法进入详情/加购。
- 变更方式：
  - 新增 `_SEARCH_ITEM_ID_KEYS`：1688 用 `offerId` 等；淘宝用 `item_id`、`itemId`、`num_iid` 等。
  - 优先从 `data.data.data`（及 items/list/records）列表提取，再深度遍历兜底。
  - `_get_search_item_id` 按来源依次尝试多个字段名。

## 验证
- `core_stress.py` AST 语法检查通过，无 lint 错误。
- main 环境实测：`POST /api_tb/product/detail` 对静态 item_id 返回 200，SKU 结构可拼加购 payload。
- 淘宝关键词接口当前因上游配额返回空列表，item 字段名待有数据后可在 `_SEARCH_ITEM_ID_KEYS["taobao"]` 中补充。
