import json
with open('d:/test_workspace/scratch/item_detail_615186748013.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

if 'data' in data:
    d = data['data']
    print("Type of data['data']:", type(d))
    if isinstance(d, dict):
        print("Keys of dict:", list(d.keys()))
        if 'data' in d:
            print("Keys of d['data']:", list(d['data'].keys()))
            if 'productSkuInfos' in d['data']:
                for sku in d['data']['productSkuInfos']:
                    attrs = ' | '.join([a.get('value', '') + ' (' + a.get('valueTrans', '') + ')' for a in sku.get('skuAttributes', [])])
                    print(f"Attrs: {attrs} => Price: {sku.get('price')}, Consign: {sku.get('consignPrice')}")
