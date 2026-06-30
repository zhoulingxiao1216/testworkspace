import json
import pymysql

DB = dict(
    host="hk-polar.rwlb.rds.aliyuncs.com",
    port=3306,
    user="xierun888",
    password="xierun@710",
    database="xierun",
    charset="utf8mb4",
    connect_timeout=15,
)

ORDER_NO = "816026061581"


def show(cur, sql, args=()):
    cur.execute(sql, args)
    rows = cur.fetchall()
    return rows


def main():
    conn = pymysql.connect(**DB)
    cur = conn.cursor(pymysql.cursors.DictCursor)

    print("=== orderlist 按 order_id 查 ===")
    rows = show(cur, "SELECT * FROM orderlist WHERE order_id=%s LIMIT 5", (ORDER_NO,))
    print(f"命中 {len(rows)}")
    for r in rows:
        slim = {k: r[k] for k in list(r.keys())[:20]}
        print(json.dumps(slim, ensure_ascii=False, default=str))

    print("\n=== orderdetail 按 order_id / consumer_order_no 查 ===")
    rows = show(
        cur,
        """
        SELECT order_id, order_detail_id, consumer_order_no, item_id, sku,
               order_fjx, order_fjx1, order_fjx2, order_fjx3,
               order_fjx1_fee, order_fjx2_fee, order_fjx3_fee, fjx_status
        FROM orderdetail
        WHERE order_id=%s OR consumer_order_no=%s
        LIMIT 20
        """,
        (ORDER_NO, ORDER_NO),
    )
    print(f"命中 {len(rows)}")
    for r in rows:
        print(json.dumps(r, ensure_ascii=False, default=str))

    order_ids = {ORDER_NO}
    for r in rows:
        if r.get("order_id"):
            order_ids.add(str(r["order_id"]))

    print("\n=== additionalitemcz 附加项明细 ===")
    for oid in order_ids:
        rows = show(
            cur,
            """
            SELECT a.*, t.type_name, t.type_id
            FROM additionalitemcz a
            LEFT JOIN service_fjx_type t ON t.type_id = a.fjxid
            WHERE a.order_id=%s
            ORDER BY a.id
            """,
            (oid,),
        )
        print(f"order_id={oid} 命中 {len(rows)}")
        for r in rows:
            print(json.dumps(r, ensure_ascii=False, default=str))

    print("\n=== service_fjx_order 服务附加项订单 ===")
    for oid in order_ids:
        rows = show(cur, "SELECT * FROM service_fjx_order WHERE order_no=%s OR order_id=%s LIMIT 20", (oid, oid))
        print(f"order_id={oid} 命中 {len(rows)}")
        for r in rows:
            print(json.dumps(r, ensure_ascii=False, default=str))

    print("\n=== 502 贴 / 贴纸 附加项类型 service_fjx_type ===")
    rows = show(
        cur,
        """
        SELECT type_id, type_name, type_group, is_design, status
        FROM service_fjx_type
        WHERE type_id=502
           OR type_name LIKE '%502%'
           OR type_name LIKE '%贴%'
        LIMIT 30
        """,
    )
    for r in rows:
        print(json.dumps(r, ensure_ascii=False, default=str))

    print("\n=== 模糊搜索 orderlist/orderdetail 含 816026061581 ===")
    rows = show(cur, "SELECT order_id, order_status, user_id, order_time FROM orderlist WHERE CAST(order_id AS CHAR) LIKE %s LIMIT 10", (f"%{ORDER_NO[-8:]}%",))
    print(f"orderlist 尾号模糊 {len(rows)}")
    for r in rows:
        print(r)

    conn.close()


if __name__ == "__main__":
    main()
