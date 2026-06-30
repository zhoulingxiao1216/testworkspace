import requests, json

headers = {
    'authorization': 'eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJpYXQiOjE3NzgwNTI5NjEsIm5iZiI6MTc3ODA1Mjk2MSwiZXhwIjoxODA5ODQ4MTYxLCJ0dGwiOjE4NDEzODQxNjEsImxvZ2luX2V4cCI6MTgwOTU4ODk2MSwibG9naW5faWQiOjU2LCJsb2dpbl91dWlkIjoiS09SOCIsImxvZ2luX21haW5faWQiOjU2LCJsb2dpbl9tYWluX3V1aWQiOiJLT1I4IiwibG9naW5fdHlwZSI6InVzZXIiLCJsb2dpbl9zaXRlIjpbIkIyQiJdLCJsb2dpbl9uYXRpb24iOiJLb3JlYSJ9.s-OurAj0yooRFDNYWczUjry8AZb2u7fFw6zeB0lWkXY',
    'userlogintoken': 'eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJpYXQiOjE3NzgxMjI3MzUsIm5iZiI6MTc3ODEyMjczNSwiZXhwIjoxODA5OTE3OTM1LCJ0dGwiOjE4NDE0NTM5MzUsImxvZ2luX2V4cCI6MTgwOTY1ODczNSwibG9naW5faWQiOjU2LCJsb2dpbl91dWlkIjoiS09SOCIsImxvZ2luX21haW5faWQiOjU2LCJsb2dpbl9tYWluX3V1aWQiOiJLT1I4IiwibG9naW5fdHlwZSI6InVzZXIiLCJsb2dpbl9zaXRlIjpbIkIyQiJdLCJsb2dpbl9uYXRpb24iOiJLb3JlYSJ9.BUMfHiBm2WzoqTOdptC0kFDIOHsMbBm8vAu2jS-_dDk',
    'content-type': 'application/json'
}

resp = requests.post('https://api.hubbuyer.com/api_b2b/cart/list', json={}, headers=headers)
data = resp.json()

for seller in data.get('data', {}).get('seller_data', []):
    for item in seller.get('data', []):
        print(f"ID: {item.get('id')}, ItemID: {item.get('item_id')}")
        
        # In cart API, the check configs are usually in 'check_fjx_remark' or something similar
        fjx = item.get('check_fjx', {})
        if fjx:
            print(f"  -> Check Fjx: {fjx}")
