import json
with open('d:/test_workspace/scratch/item_detail_615186748013.json', 'r', encoding='utf-8') as f:
    data = json.load(f)
for sku in data.get('data', {}).get('data', {}).get('productSkuInfos', []):
    attrs = ' '.join([a.get('value', '') for a in sku.get('skuAttributes', [])])
    if 'silver 2.5*12mm' in attrs or '2.5*12mm' in attrs:
        print(f"Attrs: {attrs}")
        print(f"Price: {sku.get('price')}")
        print(f"ConsignPrice: {sku.get('consignPrice')}")
        print(f"JxhyPrice: {sku.get('jxhyPrice')}")
        print(sku)
