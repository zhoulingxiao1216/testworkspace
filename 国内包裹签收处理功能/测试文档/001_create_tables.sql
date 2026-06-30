-- ============================================================
-- 国内快递签收及处理功能 - 完整迁移SQL（建表+初始数据+字段变更）
-- 分支: feature/domestic-express-002
-- TAPD: 1001960
-- 创建时间: 2026-04-28
-- 合并自: 001_create_tables.sql + 002_init_data.sql + 迁移文档SQL
-- ============================================================

-- 表1: 国内快递包裹签收主表
CREATE TABLE IF NOT EXISTS `b2b_domestic_express` (
  `id` int unsigned NOT NULL AUTO_INCREMENT,
  `package_no` varchar(100) NOT NULL DEFAULT '' COMMENT '快递单号',
  `logistics_id` int NOT NULL DEFAULT 0 COMMENT '物流公司ID(关联china_logistics)',
  `logistics_name` varchar(100) NOT NULL DEFAULT '' COMMENT '物流公司名称(冗余)',
  `order_no` varchar(100) NOT NULL DEFAULT '' COMMENT '关联全球站主订单号(可为空)',
  `platform_order_no` varchar(100) NOT NULL DEFAULT '' COMMENT '平台原订单号',
  `platform` varchar(50) NOT NULL DEFAULT '' COMMENT '平台来源: 1688/taobao/manual',
  `is_private` tinyint NOT NULL DEFAULT 0 COMMENT '是否私人包裹: 1是 0否',
  `send_time` datetime DEFAULT NULL COMMENT '发货时间(平台获取)',
  `receipt_time` datetime DEFAULT NULL COMMENT '仓库签收时间',
  `receipt_admin_id` int NOT NULL DEFAULT 0 COMMENT '签收操作人ID',
  `takeover_time` datetime DEFAULT NULL COMMENT '初检部揽收时间',
  `takeover_admin_id` int NOT NULL DEFAULT 0 COMMENT '揽收操作人ID',
  `handle_time` datetime DEFAULT NULL COMMENT '处理完成时间',
  `handle_admin_id` int NOT NULL DEFAULT 0 COMMENT '处理操作人ID',
  `handle_status` smallint NOT NULL DEFAULT 100 COMMENT '处理状态: 100未处理 200已处理(私人包裹不参与)',
  `handle_remark` varchar(500) NOT NULL DEFAULT '' COMMENT '处理备注',
  `is_timeout` tinyint NOT NULL DEFAULT 0 COMMENT '是否超时: 1是 0否(私人包裹不参与)',
  `timeout_hours` decimal(10,2) NOT NULL DEFAULT 0 COMMENT '实际耗时(小时)',
  `status` smallint NOT NULL DEFAULT 200 COMMENT '200正常 0删除',
  `admin_id` int NOT NULL DEFAULT 0 COMMENT '创建人ID',
  `date` date DEFAULT NULL,
  `created_at` datetime DEFAULT NULL,
  `updated_at` datetime DEFAULT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_package_no` (`package_no`),
  KEY `idx_order_no` (`order_no`),
  KEY `idx_receipt_time` (`receipt_time`),
  KEY `idx_handle_status` (`handle_status`),
  KEY `idx_is_timeout` (`is_timeout`),
  KEY `idx_is_private` (`is_private`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='国内快递包裹签收主表';


-- 表2: 包裹-订单关联子表
CREATE TABLE IF NOT EXISTS `b2b_domestic_express_order` (
  `id` int unsigned NOT NULL AUTO_INCREMENT,
  `express_id` int NOT NULL DEFAULT 0 COMMENT '关联b2b_domestic_express.id',
  `package_no` varchar(100) NOT NULL DEFAULT '' COMMENT '快递单号(冗余)',
  `order_no` varchar(100) NOT NULL DEFAULT '' COMMENT '全球站主订单号',
  `platform_order_no` varchar(100) NOT NULL DEFAULT '' COMMENT '平台原订单号',
  `seller_open_id` varchar(100) NOT NULL DEFAULT '' COMMENT '店铺ID',
  `user_main_uuid` varchar(100) NOT NULL DEFAULT '' COMMENT '客户主账号UUID',
  `sale_admin_id` int NOT NULL DEFAULT 0 COMMENT '业务员ID',
  `purchase_admin_id` int NOT NULL DEFAULT 0 COMMENT '采购员ID',
  `created_at` datetime DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `idx_express_id` (`express_id`),
  KEY `idx_order_no` (`order_no`),
  KEY `idx_package_no` (`package_no`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='国内快递包裹-订单关联表';


-- 表3: 超时配置表
CREATE TABLE IF NOT EXISTS `b2b_domestic_express_config` (
  `id` int unsigned NOT NULL AUTO_INCREMENT,
  `config_key` varchar(100) NOT NULL DEFAULT '' COMMENT '配置键',
  `config_value` text COMMENT '配置值(JSON)',
  `remark` varchar(255) NOT NULL DEFAULT '' COMMENT '配置说明',
  `status` smallint NOT NULL DEFAULT 200 COMMENT '200正常 0禁用',
  `created_at` datetime DEFAULT NULL,
  `updated_at` datetime DEFAULT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_config_key` (`config_key`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='国内快递签收配置表';


-- ============================================================
-- 物流轨迹功能 - 字段变更
-- 来源: docs/feature-domestic-express-002/2026-05-09-物流轨迹功能迁移文档.md
-- 日期: 2026-05-09
-- ============================================================

-- b2b_order_create_log 新增字段: 淘宝采购单行ID (幂等: 先判断字段是否存在)
SET @col_exists = (SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS 
  WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'b2b_order_create_log' AND COLUMN_NAME = 'purchase_order_line_id');
SET @sql = IF(@col_exists = 0, 
  'ALTER TABLE `b2b_order_create_log` ADD COLUMN `purchase_order_line_id` varchar(100) DEFAULT \'\' COMMENT \'淘宝采购单行ID\' AFTER `partner_order_no`', 
  'SELECT 1');
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;


-- ============================================================
-- 初始化数据
-- 来源: 002_init_data.sql
-- ============================================================

-- 超时配置默认数据
INSERT IGNORE INTO `b2b_domestic_express_config` (`config_key`, `config_value`, `remark`, `status`, `created_at`) VALUES
('timeout_weekday_hours', '24', '工作日(周一至周五)超时阈值(小时)', 200, NOW()),
('timeout_saturday_hours', '48', '周六签收超时阈值(小时)', 200, NOW()),
('holidays', '["2026-01-01","2026-01-28","2026-01-29","2026-01-30","2026-01-31","2026-02-01","2026-02-02","2026-02-03","2026-02-04","2026-04-04","2026-05-01","2026-05-02","2026-05-03","2026-05-04","2026-05-05","2026-06-01","2026-10-01","2026-10-02","2026-10-03","2026-10-04","2026-10-05","2026-10-06","2026-10-07"]', '法定节假日列表(JSON数组,格式Y-m-d)', 200, NOW());

-- ============================================================
-- 菜单及权限初始化
-- ============================================================

-- 插入菜单组 (幂等: 先检查是否已存在)
INSERT INTO `admin_menu` (`pid`, `type`, `name`, `title`, `path`, `component`, `auth`, `status`, `show`, `created_at`, `updated_at`)
SELECT 343, 2, 'b2bDepositoryDomesticExpressGroup', '国内包裹', '/b2b/depository/domesticExpressGroup', '', '/b2b/depository/domesticExpressGroup', 200, 200, NOW(), NOW()
FROM DUAL WHERE NOT EXISTS (SELECT 1 FROM `admin_menu` WHERE `name` = 'b2bDepositoryDomesticExpressGroup');
SET @groupId = (SELECT `id` FROM `admin_menu` WHERE `name` = 'b2bDepositoryDomesticExpressGroup' LIMIT 1);

-- 插入包裹签收
INSERT INTO `admin_menu` (`pid`, `type`, `name`, `title`, `path`, `component`, `auth`, `status`, `show`, `created_at`, `updated_at`)
SELECT @groupId, 3, 'b2bDepositoryDomesticExpressIndex', '包裹签收', '/b2b/depository/domesticExpress/index', '/b2b/depository/domesticExpress/index.vue', '/b2b/depository/domesticExpress/index', 200, 200, NOW(), NOW()
FROM DUAL WHERE NOT EXISTS (SELECT 1 FROM `admin_menu` WHERE `name` = 'b2bDepositoryDomesticExpressIndex');

-- 插入超时配置
INSERT INTO `admin_menu` (`pid`, `type`, `name`, `title`, `path`, `component`, `auth`, `status`, `show`, `created_at`, `updated_at`)
SELECT @groupId, 3, 'b2bDepositoryDomesticExpressConfig', '超时配置', '/b2b/depository/domesticExpress/config', '/b2b/depository/domesticExpress/config.vue', '/b2b/depository/domesticExpress/config', 200, 200, NOW(), NOW()
FROM DUAL WHERE NOT EXISTS (SELECT 1 FROM `admin_menu` WHERE `name` = 'b2bDepositoryDomesticExpressConfig');
