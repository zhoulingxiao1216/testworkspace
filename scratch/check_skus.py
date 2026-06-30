import json
with open('d:/test_workspace/scratch/item_detail_615186748013.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

if isinstance(data.get('data'), list) and len(data['data']) > 0:
    first = data['data'][0]
    if 'productSkuInfos' in first:
        for sku in first['productSkuInfos']:
            attrs = ' | '.join([a.get('value', '') + ' (' + a.get('valueTrans', '') + ')' for a in sku.get('skuAttributes', [])])
            print(f"Attrs: {attrs} => Price: {sku.get('price')}, Consign: {sku.get('consignPrice')}")
