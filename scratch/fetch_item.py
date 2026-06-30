import requests, json

url = "https://api.hubbuyer.com/api_b2b/item/detail"
headers = {
    'accept': 'application/json, text/plain, */*',
    'content-type': 'application/json',
    'language': 'korean',
    'nation': 'Korea',
}
data = {
    "url": "https://detail.1688.com/offer/615186748013.html"
}

response = requests.post(url, json=data, headers=headers)
with open('d:/test_workspace/scratch/item_detail_615186748013.json', 'w', encoding='utf-8') as f:
    f.write(response.text)
print('Response saved.')
