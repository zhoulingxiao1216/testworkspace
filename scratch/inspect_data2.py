import json
with open('d:/test_workspace/scratch/item_detail_615186748013.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

print(type(data['data'][0]))
if isinstance(data['data'][0], dict):
    print("Keys of list element:", list(data['data'][0].keys()))
    print("Content of list element:", str(data['data'][0])[:500])
