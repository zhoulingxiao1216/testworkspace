-- Mock accounts for performance tests:
-- performance_test_001@126.com ~ performance_test_050@126.com
-- Password: 123456, stored as MD5('123456') = e10adc3949ba59abbe56e057f20f883e
--
-- This script is idempotent by email/user_id and avoids fixed auto-increment ids.

SET NAMES utf8mb4;
SET FOREIGN_KEY_CHECKS = 0;

-- Pre-check.
SELECT
    COUNT(*) AS existing_mock_user_count
FROM `user`
WHERE `email` BETWEEN 'performance_test_001@126.com' AND 'performance_test_050@126.com'
  AND `email` LIKE 'performance_test\_%@126.com';

START TRANSACTION;

DROP TEMPORARY TABLE IF EXISTS `tmp_performance_mock_accounts`;
CREATE TEMPORARY TABLE `tmp_performance_mock_accounts` (
    `seq` INT NOT NULL PRIMARY KEY,
    `email` VARCHAR(255) NOT NULL,
    `uuid` VARCHAR(50) NOT NULL,
    `name` VARCHAR(255) NOT NULL,
    `mobile` VARCHAR(50) NOT NULL
) ENGINE=MEMORY;

INSERT INTO `tmp_performance_mock_accounts` (`seq`, `email`, `uuid`, `name`, `mobile`)
SELECT
    n.`seq`,
    CONCAT('performance_test_', LPAD(n.`seq`, 3, '0'), '@126.com') AS `email`,
    CONCAT('PERF', LPAD(n.`seq`, 3, '0')) AS `uuid`,
    CONCAT('performance_test_', LPAD(n.`seq`, 3, '0')) AS `name`,
    CONCAT('1900000', LPAD(n.`seq`, 4, '0')) AS `mobile`
FROM (
    SELECT 1 AS `seq` UNION ALL SELECT 2 UNION ALL SELECT 3 UNION ALL SELECT 4 UNION ALL SELECT 5
    UNION ALL SELECT 6 UNION ALL SELECT 7 UNION ALL SELECT 8 UNION ALL SELECT 9 UNION ALL SELECT 10
    UNION ALL SELECT 11 UNION ALL SELECT 12 UNION ALL SELECT 13 UNION ALL SELECT 14 UNION ALL SELECT 15
    UNION ALL SELECT 16 UNION ALL SELECT 17 UNION ALL SELECT 18 UNION ALL SELECT 19 UNION ALL SELECT 20
    UNION ALL SELECT 21 UNION ALL SELECT 22 UNION ALL SELECT 23 UNION ALL SELECT 24 UNION ALL SELECT 25
    UNION ALL SELECT 26 UNION ALL SELECT 27 UNION ALL SELECT 28 UNION ALL SELECT 29 UNION ALL SELECT 30
    UNION ALL SELECT 31 UNION ALL SELECT 32 UNION ALL SELECT 33 UNION ALL SELECT 34 UNION ALL SELECT 35
    UNION ALL SELECT 36 UNION ALL SELECT 37 UNION ALL SELECT 38 UNION ALL SELECT 39 UNION ALL SELECT 40
    UNION ALL SELECT 41 UNION ALL SELECT 42 UNION ALL SELECT 43 UNION ALL SELECT 44 UNION ALL SELECT 45
    UNION ALL SELECT 46 UNION ALL SELECT 47 UNION ALL SELECT 48 UNION ALL SELECT 49 UNION ALL SELECT 50
) n;

-- 1) Base user records.
UPDATE `user` u
JOIN `tmp_performance_mock_accounts` t ON t.`email` = u.`email` AND u.`pid` = 0
SET
    u.`last_name` = 'Performance',
    u.`first_name` = LPAD(t.`seq`, 3, '0'),
    u.`name` = t.`name`,
    u.`password` = MD5('123456'),
    u.`status` = 200,
    u.`nation` = 'China',
    u.`b2b_status` = 200,
    u.`d2c_status` = 0,
    u.`oem_status` = 0,
    u.`mobile_location` = '+86',
    u.`mobile` = t.`mobile`,
    u.`level` = 'A',
    u.`csp_manager_admin_id` = 10,
    u.`purchase_admin_id` = 15,
    u.`sale_admin_id` = 10,
    u.`csp_admin_id` = 7,
    u.`updated_at` = NOW();

INSERT INTO `user` (
    `pid`, `uuid`, `last_name`, `first_name`, `name`, `email`, `password`, `pay_password`,
    `status`, `nation`, `b2b_status`, `d2c_status`, `oem_status`, `mobile_location`, `mobile`,
    `level`, `csp_manager_admin_id`, `purchase_admin_id`, `sale_admin_id`, `csp_admin_id`,
    `avatar`, `date`, `created_at`, `updated_at`
)
SELECT
    0,
    t.`uuid`,
    'Performance',
    LPAD(t.`seq`, 3, '0'),
    t.`name`,
    t.`email`,
    MD5('123456'),
    '',
    200,
    'China',
    200,
    0,
    0,
    '+86',
    t.`mobile`,
    'A',
    10,
    15,
    10,
    7,
    '',
    CURDATE(),
    NOW(),
    NOW()
FROM `tmp_performance_mock_accounts` t
WHERE NOT EXISTS (
    SELECT 1 FROM `user` u WHERE u.`email` = t.`email` AND u.`pid` = 0
);

-- 2) B2B user records.
UPDATE `b2b_user` b
JOIN `user` u ON u.`id` = b.`user_id`
JOIN `tmp_performance_mock_accounts` t ON t.`email` = u.`email` AND u.`pid` = 0
SET
    b.`user_uuid` = u.`uuid`,
    b.`csp_manager_admin_id` = u.`csp_manager_admin_id`,
    b.`purchase_admin_id` = u.`purchase_admin_id`,
    b.`sale_admin_id` = u.`sale_admin_id`,
    b.`csp_admin_id` = u.`csp_admin_id`,
    b.`balance` = 999999.00,
    b.`is_trust` = 0,
    b.`updated_at` = NOW();

INSERT INTO `b2b_user` (
    `user_id`, `user_uuid`, `csp_manager_admin_id`, `purchase_admin_id`, `sale_admin_id`,
    `csp_admin_id`, `child_account_role`, `preference_cate`, `balance`, `is_trust`,
    `created_at`, `updated_at`
)
SELECT
    u.`id`,
    u.`uuid`,
    u.`csp_manager_admin_id`,
    u.`purchase_admin_id`,
    u.`sale_admin_id`,
    u.`csp_admin_id`,
    NULL,
    NULL,
    999999.00,
    0,
    NOW(),
    NOW()
FROM `tmp_performance_mock_accounts` t
JOIN `user` u ON u.`email` = t.`email` AND u.`pid` = 0
WHERE NOT EXISTS (
    SELECT 1 FROM `b2b_user` b WHERE b.`user_id` = u.`id`
);

-- 3) User business info.
UPDATE `user_info` ui
JOIN `user` u ON u.`id` = ui.`user_id`
JOIN `tmp_performance_mock_accounts` t ON t.`email` = u.`email` AND u.`pid` = 0
SET
    ui.`user_uuid` = u.`uuid`,
    ui.`business_form` = 1,
    ui.`business_name` = 'Performance Mock',
    ui.`phone_location` = '+86',
    ui.`phone` = t.`mobile`,
    ui.`order_meet_status` = 100,
    ui.`communicate_remark` = 'performance test mock account',
    ui.`updated_at` = NOW();

INSERT INTO `user_info` (
    `user_id`, `user_uuid`, `business_form`, `business_name`, `business_url`,
    `business_legal_person_name`, `business_amount`, `register_source`, `register_introducer`,
    `have_import_experience`, `cooperative_corporation`, `leave_reason`, `phone_location`,
    `phone`, `phone_time`, `purchase_frequency`, `purchase_num`, `purchase_money`,
    `order_type`, `sale_model`, `online_store_url`, `order_meet_status`, `communicate_remark`,
    `created_at`, `updated_at`
)
SELECT
    u.`id`,
    u.`uuid`,
    1,
    'Performance Mock',
    '',
    '',
    '0',
    0,
    'performance_mock',
    0,
    '',
    '',
    '+86',
    t.`mobile`,
    '',
    0,
    0,
    '0',
    NULL,
    NULL,
    NULL,
    100,
    'performance test mock account',
    NOW(),
    NOW()
FROM `tmp_performance_mock_accounts` t
JOIN `user` u ON u.`email` = t.`email` AND u.`pid` = 0
WHERE NOT EXISTS (
    SELECT 1 FROM `user_info` ui WHERE ui.`user_id` = u.`id`
);

-- 4) User statistics.
INSERT INTO `user_statistic` (
    `user_id`, `user_uuid`, `user_main_uuid`, `b2b_order_num`, `oem_order_num`, `d2c_order_num`,
    `b2b_last_order_no`, `oem_last_order_no`, `d2c_last_order_no`, `b2b_recharge_money`,
    `oem_recharge_money`, `d2c_recharge_money`, `b2b_recharge_num`, `oem_recharge_num`,
    `d2c_recharge_num`, `b2b_first_recharge_at`, `oem_first_recharge_at`, `d2c_first_recharge_at`,
    `b2b_first_recharge_money`, `oem_first_recharge_money`, `d2c_first_recharge_money`,
    `login_num`, `login_at`, `login_ip`, `register_at`, `register_ip`, `first_site`,
    `expected_val`, `actual_val`, `date`, `created_at`, `updated_at`
)
SELECT
    u.`id`,
    u.`uuid`,
    u.`uuid`,
    0,
    0,
    0,
    '',
    '',
    '',
    '0',
    '0',
    '0',
    0,
    0,
    0,
    NULL,
    NULL,
    NULL,
    NULL,
    NULL,
    NULL,
    0,
    NULL,
    '',
    NOW(),
    '',
    'B2B',
    '0',
    '0',
    CURDATE(),
    NOW(),
    NOW()
FROM `tmp_performance_mock_accounts` t
JOIN `user` u ON u.`email` = t.`email` AND u.`pid` = 0
WHERE NOT EXISTS (
    SELECT 1 FROM `user_statistic` us WHERE us.`user_id` = u.`id`
);

UPDATE `user_statistic` us
JOIN `user` u ON u.`id` = us.`user_id`
JOIN `tmp_performance_mock_accounts` t ON t.`email` = u.`email` AND u.`pid` = 0
SET
    us.`user_uuid` = u.`uuid`,
    us.`user_main_uuid` = u.`uuid`,
    us.`first_site` = 'B2B',
    us.`updated_at` = NOW();

-- 5) B2B membership role.
UPDATE `b2b_user_role` r
JOIN `user` u ON u.`uuid` = r.`user_uuid`
JOIN `tmp_performance_mock_accounts` t ON t.`email` = u.`email` AND u.`pid` = 0
SET
    r.`user_main_uuid` = u.`uuid`,
    r.`role_config_uuid` = 'FREE-2506-01',
    r.`role_config_fee_uuid` = '',
    r.`expire_at` = '2099-12-30 00:00:00',
    r.`role_auto_renew` = 2,
    r.`updated_at` = NOW();

INSERT INTO `b2b_user_role` (
    `user_main_uuid`, `user_uuid`, `role_config_uuid`, `role_config_fee_uuid`, `expire_at`,
    `role_auto_renew`, `date`, `created_at`, `updated_at`
)
SELECT
    u.`uuid`,
    u.`uuid`,
    'FREE-2506-01',
    '',
    '2099-12-30 00:00:00',
    2,
    CURDATE(),
    NOW(),
    NOW()
FROM `tmp_performance_mock_accounts` t
JOIN `user` u ON u.`email` = t.`email` AND u.`pid` = 0
WHERE NOT EXISTS (
    SELECT 1 FROM `b2b_user_role` r WHERE r.`user_uuid` = u.`uuid`
);

COMMIT;

SET FOREIGN_KEY_CHECKS = 1;

-- Post-check.
SELECT
    u.`email`,
    u.`uuid`,
    u.`status`,
    u.`b2b_status`,
    b.`balance`,
    r.`role_config_uuid`,
    r.`expire_at`
FROM `user` u
LEFT JOIN `b2b_user` b ON b.`user_id` = u.`id`
LEFT JOIN `b2b_user_role` r ON r.`user_uuid` = u.`uuid`
WHERE u.`email` BETWEEN 'performance_test_001@126.com' AND 'performance_test_050@126.com'
  AND u.`email` LIKE 'performance_test\_%@126.com'
ORDER BY u.`email`;
