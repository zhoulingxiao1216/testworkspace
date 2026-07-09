// Hubbuyer 1688 女装商品素材快速入口。
// 页面设计/商品卡片填充时优先引用本文件，避免反复读取大截图、渲染 HTML 和分散 JSON。
const HUBBUYER_FAST_PRODUCT_DATA = {
    "schema":  "hubbuyer-fast-product-data/v1",
    "purpose":  "页面设计和商品卡片填充的单文件快速入口；默认只读本文件即可，不需要再扫描 rendered.html、rendered.png、images.json 等原始采集文件。",
    "generatedAt":  "2026-06-09",
    "source":  {
                   "page":  "Hubbuyer 1688 女装列表页",
                   "url":  "https://b2b.hubbuyer.com/Alibaba/list?key=%E5%A5%B3%E8%A3%85",
                   "fetchedAt":  "2026-06-08 13:26:23",
                   "platform":  "1688",
                   "keyword":  "女装",
                   "originalProductCount":  50,
                   "productImageCount":  50
               },
    "usage":  {
                  "browserGlobal":  "window.HUBBUYER_FAST_PRODUCT_DATA",
                  "recommendedProducts":  "products.slice(0, 30)",
                  "primaryTitleField":  "displayTitle",
                  "primaryImageField":  "image",
                  "note":  "前 30 条包含当前商品列表页已整理过的中文标题；第 31-50 条保留抓取到的英文标题，可按需补充中文文案。"
              },
    "products":  [
                     {
                         "id":  "hb1688-women-001",
                         "source":  "1688",
                         "title":  "Cross-Border Round Neck Small Camisole Women\u0027s Suit Inner Wear Sleeveless Bottoming Shirt French Top 2025 Summer Summer",
                         "titleZh":  "跨境圆领小吊带女装套装内搭无袖打底衫 法式上衣 2025夏季",
                         "displayTitle":  "跨境圆领小吊带女装套装内搭无袖打底衫 法式上衣 2025夏季",
                         "image":  "https://cbu01.alicdn.com/img/ibank/O1CN01xipDyx1GtUFbt6igl_!!2208107370680-0-cib.jpg_400x400.jpg_.webp",
                         "price":  {
                                       "cny":  14.00,
                                       "cnyText":  "14.00 CNY",
                                       "eur":  1.82,
                                       "eurText":  "1.82 EUR"
                                   },
                         "monthlySales":  222,
                         "monthlySalesText":  "222",
                         "repurchaseRate":  30.56,
                         "repurchaseRateText":  "30.56%"
                     },
                     {
                         "id":  "hb1688-women-002",
                         "source":  "1688",
                         "title":  "2025 European and American Cross-Border Autumn and Winter Women\u0027s Clothing Amazon Furry Long-Sleeved Lapel Women\u0027s Plush Top Long Coat",
                         "titleZh":  "2025欧美跨境秋冬女装 亚马逊毛绒长袖翻领上衣 长款外套",
                         "displayTitle":  "2025欧美跨境秋冬女装 亚马逊毛绒长袖翻领上衣 长款外套",
                         "image":  "https://cbu01.alicdn.com/img/ibank/O1CN01cPMTU826XN0PwNZ5l_!!2206619717671-0-cib.jpg_400x400.jpg_.webp",
                         "price":  {
                                       "cny":  48.00,
                                       "cnyText":  "48.00 CNY",
                                       "eur":  6.24,
                                       "eurText":  "6.24 EUR"
                                   },
                         "monthlySales":  380,
                         "monthlySalesText":  "380",
                         "repurchaseRate":  33.33,
                         "repurchaseRateText":  "33.33%"
                     },
                     {
                         "id":  "hb1688-women-003",
                         "source":  "1688",
                         "title":  "2026 Summer New European and American Style Round Neck Solid Color Tank Top with Built-In Bra, Sexy Women\u0027s Base Layer Top for Inner Wear or Outer Wear",
                         "titleZh":  "2026夏季欧美新款圆领纯色带胸垫背心 性感女式内外穿打底上衣",
                         "displayTitle":  "2026夏季欧美新款圆领纯色带胸垫背心 性感女式内外穿打底上衣",
                         "image":  "https://cbu01.alicdn.com/img/ibank/O1CN01IcXKwS1M3Au7j6VUj_!!2220911641378-0-cib.jpg_400x400.jpg_.webp",
                         "price":  {
                                       "cny":  16.50,
                                       "cnyText":  "16.50 CNY",
                                       "eur":  2.15,
                                       "eurText":  "2.15 EUR"
                                   },
                         "monthlySales":  6969,
                         "monthlySalesText":  "6,969",
                         "repurchaseRate":  44.44,
                         "repurchaseRateText":  "44.44%"
                     },
                     {
                         "id":  "hb1688-women-004",
                         "source":  "1688",
                         "title":  "Modal Small Camisole Women\u0027s Inner Wear Beautiful Back Summer Thin Sexy Outer Wear Pure Desire Style Base Black Top",
                         "titleZh":  "莫代尔小吊带女内搭 美背夏季薄款性感外穿 纯欲风黑色打底上衣",
                         "displayTitle":  "莫代尔小吊带女内搭 美背夏季薄款性感外穿 纯欲风黑色打底上衣",
                         "image":  "https://cbu01.alicdn.com/img/ibank/O1CN01DvHZ7U27bmboRXkhZ_!!2217933777816-0-cib.jpg_400x400.jpg_.webp",
                         "price":  {
                                       "cny":  5.70,
                                       "cnyText":  "5.70 CNY",
                                       "eur":  0.74,
                                       "eurText":  "0.74 EUR"
                                   },
                         "monthlySales":  1599,
                         "monthlySalesText":  "1,599",
                         "repurchaseRate":  9.71,
                         "repurchaseRateText":  "9.71%"
                     },
                     {
                         "id":  "hb1688-women-005",
                         "source":  "1688",
                         "title":  "Summer Fresh Cotton Camisole Design Sense Pleated Inner Lap with Chest Pad Outer Wear Slimming Beautiful Back Top for Women",
                         "titleZh":  "夏季清新棉质吊带 设计感褶皱带胸垫外穿 修身美背女上衣",
                         "displayTitle":  "夏季清新棉质吊带 设计感褶皱带胸垫外穿 修身美背女上衣",
                         "image":  "https://cbu01.alicdn.com/img/ibank/O1CN01XSD2qq2EDEm6zKpuT_!!2214234288710-0-cib.jpg_400x400.jpg_.webp",
                         "price":  {
                                       "cny":  11.00,
                                       "cnyText":  "11.00 CNY",
                                       "eur":  1.43,
                                       "eurText":  "1.43 EUR"
                                   },
                         "monthlySales":  3443,
                         "monthlySalesText":  "3,443",
                         "repurchaseRate":  8.67,
                         "repurchaseRateText":  "8.67%"
                     },
                     {
                         "id":  "hb1688-women-006",
                         "source":  "1688",
                         "title":  "Modal Round Neck Camisole Women\u0027s Summer Chest Pad Inner Base All-match Solid Color Sleeveless Large Size Thin Top",
                         "titleZh":  "莫代尔圆领吊带女夏季带胸垫内搭 百搭纯色无袖大码薄款上衣",
                         "displayTitle":  "莫代尔圆领吊带女夏季带胸垫内搭 百搭纯色无袖大码薄款上衣",
                         "image":  "https://cbu01.alicdn.com/img/ibank/O1CN01G7r2al1c1MuqqYqdO_!!2200583743540-0-cib.jpg_400x400.jpg_.webp",
                         "price":  {
                                       "cny":  14.90,
                                       "cnyText":  "14.90 CNY",
                                       "eur":  1.94,
                                       "eurText":  "1.94 EUR"
                                   },
                         "monthlySales":  363,
                         "monthlySalesText":  "363",
                         "repurchaseRate":  14.41,
                         "repurchaseRateText":  "14.41%"
                     },
                     {
                         "id":  "hb1688-women-007",
                         "source":  "1688",
                         "title":  "Spring and Summer I-shaped Pure Cotton Vest Women\u0027s One-character Collar Hanging Neck Slimming Inner Thread Sleeveless Base Shirt Sling Top",
                         "titleZh":  "春夏 I 字纯棉背心女 一字领挂脖修身内螺纹无袖打底吊带",
                         "displayTitle":  "春夏 I 字纯棉背心女 一字领挂脖修身内螺纹无袖打底吊带",
                         "image":  "https://cbu01.alicdn.com/img/ibank/O1CN01oI0YKC1Jjoqvj6xiM_!!2208339921065-0-cib.jpg_400x400.jpg_.webp",
                         "price":  {
                                       "cny":  19.90,
                                       "cnyText":  "19.90 CNY",
                                       "eur":  2.59,
                                       "eurText":  "2.59 EUR"
                                   },
                         "monthlySales":  892,
                         "monthlySalesText":  "892",
                         "repurchaseRate":  14.56,
                         "repurchaseRateText":  "14.56%"
                     },
                     {
                         "id":  "hb1688-women-008",
                         "source":  "1688",
                         "title":  "All-match anti-slip sleeveless thin bottoming camisole women\u0027s summer stretch slim-fit slimming Korean-style exterior wear",
                         "titleZh":  "百搭防滑无袖薄款打底吊带 女夏季弹力修身显瘦韩版外穿",
                         "displayTitle":  "百搭防滑无袖薄款打底吊带 女夏季弹力修身显瘦韩版外穿",
                         "image":  "https://cbu01.alicdn.com/img/ibank/O1CN01Lku0bv1bHZQbzJghQ_!!3463703440-0-cib.jpg_400x400.jpg_.webp",
                         "price":  {
                                       "cny":  5.90,
                                       "cnyText":  "5.90 CNY",
                                       "eur":  0.77,
                                       "eurText":  "0.77 EUR"
                                   },
                         "monthlySales":  10961,
                         "monthlySalesText":  "10,961",
                         "repurchaseRate":  20.34,
                         "repurchaseRateText":  "20.34%"
                     },
                     {
                         "id":  "hb1688-women-009",
                         "source":  "1688",
                         "title":  "Tang Ge Silk Satin Beautiful Back Short Sling French Triangular Cup Mulberry Silk Underwear No Wires Silk Bra",
                         "titleZh":  "唐阁真丝缎面美背短吊带 法式三角杯桑蚕丝无钢圈丝绸文胸",
                         "displayTitle":  "唐阁真丝缎面美背短吊带 法式三角杯桑蚕丝无钢圈丝绸文胸",
                         "image":  "https://cbu01.alicdn.com/img/ibank/O1CN01VFuNsf2Bdqg8HqGLe_!!2386038362-0-cib.jpg_400x400.jpg_.webp",
                         "price":  {
                                       "cny":  59.00,
                                       "cnyText":  "59.00 CNY",
                                       "eur":  7.67,
                                       "eurText":  "7.67 EUR"
                                   },
                         "monthlySales":  1741,
                         "monthlySalesText":  "1,741",
                         "repurchaseRate":  23.47,
                         "repurchaseRateText":  "23.47%"
                     },
                     {
                         "id":  "hb1688-women-010",
                         "source":  "1688",
                         "title":  "Eyelash Lace Camisole Women\u0027s Summer All-match Silk Satin Suit Inner Top Silk Beautiful Back Base Shirt",
                         "titleZh":  "睫毛蕾丝吊带女夏季百搭丝缎西装内搭 真丝美背打底衫",
                         "displayTitle":  "睫毛蕾丝吊带女夏季百搭丝缎西装内搭 真丝美背打底衫",
                         "image":  "https://cbu01.alicdn.com/img/ibank/15279874000_2100428301.jpg_400x400.jpg_.webp",
                         "price":  {
                                       "cny":  17.95,
                                       "cnyText":  "17.95 CNY",
                                       "eur":  2.33,
                                       "eurText":  "2.33 EUR"
                                   },
                         "monthlySales":  399,
                         "monthlySalesText":  "399",
                         "repurchaseRate":  35.71,
                         "repurchaseRateText":  "35.71%"
                     },
                     {
                         "id":  "hb1688-women-011",
                         "source":  "1688",
                         "title":  "2025 Summer European and American New Style Solid Color Tank Top with Built-In Bra, Sexy Women\u0027s Undershirt for Layering or Wearing Alone",
                         "titleZh":  "2025夏季欧美新款纯色带胸垫背心 性感女式内搭/单穿上衣",
                         "displayTitle":  "2025夏季欧美新款纯色带胸垫背心 性感女式内搭/单穿上衣",
                         "image":  "https://cbu01.alicdn.com/img/ibank/O1CN01JzRTEe1nW1JLy6JhI_!!4001835096-0-cib.jpg_400x400.jpg_.webp",
                         "price":  {
                                       "cny":  20.00,
                                       "cnyText":  "20.00 CNY",
                                       "eur":  2.60,
                                       "eurText":  "2.60 EUR"
                                   },
                         "monthlySales":  8287,
                         "monthlySalesText":  "8,287",
                         "repurchaseRate":  47.19,
                         "repurchaseRateText":  "47.19%"
                     },
                     {
                         "id":  "hb1688-women-012",
                         "source":  "1688",
                         "title":  "銆?A Antibacterial Lyocell銆慍ooling Camisole with Chest Pads for Women, Suitable for Outerwear, Plus Size, Inner Wear, Beautiful Back Design, White Top",
                         "titleZh":  "A类抗菌莱赛尔凉感吊带带胸垫女 外穿大码内搭美背白色上衣",
                         "displayTitle":  "A类抗菌莱赛尔凉感吊带带胸垫女 外穿大码内搭美背白色上衣",
                         "image":  "https://cbu01.alicdn.com/img/ibank/O1CN012JnUvq1urHAhppU2K_!!3869706090-0-cib.jpg_400x400.jpg_.webp",
                         "price":  {
                                       "cny":  39.00,
                                       "cnyText":  "39.00 CNY",
                                       "eur":  5.07,
                                       "eurText":  "5.07 EUR"
                                   },
                         "monthlySales":  2484,
                         "monthlySalesText":  "2,484",
                         "repurchaseRate":  5.51,
                         "repurchaseRateText":  "5.51%"
                     },
                     {
                         "id":  "hb1688-women-013",
                         "source":  "1688",
                         "title":  "Cross-Border Foreign Trade Pure Desire Polka Dot Hottie Halter Neck Camisole Women\u0027s Summer Sexy Tie-Up Slim Fit Top",
                         "titleZh":  "跨境外贸纯欲波点辣妹挂脖吊带 女夏季性感系带修身上衣",
                         "displayTitle":  "跨境外贸纯欲波点辣妹挂脖吊带 女夏季性感系带修身上衣",
                         "image":  "https://cbu01.alicdn.com/img/ibank/O1CN01RORKoh1jp1Qdtb9Fg_!!2218022494596-0-cib.jpg_400x400.jpg_.webp",
                         "price":  {
                                       "cny":  20.90,
                                       "cnyText":  "20.90 CNY",
                                       "eur":  2.72,
                                       "eurText":  "2.72 EUR"
                                   },
                         "monthlySales":  343,
                         "monthlySalesText":  "343",
                         "repurchaseRate":  23.64,
                         "repurchaseRateText":  "23.64%"
                     },
                     {
                         "id":  "hb1688-women-014",
                         "source":  "1688",
                         "title":  "92 Cotton Blue Shoulder Short-sleeved T-shirt Women\u0027s Summer Slim-fit Slimming Western-style Pleated Waist Short T-shirt Top",
                         "titleZh":  "92棉蓝肩短袖T恤女夏季修身显瘦 洋气褶皱收腰短款上衣",
                         "displayTitle":  "92棉蓝肩短袖T恤女夏季修身显瘦 洋气褶皱收腰短款上衣",
                         "image":  "https://cbu01.alicdn.com/img/ibank/O1CN01JNdnIT1VI8IvPPfn7_!!2201423292629-0-cib.jpg_400x400.jpg_.webp",
                         "price":  {
                                       "cny":  15.50,
                                       "cnyText":  "15.50 CNY",
                                       "eur":  2.02,
                                       "eurText":  "2.02 EUR"
                                   },
                         "monthlySales":  1694,
                         "monthlySalesText":  "1,694",
                         "repurchaseRate":  11.15,
                         "repurchaseRateText":  "11.15%"
                     },
                     {
                         "id":  "hb1688-women-015",
                         "source":  "1688",
                         "title":  "American-Style Spicy Girl Tank Top for Women, Summer Slim-Fit Outerwear, New Sleeveless Racerback Inner Camisole Top",
                         "titleZh":  "美式辣妹背心女夏季修身外穿 新款无袖工字内搭吊带上衣",
                         "displayTitle":  "美式辣妹背心女夏季修身外穿 新款无袖工字内搭吊带上衣",
                         "image":  "https://cbu01.alicdn.com/img/ibank/O1CN01G1cAds2Jzqz42y7As_!!2206789229493-0-cib.jpg_400x400.jpg_.webp",
                         "price":  {
                                       "cny":  17.20,
                                       "cnyText":  "17.20 CNY",
                                       "eur":  2.24,
                                       "eurText":  "2.24 EUR"
                                   },
                         "monthlySales":  306,
                         "monthlySalesText":  "306",
                         "repurchaseRate":  6.15,
                         "repurchaseRateText":  "6.15%"
                     },
                     {
                         "id":  "hb1688-women-016",
                         "source":  "1688",
                         "title":  "One-Shoulder Ice Silk Without Breast Pad Small Camisole Women\u0027s Thin Inner Wear Beautiful Back Intimates Women\u0027s Anti-Exposure Wrapped Tube Top",
                         "titleZh":  "单肩冰丝无胸垫小吊带 女薄款内搭美背防走光裹胸抹胸",
                         "displayTitle":  "单肩冰丝无胸垫小吊带 女薄款内搭美背防走光裹胸抹胸",
                         "image":  "https://cbu01.alicdn.com/img/ibank/O1CN01lxbxTm1SVvC5JuhIj_!!2213207952253-0-cib.jpg_400x400.jpg_.webp",
                         "price":  {
                                       "cny":  6.50,
                                       "cnyText":  "6.50 CNY",
                                       "eur":  0.84,
                                       "eurText":  "0.84 EUR"
                                   },
                         "monthlySales":  445,
                         "monthlySalesText":  "445",
                         "repurchaseRate":  7.61,
                         "repurchaseRateText":  "7.61%"
                     },
                     {
                         "id":  "hb1688-women-017",
                         "source":  "1688",
                         "title":  "One-Shoulder Camisole for Outerwear, Sleeveless Top That Covers Side Breasts, Slim Fit, Beautiful Back, Sports Inner Wear, Fashionable Camisole",
                         "titleZh":  "单肩外穿吊带 无袖包副乳修身美背 运动内搭时尚背心",
                         "displayTitle":  "单肩外穿吊带 无袖包副乳修身美背 运动内搭时尚背心",
                         "image":  "https://cbu01.alicdn.com/img/ibank/O1CN01vwL9011rZ0WXYk1Zd_!!2218942625644-0-cib.jpg_400x400.jpg_.webp",
                         "price":  {
                                       "cny":  6.00,
                                       "cnyText":  "6.00 CNY",
                                       "eur":  0.78,
                                       "eurText":  "0.78 EUR"
                                   },
                         "monthlySales":  7642,
                         "monthlySalesText":  "7,642",
                         "repurchaseRate":  25.51,
                         "repurchaseRateText":  "25.51%"
                     },
                     {
                         "id":  "hb1688-women-018",
                         "source":  "1688",
                         "title":  "Women\u0027s Short-Sleeved Modal Bottoming Shirt with Breast Pads, Women\u0027s Spring and Summer All-In-One Pajamas, Five-Finger Half-Sleeved Women\u0027s Clothing",
                         "titleZh":  "女士短袖莫代尔带胸垫打底衫 春夏一体式居家五分袖上衣",
                         "displayTitle":  "女士短袖莫代尔带胸垫打底衫 春夏一体式居家五分袖上衣",
                         "image":  "https://cbu01.alicdn.com/img/ibank/O1CN01DSN9II1JtRFs9XOCx_!!2214740401086-0-cib.jpg_400x400.jpg_.webp",
                         "price":  {
                                       "cny":  19.49,
                                       "cnyText":  "19.49 CNY",
                                       "eur":  2.53,
                                       "eurText":  "2.53 EUR"
                                   },
                         "monthlySales":  1859,
                         "monthlySalesText":  "1,859",
                         "repurchaseRate":  6.67,
                         "repurchaseRateText":  "6.67%"
                     },
                     {
                         "id":  "hb1688-women-019",
                         "source":  "1688",
                         "title":  "[Factory Outlet] Solid Color Large Neckline Short Sleeve T-Shirt Women\u0027s Loose Casual Slimming V-neck Base Shirt Fashion Brand",
                         "titleZh":  "[工厂直销] 纯色大领口短袖T恤女 宽松休闲显瘦V领打底衫",
                         "displayTitle":  "[工厂直销] 纯色大领口短袖T恤女 宽松休闲显瘦V领打底衫",
                         "image":  "https://cbu01.alicdn.com/img/ibank/O1CN01QZkrGZ2KyJAa4OpAs_!!2211405079625-0-cib.jpg_400x400.jpg_.webp",
                         "price":  {
                                       "cny":  7.80,
                                       "cnyText":  "7.80 CNY",
                                       "eur":  1.01,
                                       "eurText":  "1.01 EUR"
                                   },
                         "monthlySales":  6239,
                         "monthlySalesText":  "6,239",
                         "repurchaseRate":  19.06,
                         "repurchaseRateText":  "19.06%"
                     },
                     {
                         "id":  "hb1688-women-020",
                         "source":  "1688",
                         "title":  "Spring and Summer Women\u0027s Bottoming Vest Pure Cotton Round Neck High Elastic Breathable Breast Reduction High School Girls Wear Outside and Inside Vest",
                         "titleZh":  "春夏女士打底背心 纯棉圆领高弹透气显小胸 中学生内外穿背心",
                         "displayTitle":  "春夏女士打底背心 纯棉圆领高弹透气显小胸 中学生内外穿背心",
                         "image":  "https://cbu01.alicdn.com/img/ibank/O1CN01auKiNs1cMR6r5v0I7_!!2215290253586-0-cib.jpg_400x400.jpg_.webp",
                         "price":  {
                                       "cny":  13.00,
                                       "cnyText":  "13.00 CNY",
                                       "eur":  1.69,
                                       "eurText":  "1.69 EUR"
                                   },
                         "monthlySales":  323,
                         "monthlySalesText":  "323",
                         "repurchaseRate":  28.57,
                         "repurchaseRateText":  "28.57%"
                     },
                     {
                         "id":  "hb1688-women-021",
                         "source":  "1688",
                         "title":  "Bm Style American Hot Girl Solid Color Six-Button Tank Top, Slim Fit Outerwear Cotton Top for Women",
                         "titleZh":  "BM风美式辣妹纯色六粒扣背心 修身外穿棉质女上衣",
                         "displayTitle":  "BM风美式辣妹纯色六粒扣背心 修身外穿棉质女上衣",
                         "image":  "https://cbu01.alicdn.com/img/ibank/O1CN01dY1RdH2LuTZ72dzYO_!!2218132009752-0-cib.jpg_400x400.jpg_.webp",
                         "price":  {
                                       "cny":  38.00,
                                       "cnyText":  "38.00 CNY",
                                       "eur":  4.94,
                                       "eurText":  "4.94 EUR"
                                   },
                         "monthlySales":  252,
                         "monthlySalesText":  "252",
                         "repurchaseRate":  5.65,
                         "repurchaseRateText":  "5.65%"
                     },
                     {
                         "id":  "hb1688-women-022",
                         "source":  "1688",
                         "title":  "Modal Camisole Women\u0027s Summer Thin Inner Sleeveless Base Large Size Loose Slim Top for Chubby Girls",
                         "titleZh":  "莫代尔吊带女夏季薄款内搭 无袖打底大码宽松显瘦上衣",
                         "displayTitle":  "莫代尔吊带女夏季薄款内搭 无袖打底大码宽松显瘦上衣",
                         "image":  "https://cbu01.alicdn.com/img/ibank/O1CN01ifgMB71bNypljpohR_!!2215422913454-0-cib.jpg_400x400.jpg_.webp",
                         "price":  {
                                       "cny":  9.00,
                                       "cnyText":  "9.00 CNY",
                                       "eur":  1.17,
                                       "eurText":  "1.17 EUR"
                                   },
                         "monthlySales":  876,
                         "monthlySalesText":  "876",
                         "repurchaseRate":  4.98,
                         "repurchaseRateText":  "4.98%"
                     },
                     {
                         "id":  "hb1688-women-023",
                         "source":  "1688",
                         "title":  "in stock Lyocell Tencel Linen Cotton Button Outer Wear Inner Vest Korean All-match Comfortable Slim-fit Clavicle-exposed Sling",
                         "titleZh":  "现货莱赛尔天丝麻棉扣子外穿内搭背心 韩版百搭舒适修身露锁骨吊带",
                         "displayTitle":  "现货莱赛尔天丝麻棉扣子外穿内搭背心 韩版百搭舒适修身露锁骨吊带",
                         "image":  "https://cbu01.alicdn.com/img/ibank/O1CN01MMQRn62ACXnvYmSPS_!!2214659628167-0-cib.jpg_400x400.jpg_.webp",
                         "price":  {
                                       "cny":  28.00,
                                       "cnyText":  "28.00 CNY",
                                       "eur":  3.64,
                                       "eurText":  "3.64 EUR"
                                   },
                         "monthlySales":  456,
                         "monthlySalesText":  "456",
                         "repurchaseRate":  7.73,
                         "repurchaseRateText":  "7.73%"
                     },
                     {
                         "id":  "hb1688-women-024",
                         "source":  "1688",
                         "title":  "Love T-Shirt for Women Pure Cotton Kawasaki Heart T-Shirt for Men Play Baby Little Red Heart Baaling Short-Sleeved Family Couple Wear",
                         "titleZh":  "爱心T恤女纯棉川崎红心短袖 男女情侣亲子款",
                         "displayTitle":  "爱心T恤女纯棉川崎红心短袖 男女情侣亲子款",
                         "image":  "https://cbu01.alicdn.com/i1/6000000006256/O1CN01SEPql31w5IvR0gNFC_!!6000000006256-0-1688ciroom.jpg_400x400.jpg_.webp",
                         "price":  {
                                       "cny":  25.00,
                                       "cnyText":  "25.00 CNY",
                                       "eur":  3.25,
                                       "eurText":  "3.25 EUR"
                                   },
                         "monthlySales":  160,
                         "monthlySalesText":  "160",
                         "repurchaseRate":  23.08,
                         "repurchaseRateText":  "23.08%"
                     },
                     {
                         "id":  "hb1688-women-025",
                         "source":  "1688",
                         "title":  "Cross-border European and American Foreign Trade Strapless Women\u0027s Inner Wearing Pure Spice Girl Top Summer Outer Wearing Pullover Vest Slim-fit Women\u0027s Clothing",
                         "titleZh":  "跨境欧美外贸抹胸女内搭 纯欲辣妹夏季外穿套头修身背心",
                         "displayTitle":  "跨境欧美外贸抹胸女内搭 纯欲辣妹夏季外穿套头修身背心",
                         "image":  "https://cbu01.alicdn.com/img/ibank/O1CN01tnW2nn1iIDHAJagJ2_!!2216866664389-0-cib.jpg_400x400.jpg_.webp",
                         "price":  {
                                       "cny":  7.50,
                                       "cnyText":  "7.50 CNY",
                                       "eur":  0.98,
                                       "eurText":  "0.98 EUR"
                                   },
                         "monthlySales":  3295,
                         "monthlySalesText":  "3,295",
                         "repurchaseRate":  28.93,
                         "repurchaseRateText":  "28.93%"
                     },
                     {
                         "id":  "hb1688-women-026",
                         "source":  "1688",
                         "title":  "Oil painting jacket women\u0027s summer new seaside vacation hot girl hanging neck strap small vest short small jacket wholesale",
                         "titleZh":  "油画风小上衣 女夏季海边度假辣妹挂脖吊带短款背心批发",
                         "displayTitle":  "油画风小上衣 女夏季海边度假辣妹挂脖吊带短款背心批发",
                         "image":  "https://cbu01.alicdn.com/img/ibank/O1CN01c5xpDa224jyMZayLG_!!3172677067-0-cib.jpg_400x400.jpg_.webp",
                         "price":  {
                                       "cny":  15.50,
                                       "cnyText":  "15.50 CNY",
                                       "eur":  2.02,
                                       "eurText":  "2.02 EUR"
                                   },
                         "monthlySales":  1007,
                         "monthlySalesText":  "1,007",
                         "repurchaseRate":  18.56,
                         "repurchaseRateText":  "18.56%"
                     },
                     {
                         "id":  "hb1688-women-027",
                         "source":  "1688",
                         "title":  "Shake Tone Same Summer Pure Spice Girl Thick Coaster Small Chest Large Camisole Women Slim All-match Underwear Top",
                         "titleZh":  "抖音同款夏季纯欲辣妹厚胸垫小胸大码吊带 女修身百搭内衣上衣",
                         "displayTitle":  "抖音同款夏季纯欲辣妹厚胸垫小胸大码吊带 女修身百搭内衣上衣",
                         "image":  "https://cbu01.alicdn.com/img/ibank/O1CN01WOJV3r1g3tlDF4QMO_!!2213942184087-0-cib.jpg_400x400.jpg_.webp",
                         "price":  {
                                       "cny":  8.50,
                                       "cnyText":  "8.50 CNY",
                                       "eur":  1.10,
                                       "eurText":  "1.10 EUR"
                                   },
                         "monthlySales":  1999,
                         "monthlySalesText":  "1,999",
                         "repurchaseRate":  25.93,
                         "repurchaseRateText":  "25.93%"
                     },
                     {
                         "id":  "hb1688-women-028",
                         "source":  "1688",
                         "title":  "European Station French Design Sense Mesh Lace Plastic Beautiful Back Underwear Spice Girl Fish Bone Tube Chest Women\u0027s Thin",
                         "titleZh":  "欧站法式设计感网纱蕾丝塑形美背内衣 辣妹鱼骨抹胸女薄款",
                         "displayTitle":  "欧站法式设计感网纱蕾丝塑形美背内衣 辣妹鱼骨抹胸女薄款",
                         "image":  "https://cbu01.alicdn.com/img/ibank/O1CN016qI1Xo1LfM98R23G7_!!2206526631326-0-cib.jpg_400x400.jpg_.webp",
                         "price":  {
                                       "cny":  31.00,
                                       "cnyText":  "31.00 CNY",
                                       "eur":  4.03,
                                       "eurText":  "4.03 EUR"
                                   },
                         "monthlySales":  248,
                         "monthlySalesText":  "248",
                         "repurchaseRate":  45.45,
                         "repurchaseRateText":  "45.45%"
                     },
                     {
                         "id":  "hb1688-women-029",
                         "source":  "1688",
                         "title":  "Purely Sexy Camisole for Women with Breast Pads, Versatile and Slim-Fitting, Can Be Worn Outside or as an Inner Layer, with a Beautiful Back Design, Sleeveless Top for Summer",
                         "titleZh":  "纯欲性感带胸垫吊带女 百搭修身内外穿 美背无袖夏季上衣",
                         "displayTitle":  "纯欲性感带胸垫吊带女 百搭修身内外穿 美背无袖夏季上衣",
                         "image":  "https://cbu01.alicdn.com/img/ibank/O1CN01IpluYA1kV9sWU1Dfn_!!2208236424688-0-cib.jpg_400x400.jpg_.webp",
                         "price":  {
                                       "cny":  7.88,
                                       "cnyText":  "7.88 CNY",
                                       "eur":  1.02,
                                       "eurText":  "1.02 EUR"
                                   },
                         "monthlySales":  2142,
                         "monthlySalesText":  "2,142",
                         "repurchaseRate":  28.21,
                         "repurchaseRateText":  "28.21%"
                     },
                     {
                         "id":  "hb1688-women-030",
                         "source":  "1688",
                         "title":  "In-Stock Manga-Style Chest-Enhancing Camisole with Chest Pads for Summer, Slim-Fit, Suitable for Small Busts, Base Layer Top",
                         "titleZh":  "现货漫画感显胸吊带带胸垫 夏季修身小胸适合打底上衣",
                         "displayTitle":  "现货漫画感显胸吊带带胸垫 夏季修身小胸适合打底上衣",
                         "image":  "https://cbu01.alicdn.com/img/ibank/O1CN01vfyDuP1snx0KaZU1g_!!2218462915812-0-cib.jpg_400x400.jpg_.webp",
                         "price":  {
                                       "cny":  20.00,
                                       "cnyText":  "20.00 CNY",
                                       "eur":  2.60,
                                       "eurText":  "2.60 EUR"
                                   },
                         "monthlySales":  509,
                         "monthlySalesText":  "509",
                         "repurchaseRate":  8.55,
                         "repurchaseRateText":  "8.55%"
                     },
                     {
                         "id":  "hb1688-women-031",
                         "source":  "1688",
                         "title":  "Breathable Camisole with Built-In Chest Pads and Wide Shoulder Straps, Women\u0027s Summer Slim-Fit Square-Neck Base Top",
                         "titleZh":  null,
                         "displayTitle":  "Breathable Camisole with Built-In Chest Pads and Wide Shoulder Straps, Women\u0027s Summer Slim-Fit Square-Neck Base Top",
                         "image":  "https://cbu01.alicdn.com/img/ibank/O1CN01J3BNiM1ZLZkcT9iVO_!!2611553178-0-cib.jpg_400x400.jpg_.webp",
                         "price":  {
                                       "cny":  33.50,
                                       "cnyText":  "33.50 CNY",
                                       "eur":  4.36,
                                       "eurText":  "4.36 EUR"
                                   },
                         "monthlySales":  1551,
                         "monthlySalesText":  "1,551",
                         "repurchaseRate":  5.13,
                         "repurchaseRateText":  "5.13%"
                     },
                     {
                         "id":  "hb1688-women-032",
                         "source":  "1688",
                         "title":  "2024 Summer Women\u0027s Clothing Amazon Cotton and Linen Set European and American Sleeveless Top Wide-Leg Pants Two-Piece Set Girly Style",
                         "titleZh":  null,
                         "displayTitle":  "2024 Summer Women\u0027s Clothing Amazon Cotton and Linen Set European and American Sleeveless Top Wide-Leg Pants Two-Piece Set Girly Style",
                         "image":  "https://cbu01.alicdn.com/img/ibank/O1CN0118UKnp1XolffPQEhF_!!2215643632971-0-cib.jpg_400x400.jpg_.webp",
                         "price":  {
                                       "cny":  38.00,
                                       "cnyText":  "38.00 CNY",
                                       "eur":  4.94,
                                       "eurText":  "4.94 EUR"
                                   },
                         "monthlySales":  386,
                         "monthlySalesText":  "386",
                         "repurchaseRate":  52.94,
                         "repurchaseRateText":  "52.94%"
                     },
                     {
                         "id":  "hb1688-women-033",
                         "source":  "1688",
                         "title":  "Thickened 260g Solid Color Racerback Camisole for Women with Chest Pads, Slim Fit, Versatile Base Layer",
                         "titleZh":  null,
                         "displayTitle":  "Thickened 260g Solid Color Racerback Camisole for Women with Chest Pads, Slim Fit, Versatile Base Layer",
                         "image":  "https://cbu01.alicdn.com/img/ibank/O1CN01HbESK01WzTTTvlCwr_!!2219436642859-0-cib.jpg_400x400.jpg_.webp",
                         "price":  {
                                       "cny":  18.90,
                                       "cnyText":  "18.90 CNY",
                                       "eur":  2.46,
                                       "eurText":  "2.46 EUR"
                                   },
                         "monthlySales":  352,
                         "monthlySalesText":  "352",
                         "repurchaseRate":  5.5,
                         "repurchaseRateText":  "5.5%"
                     },
                     {
                         "id":  "hb1688-women-034",
                         "source":  "1688",
                         "title":  "[Factory Direct Sale] Sweet Lace Splicing Camisole Women\u0027s Spring and Summer Korean Style Thin Inner Sleeveless Vest",
                         "titleZh":  null,
                         "displayTitle":  "[Factory Direct Sale] Sweet Lace Splicing Camisole Women\u0027s Spring and Summer Korean Style Thin Inner Sleeveless Vest",
                         "image":  "https://cbu01.alicdn.com/img/ibank/O1CN01nheOEs1pvKZ8gNp1k_!!2220877105422-0-cib.jpg_400x400.jpg_.webp",
                         "price":  {
                                       "cny":  4.70,
                                       "cnyText":  "4.70 CNY",
                                       "eur":  0.61,
                                       "eurText":  "0.61 EUR"
                                   },
                         "monthlySales":  14363,
                         "monthlySalesText":  "14,363",
                         "repurchaseRate":  54.97,
                         "repurchaseRateText":  "54.97%"
                     },
                     {
                         "id":  "hb1688-women-035",
                         "source":  "1688",
                         "title":  "2025 Camisole Women\u0027s White Beautiful Back Acetic Acid Silk Top Satin Summer Suit Imitation Base Shirt",
                         "titleZh":  null,
                         "displayTitle":  "2025 Camisole Women\u0027s White Beautiful Back Acetic Acid Silk Top Satin Summer Suit Imitation Base Shirt",
                         "image":  "https://cbu01.alicdn.com/img/ibank/O1CN01U0c0SM2CBHqoSqoUE_!!2208396738435-0-cib.jpg_400x400.jpg_.webp",
                         "price":  {
                                       "cny":  18.80,
                                       "cnyText":  "18.80 CNY",
                                       "eur":  2.44,
                                       "eurText":  "2.44 EUR"
                                   },
                         "monthlySales":  1259,
                         "monthlySalesText":  "1,259",
                         "repurchaseRate":  8.57,
                         "repurchaseRateText":  "8.57%"
                     },
                     {
                         "id":  "hb1688-women-036",
                         "source":  "1688",
                         "title":  "Pure Cotton White Tank Top for Women, 2026 New Spring Fashion, Anti-Exposure, Slimming, Beautiful Back Design, Camisole Base Layer Top",
                         "titleZh":  null,
                         "displayTitle":  "Pure Cotton White Tank Top for Women, 2026 New Spring Fashion, Anti-Exposure, Slimming, Beautiful Back Design, Camisole Base Layer Top",
                         "image":  "https://cbu01.alicdn.com/img/ibank/O1CN01wz8nxq2HHlchOpYyw_!!2221494729126-0-cib.jpg_400x400.jpg_.webp",
                         "price":  {
                                       "cny":  16.50,
                                       "cnyText":  "16.50 CNY",
                                       "eur":  2.15,
                                       "eurText":  "2.15 EUR"
                                   },
                         "monthlySales":  476,
                         "monthlySalesText":  "476",
                         "repurchaseRate":  3.39,
                         "repurchaseRateText":  "3.39%"
                     },
                     {
                         "id":  "hb1688-women-037",
                         "source":  "1688",
                         "title":  "Selected Ribbed Cotton 2026 Summer New Style Spicy Girl Camisole Tank Top for Women, Can Be Worn as an Inner Layer or Outerwear, with Beautiful Back Design and Chest Pads",
                         "titleZh":  null,
                         "displayTitle":  "Selected Ribbed Cotton 2026 Summer New Style Spicy Girl Camisole Tank Top for Women, Can Be Worn as an Inner Layer or Outerwear, with Beautiful Back Design and Chest Pads",
                         "image":  "https://cbu01.alicdn.com/img/ibank/O1CN01tb75tD29VUInUx8zC_!!2211004788073-0-cib.jpg_400x400.jpg_.webp",
                         "price":  {
                                       "cny":  19.98,
                                       "cnyText":  "19.98 CNY",
                                       "eur":  2.60,
                                       "eurText":  "2.60 EUR"
                                   },
                         "monthlySales":  538,
                         "monthlySalesText":  "538",
                         "repurchaseRate":  16.22,
                         "repurchaseRateText":  "16.22%"
                     },
                     {
                         "id":  "hb1688-women-038",
                         "source":  "1688",
                         "title":  "862 # Rayon Vitality Dopamine Color Check Cross Bra Camisole Pure Desire Hot Girl Fake Two-Piece Small Top for Women",
                         "titleZh":  null,
                         "displayTitle":  "862 # Rayon Vitality Dopamine Color Check Cross Bra Camisole Pure Desire Hot Girl Fake Two-Piece Small Top for Women",
                         "image":  "https://cbu01.alicdn.com/img/ibank/O1CN01zv9DLX1qIEJkjcqtI_!!2214639505472-0-cib.jpg_400x400.jpg_.webp",
                         "price":  {
                                       "cny":  10.50,
                                       "cnyText":  "10.50 CNY",
                                       "eur":  1.36,
                                       "eurText":  "1.36 EUR"
                                   },
                         "monthlySales":  1360,
                         "monthlySalesText":  "1,360",
                         "repurchaseRate":  28.42,
                         "repurchaseRateText":  "28.42%"
                     },
                     {
                         "id":  "hb1688-women-039",
                         "source":  "1688",
                         "title":  "Summer 2026 American Style Spicy Girl U-Neck Camisole with Chest Pads, Stunning Slim-Fit Tank Top That Hides Side Breasts, Short Top",
                         "titleZh":  null,
                         "displayTitle":  "Summer 2026 American Style Spicy Girl U-Neck Camisole with Chest Pads, Stunning Slim-Fit Tank Top That Hides Side Breasts, Short Top",
                         "image":  "https://cbu01.alicdn.com/img/ibank/O1CN018HmkpU1y4VImJdOGR_!!2218067896525-0-cib.jpg_400x400.jpg_.webp",
                         "price":  {
                                       "cny":  19.00,
                                       "cnyText":  "19.00 CNY",
                                       "eur":  2.47,
                                       "eurText":  "2.47 EUR"
                                   },
                         "monthlySales":  193,
                         "monthlySalesText":  "193",
                         "repurchaseRate":  4.48,
                         "repurchaseRateText":  "4.48%"
                     },
                     {
                         "id":  "hb1688-women-040",
                         "source":  "1688",
                         "title":  "European and American Cross-Border Sexy Lace Camisole Top, New Summer Vacation Style, Short Striped Lace Tank Top That Shows the Bust",
                         "titleZh":  null,
                         "displayTitle":  "European and American Cross-Border Sexy Lace Camisole Top, New Summer Vacation Style, Short Striped Lace Tank Top That Shows the Bust",
                         "image":  "https://cbu01.alicdn.com/img/ibank/O1CN01FsQKQt1UjKH4E3mJ7_!!2220874362553-0-cib.jpg_400x400.jpg_.webp",
                         "price":  {
                                       "cny":  35.60,
                                       "cnyText":  "35.60 CNY",
                                       "eur":  4.63,
                                       "eurText":  "4.63 EUR"
                                   },
                         "monthlySales":  188,
                         "monthlySalesText":  "188",
                         "repurchaseRate":  21.43,
                         "repurchaseRateText":  "21.43%"
                     },
                     {
                         "id":  "hb1688-women-041",
                         "source":  "1688",
                         "title":  "2026 Summer New Korean Designer Alo Sports Knitted Casual Yoga Bra Fitness Camisole for Women",
                         "titleZh":  null,
                         "displayTitle":  "2026 Summer New Korean Designer Alo Sports Knitted Casual Yoga Bra Fitness Camisole for Women",
                         "image":  "https://cbu01.alicdn.com/img/ibank/O1CN01Yk6FfX1xn6Oc6oNay_!!2218995466487-0-cib.jpg_400x400.jpg_.webp",
                         "price":  {
                                       "cny":  29.90,
                                       "cnyText":  "29.90 CNY",
                                       "eur":  3.89,
                                       "eurText":  "3.89 EUR"
                                   },
                         "monthlySales":  235,
                         "monthlySalesText":  "235",
                         "repurchaseRate":  8.62,
                         "repurchaseRateText":  "8.62%"
                     },
                     {
                         "id":  "hb1688-women-042",
                         "source":  "1688",
                         "title":  "2026 Spring and Summer Silk Wool T-Shirt for Women, Thin, Slightly See-Through, Loose Casual Outerwear, Round Neck, Long-Sleeved Blouse",
                         "titleZh":  null,
                         "displayTitle":  "2026 Spring and Summer Silk Wool T-Shirt for Women, Thin, Slightly See-Through, Loose Casual Outerwear, Round Neck, Long-Sleeved Blouse",
                         "image":  "https://cbu01.alicdn.com/img/ibank/O1CN01fkV9nF1FmKdqUxycs_!!2090480529-0-cib.jpg_400x400.jpg_.webp",
                         "price":  {
                                       "cny":  46.00,
                                       "cnyText":  "46.00 CNY",
                                       "eur":  5.98,
                                       "eurText":  "5.98 EUR"
                                   },
                         "monthlySales":  334,
                         "monthlySalesText":  "334",
                         "repurchaseRate":  18.42,
                         "repurchaseRateText":  "18.42%"
                     },
                     {
                         "id":  "hb1688-women-043",
                         "source":  "1688",
                         "title":  "Metwo Concave Collar Racerback Vest with Latex Straps, Ultra-Thin, Breathable, Comfortable, Backless Racerback Vest Inner Top",
                         "titleZh":  null,
                         "displayTitle":  "Metwo Concave Collar Racerback Vest with Latex Straps, Ultra-Thin, Breathable, Comfortable, Backless Racerback Vest Inner Top",
                         "image":  "https://cbu01.alicdn.com/img/ibank/O1CN013rduv21Q5hU19saCP_!!2217013841925-0-cib.jpg_400x400.jpg_.webp",
                         "price":  {
                                       "cny":  21.00,
                                       "cnyText":  "21.00 CNY",
                                       "eur":  2.73,
                                       "eurText":  "2.73 EUR"
                                   },
                         "monthlySales":  242,
                         "monthlySalesText":  "242",
                         "repurchaseRate":  4.67,
                         "repurchaseRateText":  "4.67%"
                     },
                     {
                         "id":  "hb1688-women-044",
                         "source":  "1688",
                         "title":  "Small Camisole with Built-In Bra Pads for Women, Invisible Foundation-Like Base Layer, Beautiful Back Design, Plus Size, Short Style",
                         "titleZh":  null,
                         "displayTitle":  "Small Camisole with Built-In Bra Pads for Women, Invisible Foundation-Like Base Layer, Beautiful Back Design, Plus Size, Short Style",
                         "image":  "https://cbu01.alicdn.com/img/ibank/O1CN019lZT0r2HF1F7cHjMM_!!2215896119120-0-cib.jpg_400x400.jpg_.webp",
                         "price":  {
                                       "cny":  18.00,
                                       "cnyText":  "18.00 CNY",
                                       "eur":  2.34,
                                       "eurText":  "2.34 EUR"
                                   },
                         "monthlySales":  194,
                         "monthlySalesText":  "194",
                         "repurchaseRate":  11.29,
                         "repurchaseRateText":  "11.29%"
                     },
                     {
                         "id":  "hb1688-women-045",
                         "source":  "1688",
                         "title":  "Purple New Style Pleated Camisole with Chest Pads for Women, Suitable for Wearing Outside or Inside, Featuring a Cinched Waist and Beautiful Back Design for Summer",
                         "titleZh":  null,
                         "displayTitle":  "Purple New Style Pleated Camisole with Chest Pads for Women, Suitable for Wearing Outside or Inside, Featuring a Cinched Waist and Beautiful Back Design for Summer",
                         "image":  "https://cbu01.alicdn.com/img/ibank/O1CN01JWI2mI1nmVadgZyBg_!!2207621175132-0-cib.jpg_400x400.jpg_.webp",
                         "price":  {
                                       "cny":  12.60,
                                       "cnyText":  "12.60 CNY",
                                       "eur":  1.64,
                                       "eurText":  "1.64 EUR"
                                   },
                         "monthlySales":  1134,
                         "monthlySalesText":  "1,134",
                         "repurchaseRate":  15.56,
                         "repurchaseRateText":  "15.56%"
                     },
                     {
                         "id":  "hb1688-women-046",
                         "source":  "1688",
                         "title":  "2026 European and American Cotton and Linen Camisole Women\u0027s Summer New Loose Cotton and Linen Sleeveless Versatile Base Top",
                         "titleZh":  null,
                         "displayTitle":  "2026 European and American Cotton and Linen Camisole Women\u0027s Summer New Loose Cotton and Linen Sleeveless Versatile Base Top",
                         "image":  "https://cbu01.alicdn.com/img/ibank/O1CN01Iwao7X1tK0bVM5d38_!!2208154365882-0-cib.jpg_400x400.jpg_.webp",
                         "price":  {
                                       "cny":  15.00,
                                       "cnyText":  "15.00 CNY",
                                       "eur":  1.95,
                                       "eurText":  "1.95 EUR"
                                   },
                         "monthlySales":  876,
                         "monthlySalesText":  "876",
                         "repurchaseRate":  52,
                         "repurchaseRateText":  "52%"
                     },
                     {
                         "id":  "hb1688-women-047",
                         "source":  "1688",
                         "title":  "Summer Thin Pure Cotton Women\u0027s Sleeveless Ribbed Knit Tank Top Versatile Outerwear",
                         "titleZh":  null,
                         "displayTitle":  "Summer Thin Pure Cotton Women\u0027s Sleeveless Ribbed Knit Tank Top Versatile Outerwear",
                         "image":  "https://cbu01.alicdn.com/img/ibank/O1CN01ZLeKMf2BcwB8YBwNJ_!!2219710588360-0-cib.jpg_400x400.jpg_.webp",
                         "price":  {
                                       "cny":  11.80,
                                       "cnyText":  "11.80 CNY",
                                       "eur":  1.53,
                                       "eurText":  "1.53 EUR"
                                   },
                         "monthlySales":  775,
                         "monthlySalesText":  "775",
                         "repurchaseRate":  23.4,
                         "repurchaseRateText":  "23.4%"
                     },
                     {
                         "id":  "hb1688-women-048",
                         "source":  "1688",
                         "title":  "Cartoon Outer-Chest Expanded Camisole Women\u0027s Outer Wear Summer Slim-Fit Slimming Small Chest Large Spice Girl Inner Base Top",
                         "titleZh":  null,
                         "displayTitle":  "Cartoon Outer-Chest Expanded Camisole Women\u0027s Outer Wear Summer Slim-Fit Slimming Small Chest Large Spice Girl Inner Base Top",
                         "image":  "https://cbu01.alicdn.com/img/ibank/O1CN01Le9ATU1FU0j3Gsnbd_!!2211008090489-0-cib.jpg_400x400.jpg_.webp",
                         "price":  {
                                       "cny":  15.50,
                                       "cnyText":  "15.50 CNY",
                                       "eur":  2.02,
                                       "eurText":  "2.02 EUR"
                                   },
                         "monthlySales":  224,
                         "monthlySalesText":  "224",
                         "repurchaseRate":  6.19,
                         "repurchaseRateText":  "6.19%"
                     },
                     {
                         "id":  "hb1688-women-049",
                         "source":  "1688",
                         "title":  "Four Seasons New Style High-Elastic Thin Strap Women\u0027s Tank Top, Soft and Comfortable, Slimming, Suitable for Outerwear or as a Base Layer, with a Beautiful Back Design",
                         "titleZh":  null,
                         "displayTitle":  "Four Seasons New Style High-Elastic Thin Strap Women\u0027s Tank Top, Soft and Comfortable, Slimming, Suitable for Outerwear or as a Base Layer, with a Beautiful Back Design",
                         "image":  "https://cbu01.alicdn.com/img/ibank/O1CN01zjhxNO1qOdwpZGpi3_!!2208476805486-0-cib.jpg_400x400.jpg_.webp",
                         "price":  {
                                       "cny":  37.00,
                                       "cnyText":  "37.00 CNY",
                                       "eur":  4.81,
                                       "eurText":  "4.81 EUR"
                                   },
                         "monthlySales":  2094,
                         "monthlySalesText":  "2,094",
                         "repurchaseRate":  8.82,
                         "repurchaseRateText":  "8.82%"
                     },
                     {
                         "id":  "hb1688-women-050",
                         "source":  "1688",
                         "title":  "Live Broadcast Thickened Chest Pads for a Larger Appearance, Detachable Camisole Versatile Short Style with Beautiful Back, Base Wrap, and Bandeau for Women",
                         "titleZh":  null,
                         "displayTitle":  "Live Broadcast Thickened Chest Pads for a Larger Appearance, Detachable Camisole Versatile Short Style with Beautiful Back, Base Wrap, and Bandeau for Women",
                         "image":  "https://cbu01.alicdn.com/img/ibank/O1CN01PTxPxc1FU0jHEjZbK_!!2211008090489-0-cib.jpg_400x400.jpg_.webp",
                         "price":  {
                                       "cny":  6.90,
                                       "cnyText":  "6.90 CNY",
                                       "eur":  0.90,
                                       "eurText":  "0.90 EUR"
                                   },
                         "monthlySales":  319,
                         "monthlySalesText":  "319",
                         "repurchaseRate":  17.65,
                         "repurchaseRateText":  "17.65%"
                     }
                 ]
};

if (typeof window !== 'undefined') {
  window.HUBBUYER_FAST_PRODUCT_DATA = HUBBUYER_FAST_PRODUCT_DATA;
}

if (typeof module !== 'undefined') {
  module.exports = HUBBUYER_FAST_PRODUCT_DATA;
}
