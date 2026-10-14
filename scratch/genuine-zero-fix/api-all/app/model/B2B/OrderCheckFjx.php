<?php
/**
 * OrderCheckFjx.php
 * Created on 2025/5/29
 * Created by WML
 *
 */

namespace app\model\B2B;

use app\model\Base;
use Illuminate\Database\Query\Builder;
use Illuminate\Support\Collection;
use support\Db;

/**
 * 订单检品和附加项快照模型，封装配置读写与批量同步。
 */
class OrderCheckFjx extends Base
{
    static string $table_name = 'b2b_order_check_fjx';

    static function tableName(): string
    {
        return self::$table_name;
    }

    /**
     * 入库参数
     * @param $request
     * @return array
     */
    static function param($request): array
    {
        $param['status'] = $request->input('status') ?? null;
        return $param;
    }

    /**
     * 复杂语句查询
     * @param array $condition
     * @return Builder
     */
    static function getQueryBuilder(array $condition = []): Builder
    {
        return Db::table(self::tableName())->where($condition);
    }

    static function getQueryBuilderWhereIn($column,$values,$boolean = 'and',$not = false): Builder
    {
        return Db::table(self::tableName())->whereIn($column,$values,$boolean,$not);
    }


    /**
     * 查询单个数据
     * @param $condition
     * @param array $order
     * @return object|null
     */
    static function findData($condition,array $order = ["id","desc"]): object|null
    {
        return Db::table(self::tableName())->where($condition)->orderBy($order[0],$order[1])->first();
    }

    static function findDataJson($condition, array $order=["id","desc"],  array $fields=["*"]): object|null
    {
        $data = Db::table(self::tableName())->where($condition)->orderBy($order[0],$order[1])->select($fields)->first();
        if(!empty($data)){
            $data->check_config = !empty($data->check_config) ? json_decode($data->check_config,true) : [];
            $data->fjx_config = !empty($data->fjx_config) ? json_decode($data->fjx_config,true) : [];
            $data->user_fjx_config = !empty($data->user_fjx_config) ? json_decode($data->user_fjx_config,true) : [];
        }
        return $data;
    }

    /**
     * 查询列表数据
     * @param $condition
     * @param int $limit
     * @param int $offset
     * @param array $order
     * @param array $fields
     * @return Collection
     */
    static function listData($condition,int $limit = 15,int $offset = 0,array $order = ["id","desc"],array $fields = ["*"]): Collection
    {
        return Db::table(self::tableName())->where($condition)->limit($limit)->offset($offset)->select($fields)->orderBy($order[0],$order[1])->get();
    }

    /**
     * @param $condition
     * @return int
     */
    static function totalData($condition): int
    {
        return Db::table(self::tableName())->where($condition)->count();
    }

    /**
     * 查询所有数据
     * @param $condition
     * @param array $order
     * @param int $limit
     * @return Collection
     */
    static function allData($condition,array $order = ["id","desc"],int $limit = 200): Collection
    {
        return Db::table(self::tableName())->where($condition)->limit($limit)->orderBy($order[0],$order[1])->get();
    }

    /**
     * 插入数据
     * @param $data
     * @return bool
     */
    static function insertData($data): bool
    {
        $data['created_at'] = date("Y-m-d H:i:s");
        return Db::table(self::tableName())->insert($data);
    }

    static function insertAllData($data): bool
    {
        return Db::table(self::tableName())->insert($data);
    }

    /**
     * 插入数据 并返回新增ID
     * @param $data
     * @return int
     */
    static function insertDataGetId($data): int
    {
        $data['created_at'] = date("Y-m-d H:i:s");
        return Db::table(self::tableName())->insertGetId($data);
    }

    /**
     * 更新数据
     * @param $condition
     * @param $data
     * @return int
     */
    static function updateData($condition,$data): int
    {
        if(!isset($data['updated_at'])){
            $data['updated_at'] = date("Y-m-d H:i:s");
        }
        return Db::table(self::tableName())->where($condition)->update($data);
    }


    /**
     * 批量按主键 id 更新检品附加项配置（单条 upsert，避免循环内逐条写库）。
     * 每行必须包含 id；其余列按 $rows 各自取值，仅更新 $update_columns 指定的列。
     * 由于所有 id 均已存在，MySQL 走 ON DUPLICATE KEY UPDATE，不会真正插入新行。
     * @param array $rows 形如 [['id'=>1,'check_config'=>'...','check_total'=>0, ...], ...]
     * @param array $update_columns 需要更新的列名（不含 id）
     * @return bool 空批次返回 false；SQL 正常执行返回 true，包括零变更。
     * @throws \Throwable 数据库异常交由调用方处理和回滚。
     */
    static function batchUpsertConfig(array $rows, array $update_columns): bool
    {
        if (empty($rows)) return false;
        // 返回值是受影响行数；数据一致时为 0，不代表 SQL 执行失败。
        // 数据库异常继续向上抛出，由调用方事务负责回滚。
        Db::table(self::tableName())->upsert($rows, ['id'], $update_columns);
        return true;
    }

    /**
     * 删除数据
     * @param $condition
     * @param array $order
     * @param int $limit
     * @return int
     */
    static function delData($condition,array $order = ["id","desc"],int $limit = 1): int
    {
        $data = Db::table(self::tableName())->where($condition)->orderBy($order[0],$order[1])->limit($limit)->get();
        self::addDelLog(self::tableName(),$condition,$data);
        return Db::table(self::tableName())->where($condition)->orderBy($order[0],$order[1])->limit($limit)->delete();
    }


    /**
     * batchDelData 批量删除数据
     * Created on 2025/4/16
     * Created by WML
     * @param $field
     * @param $value
     * @param $limit
     * @return array
     */
    static function batchDelData($field,$value,$limit): array
    {
        Db::beginTransaction();
        try {
            $data = self::getQueryBuilderWhereIn($field,$value)->limit($limit)->get();
            $row = self::getQueryBuilderWhereIn($field,$value)->limit($limit)->delete();
            $res = self::addDelLog(self::tableName(),[$field => ['in',$value]],$data);
            if (!$data || !$row || !$res) {
                Db::rollBack();
                return noticeMsg(400);
            } else {
                Db::commit();
                return noticeMsg(200);
            }
        } catch (\Exception $e) {
            Db::rollBack();
            return noticeMsg(500,$e->getMessage(),['file' => $e->getFile(),'line' => $e->getLine(),'message' => $e->getMessage()]);
        }


    }
}
