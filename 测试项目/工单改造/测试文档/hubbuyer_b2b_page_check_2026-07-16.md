# Hubbuyer B2B 前台頁面可用性檢查（2026-07-16）

- 檢查入口：https://main-b2b.hubbuyer.com/jp
- 執行時間：2026-07-16T02:06:44.085Z ~ 2026-07-16T02:09:35.605Z
- 登入狀態：未登入（未取得截圖中的 Chrome 登入態）
- 首頁內部連結：17 個，本次檢查 17 個
- 按鈕/互動入口：24 個
- 總檢查數：42
- 結果統計：PASS 37，WARN 2，FAIL 3

## 主要問題

1. PASS | 1688牛革製の細いベルト、女性用スカートの装飾、シンプルなスーツ用本革ベルト、女性用アクセサリー、高級感、越境配送 14.00 CNY
   URL: https://main-b2b.hubbuyer.com/jp/products/cowhide-thin-belt-for-women-simple-decorative-belt-for-dresses-genuine-leather-belt-for-women-high-end-accessory-cross-border-shipping-643468030315
   HTTP: 200 | blank: no | console: 0 | pageError: 0
   
2. PASS | (no text)
   URL: https://main-b2b.hubbuyer.com/jp/products/proea-baloui-5280-men-s-pure-cotton-boxer-briefs-combed-cotton-u-convex-single-layer-breathable-wide-side-two-pack-542525759859
   HTTP: 200 | blank: no | console: 0 | pageError: 0
   
3. PASS | (no text)
   URL: https://main-b2b.hubbuyer.com/jp/products/men-s-underwear-men-s-boxer-briefs-ice-mesh-summer-youth-sports-comfortable-breathable-boxer-shorts-649531397559
   HTTP: 200 | blank: no | console: 0 | pageError: 0
   
4. PASS | (no text)
   URL: https://main-b2b.hubbuyer.com/jp/products/cleaning-suit-15-piece-set-cleaning-car-tools-interior-wheel-paint-surface-cleaning-with-storage-tool-box-889373058335
   HTTP: 200 | blank: no | console: 0 | pageError: 0
   
5. FAIL | 搜尋：輸入「ペット餌入れ器」後點擊検索
   URL: https://main-b2b.hubbuyer.com/jp
   HTTP: 200 | blank: no | console: 0 | pageError: 0
   navError: locator.fill: Timeout 30000ms exceeded. Call log: [2m - waiting for locator('input').first()[22m [2m - locator resolved to <input value="" type="text" tabindex="0" role="combobox" autocomplete="off" spellcheck="false" id="el-id-1024-216" aria-expanded="false" aria-haspopup="listbox" class="el-select__input" aria-activedescendant="" aria-autocomplete="none
6. FAIL | 會員入口：会員登録
   URL: https://main-auth.hubbuyer.com/jump_common?jump_data=%7B%22jump_source_url%22%3A%22https%3A%2F%2Fmain-b2b.hubbuyer.com%2Fjp%22%2C%22jump_site%22%3A%22B2B%22%2C%22token%22%3A%22%22%2C%22jump_go_url%22%3A%22%2Fsign%2Fup%22%2C%22nation_key%22%3A%22Japan%22%2C%22language_key%22%3A%22japanese%22%2C%22language_val%22%3A%22%22%7D
   HTTP: 200 | blank: yes | console: 0 | pageError: 0
   
7. WARN | 會員入口：ログイン
   URL: https://main-b2b.hubbuyer.com/jp
   HTTP: 200 | blank: no | console: 0 | pageError: 0
   
8. WARN | 服務入口：OEM
   URL: https://main-b2b.hubbuyer.com/jp
   HTTP: 200 | blank: no | console: 1 | pageError: 0
   
9. FAIL | さらに表示按鈕 #1
   URL: https://main-b2b.hubbuyer.com/jp
   HTTP: 200 | blank: no | console: 2 | pageError: 0
   navError: locator.click: Timeout 5000ms exceeded. Call log: [2m - waiting for locator('button').nth(2)[22m [2m - locator resolved to <button type="button" aria-label="Carousel arrow right" class="el-carousel__arrow el-carousel__arrow--right">…</button>[22m [2m - attempting click action[22m [2m 2 × waiting for element to be visible, enabled and stable[22m [2m 
10. PASS | さらに表示按鈕 #6
   URL: https://main-auth.hubbuyer.com/sign/up
   HTTP: 200 | blank: no | console: 0 | pageError: 0
   

## 按鈕/互動入口結果

| 結果 | 入口 | 行為 | HTTP | 最終 URL |
|---|---|---|---|---|
| FAIL | 搜尋：輸入「ペット餌入れ器」後點擊検索 | 頁內變化/彈窗 | 200 | https://main-b2b.hubbuyer.com/jp |
| PASS | 圖片搜尋：画像検索 | 頁內變化/彈窗 | 200 | https://main-b2b.hubbuyer.com/jp |
| PASS | 購物車：カート | 頁內變化/彈窗 | 200 | https://main-b2b.hubbuyer.com/jp |
| PASS | 分類：カテゴリー | 頁內變化/彈窗 | 200 | https://main-b2b.hubbuyer.com/jp |
| PASS | 上方導覽：(B2B)ご利用ガイド | 頁內變化/彈窗 | 200 | https://main-b2b.hubbuyer.com/jp |
| PASS | 上方導覽：(B2B)サービス/料金 | 頁內變化/彈窗 | 200 | https://main-b2b.hubbuyer.com/jp |
| PASS | 上方導覽：(B2B)国際送料 | 頁內變化/彈窗 | 200 | https://main-b2b.hubbuyer.com/jp |
| PASS | 上方導覽：Blog | 頁內變化/彈窗 | 200 | https://main-b2b.hubbuyer.com/jp |
| PASS | 上方導覽：よくある質問 | 頁內變化/彈窗 | 200 | https://main-b2b.hubbuyer.com/jp |
| PASS | 商品 Tab：Amazon新品 | 頁內變化/彈窗 | 200 | https://main-b2b.hubbuyer.com/jp |
| PASS | 商品 Tab：Amazon人気 | 頁內變化/彈窗 | 200 | https://main-b2b.hubbuyer.com/jp |
| PASS | 商品 Tab：1688売れ筋 | 頁內變化/彈窗 | 200 | https://main-b2b.hubbuyer.com/jp |
| FAIL | 會員入口：会員登録 | 有跳轉 | 200 | https://main-auth.hubbuyer.com/jump_common?jump_data=%7B%22jump_source_url%22%3A%22https%3A%2F%2Fmain-b2b.hubbuyer.com%2Fjp%22%2C%22jump_site%22%3A%22B2B%22%2C%22token%22%3A%22%22%2C%22jump_go_url%22%3A%22%2Fsign%2Fup%22%2C%22nation_key%22%3A%22Japan%22%2C%22language_key%22%3A%22japanese%22%2C%22language_val%22%3A%22%22%7D |
| WARN | 會員入口：ログイン | 未找到/未點擊 | 200 | https://main-b2b.hubbuyer.com/jp |
| PASS | 服務入口：1688越境アシスタント | 頁內變化/彈窗 | 200 | https://main-b2b.hubbuyer.com/jp |
| PASS | 服務入口：拡張機能 | 頁內變化/彈窗 | 200 | https://main-b2b.hubbuyer.com/jp |
| WARN | 服務入口：OEM | 頁內變化/彈窗 | 200 | https://main-b2b.hubbuyer.com/jp |
| PASS | 服務入口：D2C | 頁內變化/彈窗 | 200 | https://main-b2b.hubbuyer.com/jp |
| FAIL | さらに表示按鈕 #1 | 頁內變化/彈窗 | 200 | https://main-b2b.hubbuyer.com/jp |
| PASS | さらに表示按鈕 #2 | 頁內變化/彈窗 | 200 | https://main-b2b.hubbuyer.com/jp |
| PASS | さらに表示按鈕 #3 | 頁內變化/彈窗 | 200 | https://main-b2b.hubbuyer.com/jp |
| PASS | さらに表示按鈕 #4 | 頁內變化/彈窗 | 200 | https://main-b2b.hubbuyer.com/jp |
| PASS | さらに表示按鈕 #5 | 頁內變化/彈窗 | 200 | https://main-b2b.hubbuyer.com/jp |
| PASS | さらに表示按鈕 #6 | 有跳轉 | 200 | https://main-auth.hubbuyer.com/sign/up |

## 限制

本次自動化瀏覽器未使用截圖中的已登入 Chrome 會話，因此「會員中心/我的足跡/收藏/收貨地址」等登入後專屬快捷入口未覆蓋；若要覆蓋，需要可自動化登入態或測試帳號。

完整 JSON：D:/test_workspace/测试项目/工单改造/测试文档/hubbuyer_b2b_page_check_2026-07-16.json
