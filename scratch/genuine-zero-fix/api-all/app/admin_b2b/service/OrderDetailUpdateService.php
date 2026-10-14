<?php
/**
 * OrderDetailUpdateService.php
 * Created on 2025/6/27
 * Created by WML
 *
 */

namespace app\admin_b2b\service;

use app\model\B2B\CheckConfig;
use app\model\B2B\CheckFeeConfig;
use app\model\B2B\DesignFjxConfig;
use app\model\B2B\FjxConfig;
use app\model\B2B\FjxFeeConfig;
use app\model\B2B\Order;
use app\model\B2B\OrderCheckFjx;
use app\model\B2B\OrderDetail;
use app\model\B2B\UserFjxConfig;
use app\model\B2B\UserFjxFeeConfig;
use app\service\checkFjx\B2BCheckService;
use app\service\checkFjx\B2BFjxService;
use app\service\checkFjx\B2BUserFjxService;
use app\service\b2b\StorageAddonMessageService;
use support\Context;

/**
 * 订单商品数量更新服务，集中处理质检数量、附加项数量和数量边界判断。
 */
class OrderDetailUpdateService
{
    /**
     * 一键没货前需要确认没有进入的数量阶段。
     *
     * @var string[]
     */
    private const NO_STOCK_BLOCKING_QTY_FIELDS = [
        'arrive_qty',
        'wait_check_qty',
        'bad_qty',
        'wait_qty',
        'return_qty',
        'change_qty',
        'genuine_qty',
        'store_qty',
        'send_qty',
    ];

    /**
     * 设计类附加项状态名称，用于入库拦截提示。
     *
     * @var array<int, array{type: string, name: string}>
     */
    private const STORAGE_DESIGN_FJX_TYPES = [
        FjxConfig::DESIGN_STICKER => ['type' => FjxConfig::STICKER, 'name' => '贴纸'],
        FjxConfig::DESIGN_HANG_TAG => ['type' => FjxConfig::HANG_TAG, 'name' => '吊牌'],
        FjxConfig::DESIGN_FBA => ['type' => FjxConfig::FBA, 'name' => 'FBA'],
        FjxConfig::DESIGN_WASH => ['type' => FjxConfig::WASH, 'name' => '洗标'],
    ];

    /**
     * 批量检查入库商品的设计类附加项完成状态。
     *
     * 仅检查订单快照中启用的贴纸、吊牌、FBA、洗标；未选择或已禁用的设计项不参与拦截。
     * 快照状态会被订单维度的最新设计记录覆盖，避免入库接口使用过期状态。
     *
     * @param array<int|string> $order_detail_ids 订单商品明细 ID
     * @return array<int, array<int, array{name: string, reasons: string[]}>>
     * key 为订单商品明细 ID，value 为未完成附加项及原因
     */
    public static function getUnfinishedStorageAddonMap(array $order_detail_ids): array
    {
        $order_detail_ids = array_values(array_unique(array_filter(
            array_map('intval', $order_detail_ids),
            static fn(int $id): bool => $id > 0
        )));
        if (empty($order_detail_ids)) return [];

        $snapshot_rows = OrderCheckFjx::getQueryBuilderWhereIn('order_detail_id', $order_detail_ids)
            ->orderBy('id', 'desc')
            ->get()
            ->unique('order_detail_id');
        if ($snapshot_rows->isEmpty()) return [];

        $design_candidates = [];
        foreach ($snapshot_rows as $snapshot_row) {
            $order_detail_id = (int)$snapshot_row->order_detail_id;
            foreach ([
                self::decodeConfig($snapshot_row->fjx_config ?? []),
                self::decodeConfig($snapshot_row->user_fjx_config ?? []),
            ] as $config_group) {
                foreach ($config_group as $config_item) {
                    $design_type = self::STORAGE_DESIGN_FJX_TYPES[(int)($config_item['is_design'] ?? 0)] ?? null;
                    if (empty($design_type) || (int)($config_item['status'] ?? 0) !== 200) continue;

                    $config_uuid = (string)($config_item['fjx_config_uuid'] ?? '');
                    $candidate_key = $order_detail_id . '|' . $design_type['type'] . '|' . $config_uuid;
                    $design_candidates[$candidate_key] = [
                        'order_detail_id' => $order_detail_id,
                        'type' => $design_type['type'],
                        'config_uuid' => $config_uuid,
                        'name' => $design_type['name'],
                        'design_status' => (int)($config_item['design_status'] ?? 0),
                        'print_status' => (int)($config_item['print_status'] ?? 0),
                    ];
                }
            }
        }
        if (empty($design_candidates)) return [];

        $design_rows = DesignFjxConfig::getQueryBuilderWhereIn('order_detail_id', $order_detail_ids)
            ->whereIn('type', array_values(array_column(self::STORAGE_DESIGN_FJX_TYPES, 'type')))
            ->orderBy('id', 'desc')
            ->select(['id', 'order_detail_id', 'type', 'fjx_config_uuid', 'status', 'print_status'])
            ->get();
        $design_status_map = [];
        foreach ($design_rows as $design_row) {
            $key = (int)$design_row->order_detail_id . '|' . (string)$design_row->type . '|' . (string)($design_row->fjx_config_uuid ?? '');
            if (!array_key_exists($key, $design_status_map)) {
                $design_status_map[$key] = [
                    'design_status' => (int)($design_row->status ?? 0),
                    'print_status' => (int)($design_row->print_status ?? 0),
                ];
            }
        }

        $unfinished_map = [];
        foreach ($design_candidates as $candidate) {
            $key = $candidate['order_detail_id'] . '|' . $candidate['type'] . '|' . $candidate['config_uuid'];
            $design_state = $design_status_map[$key] ?? [
                'design_status' => $candidate['design_status'],
                'print_status' => $candidate['print_status'],
            ];
            $reasons = [];
            if ((int)($design_state['design_status'] ?? 0) !== 200) {
                $reasons[] = '设计未完成';
            }
            if ((int)($design_state['print_status'] ?? 0) !== 200) {
                $reasons[] = '未打印';
            }
            if (empty($reasons)) continue;

            $unfinished_map[$candidate['order_detail_id']][] = [
                'name' => $candidate['name'],
                'reasons' => $reasons,
            ];
        }

        foreach ($unfinished_map as $order_detail_id => $addons) {
            $normalized_addons = [];
            foreach ($addons as $addon) {
                $name = (string)($addon['name'] ?? '');
                if ($name === '') continue;

                if (!isset($normalized_addons[$name])) {
                    $normalized_addons[$name] = [
                        'name' => $name,
                        'reasons' => [],
                    ];
                }
                $normalized_addons[$name]['reasons'] = array_values(array_unique(array_merge(
                    $normalized_addons[$name]['reasons'],
                    (array)($addon['reasons'] ?? [])
                )));
            }
            $unfinished_map[$order_detail_id] = array_values($normalized_addons);
        }

        return $unfinished_map;
    }

    /**
     * 汇总多个订单商品的未完成设计类附加项提示。
     *
     * @param array<int|string> $order_detail_ids 订单商品明细 ID
     * @return string|null 无未完成项时返回 null
     */
    public static function getUnfinishedStorageAddonMessage(array $order_detail_ids): ?string
    {
        $unfinished_map = self::getUnfinishedStorageAddonMap($order_detail_ids);
        if (empty($unfinished_map)) return null;

        $order_detail_data = OrderDetail::getQueryBuilderWhereIn('id', array_keys($unfinished_map))
            ->select(['id', 'uuid'])
            ->get()
            ->keyBy('id');
        $items = [];
        foreach ($unfinished_map as $order_detail_id => $addons) {
            $order_detail = $order_detail_data->get((int)$order_detail_id);
            $items[] = [
                'uuid' => $order_detail->uuid ?? '商品',
                'addons' => $addons,
            ];
        }

        return StorageAddonMessageService::format($items);
    }

//    static function updateSuccessCallBack($admin_id,$order_detail_id,$quantity,$type='',$scale=0): void
//    {
//        $order_detail_data = OrderDetail::findData(['id'=>$order_detail_id]);
//
//        if(empty($type)){
//            $final_qty = $quantity;
//        }else{
//            $final_qty = calc($type,,$quantity,$scale);
//        }
//        OrderQuantityLog::insertData([
//            'admin_id' => $admin_id,
//            'order_no' => $order_detail_data->order_no,
//            'order_detail_id' => $order_detail_id,
//            'goods_uuid' => $order_detail_data->goods_uuid,
//            'quantity' => $quantity,
//            'old_qty' => 0,
//            'final_qty' => 0,
//            'type' => $type,
//        ]);
//
//    }

    /**
     * 修改订单附加项数量
     * updateOrderCheckFjx
     * Created on 2025/9/24
     * Created by XiaFei
     * @param $order_detail_id
     * @return bool
     */
    static function updateOrderCheckFjx($order_detail_id): bool
    {
        return self::updateOrderCheckFjxBatch([(int)$order_detail_id]);
    }

    /**
     * 批量同步订单商品的检品、附加项数量及金额。
     * 所有订单、商品、配置与费率通道在循环前一次性读取，循环内只处理内存数据，最后统一 upsert。
     *
     * @param array $order_detail_ids
     * @return bool
     */
    static function updateOrderCheckFjxBatch(array $order_detail_ids): bool
    {
        $order_detail_ids = array_values(array_unique(array_filter(
            array_map('intval', $order_detail_ids),
            static fn($id) => $id > 0
        )));
        if (empty($order_detail_ids)) return true;

        $order_check_fjx_map = OrderCheckFjx::getQueryBuilderWhereIn('order_detail_id', $order_detail_ids)
            ->orderBy('id', 'desc')
            ->get()
            ->unique('order_detail_id')
            ->keyBy('order_detail_id');
        if ($order_check_fjx_map->isEmpty()) return true;

        $order_detail_map = OrderDetail::getQueryBuilderWhereIn('id', $order_check_fjx_map->keys()->all())
            ->get()
            ->keyBy('id');
        $order_nos = $order_detail_map->pluck('order_no')->filter()->unique()->values()->all();
        $order_map = empty($order_nos)
            ? collect()
            : Order::getQueryBuilderWhereIn('order_no', $order_nos)
                ->orderBy('id', 'desc')
                ->get()
                ->unique('order_no')
                ->keyBy('order_no');

        $check_config_uuids = [];
        $fjx_config_uuids = [];
        $user_fjx_config_uuids = [];
        $check_fee_config_ids = [];
        $fjx_fee_config_ids = [];
        $user_fjx_fee_config_ids = [];
        $exclusive_fallback_user_uuids = [];
        foreach ($order_check_fjx_map as $order_check_fjx_data) {
            $order_check_fjx_data->check_config = self::decodeConfig($order_check_fjx_data->check_config ?? []);
            $order_check_fjx_data->fjx_config = self::decodeConfig($order_check_fjx_data->fjx_config ?? []);
            $order_check_fjx_data->user_fjx_config = self::decodeConfig($order_check_fjx_data->user_fjx_config ?? []);

            foreach ($order_check_fjx_data->check_config as $item) {
                if (!empty($item['check_config_uuid'])) $check_config_uuids[] = $item['check_config_uuid'];
                if (!empty($item['check_fee_config_id'])) $check_fee_config_ids[] = (int)$item['check_fee_config_id'];
            }
            foreach ($order_check_fjx_data->fjx_config as $item) {
                if (!empty($item['fjx_config_uuid'])) $fjx_config_uuids[] = $item['fjx_config_uuid'];
                if (!empty($item['fjx_fee_config_id'])) $fjx_fee_config_ids[] = (int)$item['fjx_fee_config_id'];
            }
            foreach ($order_check_fjx_data->user_fjx_config as $item) {
                if (!empty($item['fjx_config_uuid'])) $user_fjx_config_uuids[] = $item['fjx_config_uuid'];
                if (!empty($item['fjx_fee_config_id'])) $user_fjx_fee_config_ids[] = (int)$item['fjx_fee_config_id'];
            }

            $order_detail = $order_detail_map->get((int)$order_check_fjx_data->order_detail_id);
            $order_data = !empty($order_detail) ? $order_map->get($order_detail->order_no) : null;
            if (
                !empty($order_data->user_main_uuid)
                && empty($order_check_fjx_data->user_fjx_config)
                && empty(B2BFjxService::onlyNormalFjxConfig($order_check_fjx_data->fjx_config))
            ) {
                $exclusive_fallback_user_uuids[] = (string)$order_data->user_main_uuid;
            }
        }

        $check_config_map = self::buildUuidMap(CheckConfig::class, $check_config_uuids);
        $fjx_config_map = self::buildUuidMap(FjxConfig::class, $fjx_config_uuids);
        $user_fjx_config_map = self::buildUuidMap(UserFjxConfig::class, $user_fjx_config_uuids);
        $check_fee_config_map = self::buildIdMap(CheckFeeConfig::class, $check_fee_config_ids);
        $fjx_fee_config_map = self::buildIdMap(FjxFeeConfig::class, $fjx_fee_config_ids);
        $user_fjx_fee_config_map = self::buildIdMap(UserFjxFeeConfig::class, $user_fjx_fee_config_ids);
        $exclusive_user_set = self::buildExclusiveUserSet($exclusive_fallback_user_uuids);

        $upsert_rows = [];
        foreach ($order_check_fjx_map as $order_check_fjx_data) {
            $order_detail = $order_detail_map->get((int)$order_check_fjx_data->order_detail_id);
            $order_data = !empty($order_detail) ? $order_map->get($order_detail->order_no) : null;
            if (empty($order_detail) || empty($order_data)) return false;

            $normal_fjx_config = B2BFjxService::onlyNormalFjxConfig($order_check_fjx_data->fjx_config);
            $use_exclusive_matrix = !empty($order_check_fjx_data->user_fjx_config)
                || (empty($normal_fjx_config) && isset($exclusive_user_set[(string)($order_data->user_main_uuid ?? '')]));

            $check_config = $order_check_fjx_data->check_config;
            foreach ($check_config as &$check_config_item) {
                $config = $check_config_map[$check_config_item['check_config_uuid'] ?? ''] ?? null;
                if (empty($config)) return false;
                $fee_channel = self::resolveCheckFeeChannel($check_config_item, $check_fee_config_map);
                if ($fee_channel == CheckFeeConfig::FEE_CHANNEL_TIME || $config->fee_unit == CheckConfig::FEE_UNIT_30M_UNIT) {
                    $check_config_item['quantity'] = max(0, $check_config_item['quantity'] ?? 0);
                } elseif ($config->fee_unit == CheckConfig::FEE_UNIT_SKU) {
                    $check_config_item['quantity'] = 1;
                } elseif ($config->fee_type == CheckConfig::FEE_TYPE_GENUINE) {
                    $check_config_item['quantity'] = self::resolveSnapshotQuantity($check_config_item, $order_detail, (int)$config->fee_unit, CheckConfig::FEE_TYPE_GENUINE, $fee_channel, CheckFeeConfig::FEE_CHANNEL_TIME);
                } elseif ($config->fee_type == CheckConfig::FEE_TYPE_ARRIVAL) {
                    $check_config_item['quantity'] = self::resolveSnapshotQuantity($check_config_item, $order_detail, (int)$config->fee_unit, CheckConfig::FEE_TYPE_ARRIVAL, $fee_channel, CheckFeeConfig::FEE_CHANNEL_TIME);
                } elseif ($config->fee_type == CheckConfig::FEE_TYPE_NEED_CHECK) {
                    $check_config_item['quantity'] = self::resolveSnapshotQuantity($check_config_item, $order_detail, (int)$config->fee_unit, CheckConfig::FEE_TYPE_NEED_CHECK, $fee_channel, CheckFeeConfig::FEE_CHANNEL_TIME);
                }
            }
            unset($check_config_item);

            $fjx_config = $use_exclusive_matrix
                ? B2BFjxService::onlyDesignFjxConfig($order_check_fjx_data->fjx_config)
                : $order_check_fjx_data->fjx_config;
            foreach ($fjx_config as &$fjx_config_item) {
                $config = $fjx_config_map[$fjx_config_item['fjx_config_uuid'] ?? ''] ?? null;
                if (empty($config)) return false;
                $fee_channel = self::resolveFjxFeeChannel($fjx_config_item, $fjx_fee_config_map);
                if ($fee_channel == FjxFeeConfig::FEE_CHANNEL_TIME || $fee_channel == FjxFeeConfig::FEE_CHANNEL_TALK || $config->fee_unit == FjxConfig::FEE_UNIT_3M_UNIT) {
                    $fjx_config_item['quantity'] = max(0, $fjx_config_item['quantity'] ?? 0);
                } elseif ($config->fee_unit == FjxConfig::FEE_UNIT_SKU) {
                    $fjx_config_item['quantity'] = 1;
                } elseif ($config->fee_type == FjxConfig::FEE_TYPE_GENUINE) {
                    $fjx_config_item['quantity'] = self::resolveSnapshotQuantity($fjx_config_item, $order_detail, (int)$config->fee_unit, FjxConfig::FEE_TYPE_GENUINE, $fee_channel, FjxFeeConfig::FEE_CHANNEL_TIME);
                } elseif ($config->fee_type == FjxConfig::FEE_TYPE_ARRIVAL) {
                    $fjx_config_item['quantity'] = self::resolveSnapshotQuantity($fjx_config_item, $order_detail, (int)$config->fee_unit, FjxConfig::FEE_TYPE_ARRIVAL, $fee_channel, FjxFeeConfig::FEE_CHANNEL_TIME);
                } elseif ($config->fee_type == FjxConfig::FEE_TYPE_CHECK) {
                    $fjx_config_item['quantity'] = self::resolveSnapshotQuantity($fjx_config_item, $order_detail, (int)$config->fee_unit, FjxConfig::FEE_TYPE_CHECK, $fee_channel, FjxFeeConfig::FEE_CHANNEL_TIME);
                }
            }
            unset($fjx_config_item);

            $user_fjx_config = $use_exclusive_matrix ? $order_check_fjx_data->user_fjx_config : [];
            foreach ($user_fjx_config as &$user_fjx_config_item) {
                $config = $user_fjx_config_map[$user_fjx_config_item['fjx_config_uuid'] ?? ''] ?? null;
                if (empty($config)) return false;
                $fee_channel = self::resolveUserFjxFeeChannel($user_fjx_config_item, $user_fjx_fee_config_map);
                if ($fee_channel == UserFjxFeeConfig::FEE_CHANNEL_TIME || $fee_channel == UserFjxFeeConfig::FEE_CHANNEL_TALK || $config->fee_unit == UserFjxConfig::FEE_UNIT_3M_UNIT) {
                    $user_fjx_config_item['quantity'] = max(0, $user_fjx_config_item['quantity'] ?? 0);
                } elseif ($config->fee_unit == UserFjxConfig::FEE_UNIT_SKU) {
                    $user_fjx_config_item['quantity'] = 1;
                } elseif ($config->fee_type == UserFjxConfig::FEE_TYPE_GENUINE) {
                    $user_fjx_config_item['quantity'] = self::resolveSnapshotQuantity($user_fjx_config_item, $order_detail, (int)$config->fee_unit, UserFjxConfig::FEE_TYPE_GENUINE, $fee_channel, UserFjxFeeConfig::FEE_CHANNEL_TIME);
                } elseif ($config->fee_type == UserFjxConfig::FEE_TYPE_ARRIVAL) {
                    $user_fjx_config_item['quantity'] = self::resolveSnapshotQuantity($user_fjx_config_item, $order_detail, (int)$config->fee_unit, UserFjxConfig::FEE_TYPE_ARRIVAL, $fee_channel, UserFjxFeeConfig::FEE_CHANNEL_TIME);
                } elseif ($config->fee_type == UserFjxConfig::FEE_TYPE_CHECK) {
                    $user_fjx_config_item['quantity'] = self::resolveSnapshotQuantity($user_fjx_config_item, $order_detail, (int)$config->fee_unit, UserFjxConfig::FEE_TYPE_CHECK, $fee_channel, UserFjxFeeConfig::FEE_CHANNEL_TIME);
                }
            }
            unset($user_fjx_config_item);

            $check_fee_info = B2BCheckService::getSelectedNameFeeInfo($check_config, $order_data->member_level_uuid);
            Context::set('fjx_spec_info_param', '');
            $selected_fjx_config = $use_exclusive_matrix
                ? B2BFjxService::onlyDesignFjxConfig($fjx_config)
                : B2BFjxService::mergeFjxConfigByUuid(
                    B2BFjxService::onlyNormalFjxConfig($fjx_config),
                    B2BFjxService::onlyDesignFjxConfig($fjx_config)
                );
            $fjx_fee_info = empty($selected_fjx_config)
                ? ['status_active_total' => 0, 'status_active_amount' => 0]
                : B2BFjxService::getSelectedNameFeeInfo($selected_fjx_config, $order_data->member_level_uuid);
            Context::set('user_fjx_spec_info_param', '');
            $user_fjx_fee_info = $use_exclusive_matrix
                ? B2BUserFjxService::getSelectedNameFeeInfo($user_fjx_config, $order_data->member_level_uuid, 'admin', $order_data->user_main_uuid ?? '')
                : ['status_active_total' => 0, 'status_active_amount' => 0];

            $upsert_rows[] = [
                'id' => (int)$order_check_fjx_data->id,
                'check_config' => !empty($check_config) ? json_encode($check_config, JSON_UNESCAPED_SLASHES | JSON_UNESCAPED_UNICODE) : null,
                'fjx_config' => !empty($fjx_config) ? json_encode($fjx_config, JSON_UNESCAPED_SLASHES | JSON_UNESCAPED_UNICODE) : null,
                'user_fjx_config' => $use_exclusive_matrix && !empty($user_fjx_config)
                    ? json_encode($user_fjx_config, JSON_UNESCAPED_SLASHES | JSON_UNESCAPED_UNICODE)
                    : null,
                'check_total' => $check_fee_info['status_active_total'],
                'check_amount' => $check_fee_info['status_active_amount'] ?? 0,
                'fjx_total' => $fjx_fee_info['status_active_total'],
                'fjx_amount' => $fjx_fee_info['status_active_amount'] ?? 0,
                'user_fjx_total' => $user_fjx_fee_info['status_active_total'],
                'user_fjx_amount' => $user_fjx_fee_info['status_active_amount'] ?? 0,
                'updated_at' => date("Y-m-d H:i:s"),
            ];
        }

        return OrderCheckFjx::batchUpsertConfig($upsert_rows, [
            'check_config', 'fjx_config', 'user_fjx_config',
            'check_total', 'check_amount', 'fjx_total', 'fjx_amount',
            'user_fjx_total', 'user_fjx_amount', 'updated_at',
        ]);
    }

    /**
     * 将 JSON 字段规范为配置数组。
     */
    /**
     * Resolve a snapshot quantity with the shared order detail fallback rule.
     *
     * @param array $snapshot_config
     * @param mixed $order_detail
     * @param int $fee_unit
     * @param int $fee_type
     * @param int $fee_channel
     * @param int $time_fee_channel
     * @return int|float
     */
    private static function resolveSnapshotQuantity(array $snapshot_config, mixed $order_detail, int $fee_unit, int $fee_type, int $fee_channel, int $time_fee_channel): int|float
    {
        return OrderCheckFjxService::resolveActiveQuantity(
            array_merge($snapshot_config, [
                'fee_unit' => $fee_unit,
                'fee_type' => $fee_type,
                'fee_channel' => $fee_channel,
            ]),
            OrderCheckFjxService::buildOrderDetailQuantityContext($order_detail),
            $time_fee_channel
        );
    }

    protected static function decodeConfig(mixed $config): array
    {
        if (is_array($config)) return $config;
        if (!is_string($config) || $config === '') return [];
        $decoded = json_decode($config, true);
        return is_array($decoded) ? $decoded : [];
    }

    /**
     * 按 UUID 一次性查询配置并构建内存 map。
     */
    protected static function buildUuidMap(string $modelClass, array $uuids): array
    {
        $uuids = array_values(array_unique(array_filter($uuids)));
        if (empty($uuids)) return [];
        return $modelClass::getQueryBuilderWhereIn('uuid', $uuids)
            ->orderBy('id', 'desc')
            ->get()
            ->unique('uuid')
            ->keyBy('uuid')
            ->all();
    }

    /**
     * 按主键一次性查询费率配置并构建内存 map。
     */
    protected static function buildIdMap(string $modelClass, array $ids): array
    {
        $ids = array_values(array_unique(array_filter(array_map('intval', $ids))));
        if (empty($ids)) return [];
        return $modelClass::getQueryBuilderWhereIn('id', $ids)
            ->get()
            ->keyBy('id')
            ->all();
    }

    /**
     * 批量判断缺少快照标识时哪些用户启用了定制附加项专属矩阵。
     */
    protected static function buildExclusiveUserSet(array $userMainUuids): array
    {
        $userMainUuids = array_values(array_unique(array_filter($userMainUuids)));
        if (empty($userMainUuids)) return [];

        $targetSet = array_flip($userMainUuids);
        $exclusiveUserSet = [];
        $rows = UserFjxConfig::getQueryBuilder(['status' => 200, 'is_custom_price' => 1])
            ->select(['user_main_uuids', 'custom_fee_info'])
            ->get();
        foreach ($rows as $row) {
            $customFeeInfo = self::decodeConfig($row->custom_fee_info ?? []);
            if (empty($customFeeInfo)) continue;
            $rowUserUuids = array_filter(array_map('trim', explode(',', (string)($row->user_main_uuids ?? ''))));
            foreach ($rowUserUuids as $userMainUuid) {
                if (isset($targetSet[$userMainUuid])) $exclusiveUserSet[$userMainUuid] = true;
            }
        }
        return $exclusiveUserSet;
    }

    protected static function resolveCheckFeeChannel(array $checkConfig, array $feeConfigMap = []): int
    {
        $feeChannel = (int)($checkConfig['fee_channel'] ?? 0);
        if ($feeChannel > 0) {
            return $feeChannel;
        }

        $checkFeeConfigId = $checkConfig['check_fee_config_id'] ?? 0;
        if (empty($checkFeeConfigId)) {
            return 0;
        }

        $checkFeeConfig = $feeConfigMap[(int)$checkFeeConfigId] ?? null;
        return (int)($checkFeeConfig->fee_channel ?? 0);
    }

    protected static function resolveFjxFeeChannel(array $fjxConfig, array $feeConfigMap = []): int
    {
        $feeChannel = (int)($fjxConfig['fee_channel'] ?? 0);
        if ($feeChannel > 0) {
            return $feeChannel;
        }

        $fjxFeeConfigId = $fjxConfig['fjx_fee_config_id'] ?? 0;
        if (empty($fjxFeeConfigId)) {
            return 0;
        }

        $fjxFeeConfig = $feeConfigMap[(int)$fjxFeeConfigId] ?? null;
        return (int)($fjxFeeConfig->fee_channel ?? 0);
    }

    protected static function resolveUserFjxFeeChannel(array $userFjxConfig, array $feeConfigMap = []): int
    {
        $feeChannel = (int)($userFjxConfig['fee_channel'] ?? 0);
        if ($feeChannel > 0) {
            return $feeChannel;
        }

        $userFjxFeeConfigId = $userFjxConfig['fjx_fee_config_id'] ?? 0;
        if (empty($userFjxFeeConfigId)) {
            return 0;
        }

        $userFjxFeeConfig = $feeConfigMap[(int)$userFjxFeeConfigId] ?? null;
        return (int)($userFjxFeeConfig->fee_channel ?? 0);
    }

    static function isSpotCheckDetail(array $checkConfigData = []): bool
    {
        foreach ($checkConfigData as $checkConfig) {
            if (
                ($checkConfig['check_config_uuid'] ?? '') === CheckConfig::CHECK_CONFIG_UUID_01
                && (int)($checkConfig['status'] ?? 0) === 200
            ) {
                return true;
            }
        }

        return false;
    }

    static function getQualityResultLimitQty(object $orderDetailData, array $checkConfigData = []): mixed
    {
        if (self::isSpotCheckDetail($checkConfigData) && !self::isQuantityEmpty($orderDetailData->arrive_qty ?? '')) {
            return $orderDetailData->arrive_qty;
        }

        return $orderDetailData->wait_check_qty ?? '';
    }

    static function getOrderCheckConfigData(object $orderDetailData): array
    {
        if (empty($orderDetailData->id)) {
            return [];
        }

        $orderCheckFjxData = OrderCheckFjx::findDataJson(
            ['order_detail_id' => $orderDetailData->id],
            ['id', 'desc'],
            ['check_config']
        );

        if (empty($orderCheckFjxData) || empty($orderCheckFjxData->check_config)) {
            return [];
        }

        return $orderCheckFjxData->check_config;
    }

    static function isQualityResultLimitEmpty(mixed $quantity): bool
    {
        return self::isQuantityEmpty($quantity);
    }

    static function shouldCheckBadQtyLimit(object $orderDetailData): bool
    {
        return self::isQuantityEmpty($orderDetailData->return_qty ?? '')
            && self::isQuantityEmpty($orderDetailData->change_qty ?? '');
    }

    /**
     * 判断订单商品是否仍处于可以一键标记“没货没买”的初始待采购状态。
     *
     * 待采购历史数据可能把未操作数量保存为数字 0，因此 purchase_qty=0 只有在没有对应操作日志时才视为初始值。
     * @param object $orderDetailData 订单商品行数据
     * @param string[] $operatedFields 已存在数量操作日志的字段
     * @return bool
     */
    static function isNoStockActionAllowed(object $orderDetailData, array $operatedFields = []): bool
    {
        if ((int)($orderDetailData->order_mark ?? 0) !== OrderDetail::ORDER_MARK_WAIT_PURCHASED) {
            return false;
        }

        $operatedFieldMap = array_fill_keys(array_map('strval', $operatedFields), true);
        if (isset($operatedFieldMap['purchase_qty'])) {
            return false;
        }

        $purchaseQty = $orderDetailData->purchase_qty ?? '';
        if (!self::isQuantityEmpty($purchaseQty) && self::quantityToFloat($purchaseQty) !== 0.0) {
            return false;
        }

        foreach (self::NO_STOCK_BLOCKING_QTY_FIELDS as $field) {
            if (isset($operatedFieldMap[$field])) {
                return false;
            }

            $quantity = $orderDetailData->{$field} ?? '';
            if (!self::isQuantityEmpty($quantity) && self::quantityToFloat($quantity) !== 0.0) {
                return false;
            }
        }

        return true;
    }

    static function isBeforeShipmentQuantityLocked(object $orderDetailData): bool
    {
        return self::quantityToFloat($orderDetailData->send_qty ?? 0) > 0;
    }

    static function isStoreQtyGreaterThanGenuineQty(object $orderDetailData): bool
    {
        return self::quantityToFloat($orderDetailData->store_qty ?? 0) > self::quantityToFloat($orderDetailData->genuine_qty ?? 0);
    }

    static function isFutureStoreQtyGreaterThanGenuineQty(object $orderDetailData, mixed $incrementQty): bool
    {
        $futureOrderDetailData = clone $orderDetailData;
        $futureOrderDetailData->store_qty = self::quantityToFloat($orderDetailData->store_qty ?? 0)
            + self::quantityToFloat($incrementQty);

        return self::isStoreQtyGreaterThanGenuineQty($futureOrderDetailData);
    }

    static function getActualQualityOperateQty(object $orderDetailData): float
    {
        return self::quantityToFloat($orderDetailData->arrive_qty ?? 0) - self::quantityToFloat($orderDetailData->store_qty ?? 0);
    }

    /**
     * 获取质检结果或退换处置占用的最大可操作数量。
     *
     * 不良/待定是质检结果，退货/换货是对同一批问题货的后续处置；两组不能简单相加，
     * 否则已登记不良后再退货同一批货会被重复占用。
     *
     * @param object $orderDetailData 订单商品行数据
     * @param array $overrides 本次操作后的字段值覆盖
     * @return float
     */
    static function getQualityOperateQty(object $orderDetailData, array $overrides = []): float
    {
        $qualityQty = self::sumQualityOperateFields($orderDetailData, ['bad_qty', 'wait_qty'], $overrides);
        $returnChangeQty = self::sumQualityOperateFields($orderDetailData, ['return_qty', 'change_qty'], $overrides);

        return max($qualityQty, $returnChangeQty);
    }

    private static function sumQualityOperateFields(object $orderDetailData, array $fields, array $overrides = []): float
    {
        $totalQty = 0.0;

        foreach ($fields as $field) {
            $qty = array_key_exists($field, $overrides) ? $overrides[$field] : ($orderDetailData->{$field} ?? 0);
            $totalQty += self::quantityToFloat($qty);
        }

        return $totalQty;
    }

    static function isQualityOperateQtyWithinActual(object $orderDetailData, array $overrides = []): bool
    {
        return self::getQualityOperateQty($orderDetailData, $overrides) <= self::getActualQualityOperateQty($orderDetailData);
    }

    /**
     * 校验累计不良数量不能小于零，允许使用负增量撤销已有不良数量。
     *
     * @param mixed $quantity 本次操作后的累计不良数量
     * @return bool
     */
    static function isBadQtyNonNegative(mixed $quantity): bool
    {
        return self::quantityToFloat($quantity) >= 0;
    }

    /**
     * 计算一键正品数量：到货数 - 不良数 - 待定数。
     *
     * @param object $orderDetailData 订单商品行数据
     * @return float
     */
    static function calculateGenuineQty(object $orderDetailData): float
    {
        return self::quantityToFloat($orderDetailData->arrive_qty ?? 0)
            - self::quantityToFloat($orderDetailData->bad_qty ?? 0)
            - self::quantityToFloat($orderDetailData->wait_qty ?? 0);
    }

    /**
     * 根据最新正品数与已入库数计算数量更新后的商品状态。
     *
     * 已完成入库或进入待发货阶段的商品，在正品数未产生新增待入库量时保持原进度；
     * 只有正品数超过已入库数时，才回到待入库或部分入库状态。
     *
     * @param object $orderDetailData 更新前订单商品数据
     * @param mixed $genuineQty 更新后的正品数量
     * @return int
     */
    static function resolveOrderMarkAfterGenuineQty(object $orderDetailData, mixed $genuineQty): int
    {
        $genuineQty = self::quantityToFloat($genuineQty);
        $storeQty = self::quantityToFloat($orderDetailData->store_qty ?? 0);
        $currentOrderMark = (int)($orderDetailData->order_mark ?? 0);

        if ($genuineQty > $storeQty) {
            return $storeQty > 0
                ? OrderDetail::ORDER_MARK_PART_STOCK
                : OrderDetail::ORDER_MARK_STOCK_PENDING;
        }

        // 正品数和入库数都为 0 时没有入库状态依据，保留当前业务阶段。
        if ($genuineQty <= 0 && $storeQty <= 0) {
            return $currentOrderMark;
        }

        return max($currentOrderMark, OrderDetail::ORDER_MARK_COMPLETED_STOCK);
    }

    private static function isQuantityEmpty(mixed $quantity): bool
    {
        return $quantity === '' || $quantity === null;
    }

    private static function quantityToFloat(mixed $quantity): float
    {
        if (self::isQuantityEmpty($quantity)) {
            return 0.0;
        }

        return (float)$quantity;
    }
}
