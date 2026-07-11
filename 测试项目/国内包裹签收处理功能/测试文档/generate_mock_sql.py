import os
import random
from datetime import datetime, timedelta

output_file = r"d:\test_workspace\国内包裹签收处理功能\测试文档\003_mock_data.sql"

def generate_mock_data():
    now = datetime.now()
    
    express_inserts = []
    order_inserts = []
    
    express_id_counter = 1
    order_id_counter = 1
    
    def add_package(status_type):
        nonlocal express_id_counter, order_id_counter
        
        # Base data
        package_no = f"SF{random.randint(1000000000, 9999999999)}"
        logistics_id = 1
        logistics_name = "顺丰速运"
        platform = "1688"
        
        send_time = now - timedelta(days=random.randint(3, 5), hours=random.randint(1, 12))
        receipt_time = "NULL"
        takeover_time = "NULL"
        handle_time = "NULL"
        handle_status = 100
        is_private = 0
        is_timeout = 0
        timeout_hours = 0.0
        
        order_no = f"B2B{random.randint(10000000, 99999999)}"
        
        # Scenario logic
        if status_type == "shipped":
            # 仅发货，未签收
            pass
            
        elif status_type == "unprocessed_normal":
            # 已签收，未超时 (12小时前签收)
            rt = now - timedelta(hours=12)
            receipt_time = f"'{rt.strftime('%Y-%m-%d %H:%M:%S')}'"
            
        elif status_type == "unprocessed_timeout":
            # 已签收，已超时 (30小时前签收)
            rt = now - timedelta(hours=30)
            receipt_time = f"'{rt.strftime('%Y-%m-%d %H:%M:%S')}'"
            is_timeout = 1
            timeout_hours = 30.0
            
        elif status_type == "processed":
            # 已处理
            rt = now - timedelta(days=2)
            tt = rt + timedelta(hours=5)
            receipt_time = f"'{rt.strftime('%Y-%m-%d %H:%M:%S')}'"
            takeover_time = f"'{tt.strftime('%Y-%m-%d %H:%M:%S')}'"
            handle_time = f"'{tt.strftime('%Y-%m-%d %H:%M:%S')}'"
            handle_status = 200
            timeout_hours = 5.0
            
        elif status_type == "private":
            # 私人包裹
            rt = now - timedelta(hours=random.randint(1, 10))
            receipt_time = f"'{rt.strftime('%Y-%m-%d %H:%M:%S')}'"
            is_private = 1
            order_no = "" # 私人包裹无订单
            platform = "manual"
            
        # SQL for express
        send_time_val = f"'{send_time.strftime('%Y-%m-%d %H:%M:%S')}'" if status_type != "private" else "NULL"
        
        express_inserts.append(
            f"INSERT INTO `b2b_domestic_express` "
            f"(`id`, `package_no`, `logistics_id`, `logistics_name`, `order_no`, `platform_order_no`, `platform`, "
            f"`is_private`, `send_time`, `receipt_time`, `takeover_time`, `handle_time`, `handle_status`, `is_timeout`, `timeout_hours`) VALUES "
            f"({express_id_counter}, '{package_no}', {logistics_id}, '{logistics_name}', '{order_no}', 'P{order_no}', '{platform}', "
            f"{is_private}, {send_time_val}, {receipt_time}, {takeover_time}, {handle_time}, {handle_status}, {is_timeout}, {timeout_hours});"
        )
        
        # SQL for order association (only if not private)
        if is_private == 0:
            # Maybe 1 or 2 orders per package
            num_orders = random.choices([1, 2], weights=[0.8, 0.2])[0]
            for _ in range(num_orders):
                assoc_order_no = f"B2B{random.randint(10000000, 99999999)}" if _ > 0 else order_no
                order_inserts.append(
                    f"INSERT INTO `b2b_domestic_express_order` "
                    f"(`id`, `express_id`, `package_no`, `order_no`, `platform_order_no`, `seller_open_id`, `user_main_uuid`, `sale_admin_id`, `purchase_admin_id`) VALUES "
                    f"({order_id_counter}, {express_id_counter}, '{package_no}', '{assoc_order_no}', 'P{assoc_order_no}', 'S1001', 'U0001', {random.choice([111, 113, 115])}, {random.choice([110, 112])});"
                )
                order_id_counter += 1
                
        express_id_counter += 1

    # Generate records
    for _ in range(5): add_package("shipped")
    for _ in range(10): add_package("unprocessed_normal")
    for _ in range(5): add_package("unprocessed_timeout")
    for _ in range(20): add_package("processed")
    for _ in range(5): add_package("private")
    
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write("-- ============================================================\n")
        f.write("-- 国内包裹签收处理功能 - Mock 测试数据\n")
        f.write(f"-- 生成时间: {now.strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write("-- 包含场景: 已发货、未处理(含超时)、已处理、私人包裹、一对多关联订单\n")
        f.write("-- ============================================================\n\n")
        
        f.write("TRUNCATE TABLE `b2b_domestic_express`;\n")
        f.write("TRUNCATE TABLE `b2b_domestic_express_order`;\n\n")
        
        f.write("-- 插入主表数据 (b2b_domestic_express)\n")
        f.write("\n".join(express_inserts))
        f.write("\n\n-- 插入订单关联表数据 (b2b_domestic_express_order)\n")
        f.write("\n".join(order_inserts))
        f.write("\n")

if __name__ == "__main__":
    generate_mock_data()
    print(f"Mock SQL successfully generated at: {output_file}")
