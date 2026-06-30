import json
with open('d:/test_workspace/scratch/item_detail_615186748013.json', 'r', encoding='utf-8') as f:
    data = json.load(f)
for sku in data.get('data', {}).get('data', {}).get('productSkuInfos', []):
    attrs = ' | '.join([a.get('value', '') + ' (' + a.get('valueTrans', '') + ')' for a in sku.get('skuAttributes', [])])
    print(f"Attrs: {attrs} => Price: {sku.get('price')}, Consign: {sku.get('consignPrice')}")
