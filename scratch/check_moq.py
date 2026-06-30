import json
with open('d:/test_workspace/scratch/item_detail_615186748013.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

d = data.get('data', {})
if isinstance(d, dict) and 'data' in d:
    inner = d['data']
    print(list(inner.keys()))
    print("min_order_quantity:", inner.get('min_order_quantity'))
    print("amountOnSale:", inner.get('amountOnSale'))
    if 'sale_info' in inner:
        print("sale_info:", str(inner['sale_info'])[:200])
    
    # Check if there is anything in 'fenxiaoSaleInfo' or something else
    print("fenxiao_sale_info:", inner.get('fenxiao_sale_info'))
