<?php
/**
 * 验证附加项快照零变更成功、空批次拒绝及数据库异常传播；不连接数据库。
 */
namespace app\model {
    class Base {}
}

namespace support {
    /** 模拟数据库写入返回值，不执行任何 SQL。 */
    class Db
    {
        public static int $affected = 0;
        public static int $calls = 0;
        public static bool $fail = false;

        public static function table(string $table): self
        {
            if ($table !== 'b2b_order_check_fjx') throw new \RuntimeException('Unexpected table');
            return new self();
        }

        public function upsert(array $rows, array $keys, array $columns): int
        {
            self::$calls++;
            if ($keys !== ['id'] || $columns !== ['fjx_config']) throw new \RuntimeException('Unexpected upsert arguments');
            if (self::$fail) throw new \RuntimeException('database failure');
            return self::$affected;
        }
    }
}

namespace {
    require __DIR__ . '/../../app/model/B2B/OrderCheckFjx.php';

    function check(bool $condition, string $name): void
    {
        if (!$condition) throw new \RuntimeException($name);
        echo "PASS: {$name}\n";
    }

    $rows = [['id' => 1, 'fjx_config' => '[]']];
    check(\app\model\B2B\OrderCheckFjx::batchUpsertConfig($rows, ['fjx_config']), 'zero changes succeeds');
    check(\app\model\B2B\OrderCheckFjx::batchUpsertConfig($rows, ['fjx_config']), 'repeated identical write succeeds');
    \support\Db::$affected = 2;
    check(\app\model\B2B\OrderCheckFjx::batchUpsertConfig($rows, ['fjx_config']), 'changed rows succeeds');
    $calls = \support\Db::$calls;
    check(!\app\model\B2B\OrderCheckFjx::batchUpsertConfig([], ['fjx_config']), 'empty batch rejected');
    check(\support\Db::$calls === $calls, 'empty batch does not write');
    \support\Db::$fail = true;
    $exception = null;
    try {
        \app\model\B2B\OrderCheckFjx::batchUpsertConfig($rows, ['fjx_config']);
    } catch (\RuntimeException $error) {
        $exception = $error;
    }
    check($exception !== null && $exception->getMessage() === 'database failure', 'database exception propagates');
}
