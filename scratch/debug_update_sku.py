import requests
import json

def test_add_sku():
    headers = {
        "authorization": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJpYXQiOjE3NzgwNTI5NjEsIm5iZiI6MTc3ODA1Mjk2MSwiZXhwIjoxODA5ODQ4MTYxLCJ0dGwiOjE4NDEzODQxNjEsImxvZ2luX2V4cCI6MTgwOTU4ODk2MSwibG9naW5faWQiOjU2LCJsb2dpbl91dWlkIjoiS09SOCIsImxvZ2luX21haW5faWQiOjU2LCJsb2dpbl9tYWluX3V1aWQiOiJLT1I4IiwibG9naW5fdHlwZSI6InVzZXIiLCJsb2dpbl9zaXRlIjpbIkIyQiJdLCJsb2dpbl9uYXRpb24iOiJLb3JlYSJ9.s-OurAj0yooRFDNYWczUjry8AZb2u7fFw6zeB0lWkXY",
        "userlogintoken": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJpYXQiOjE3NzgxMjI3MzUsIm5iZiI6MTc3ODEyMjczNSwiZXhwIjoxODA5OTE3OTM1LCJ0dGwiOjE4NDE0NTM5MzUsImxvZ2luX2V4cCI6MTgwOTY1ODczNSwibG9naW5faWQiOjU2LCJsb2dpbl91dWlkIjoiS09SOCIsImxvZ2luX21haW5faWQiOjU2LCJsb2dpbl9tYWluX3V1aWQiOiJLT1I4IiwibG9naW5fdHlwZSI6InVzZXIiLCJsb2dpbl9zaXRlIjpbIkIyQiJdLCJsb2dpbl9uYXRpb24iOiJLb3JlYSJ9.BUMfHiBm2WzoqTOdptC0kFDIOHsMbBm8vAu2jS-_dDk",
        "content-type": "application/json"
    }

    item_id_to_find = "783382159597"
    target_sku = "ar-rg-006r-siv-18-r2"

    print(f"Step 1: Fetching cart list to find cart_detail_id for item {item_id_to_find}...")
    
    try:
        resp = requests.post("https://api.hubbuyer.com/api_b2b/cart/list", json={}, headers=headers, timeout=10)
        cart_data = resp.json()
        
        if cart_data.get('code') not in [0, 200]:
            print(f"Error fetching cart: {cart_data}")
            return
            
        found_cart_detail_id = 0
        
        # Parse seller_data array
        seller_data_list = cart_data.get('data', {}).get('seller_data', [])
        for seller in seller_data_list:
            items = seller.get('data', [])
            for item in items:
                if str(item.get('item_id')) == item_id_to_find:
                    found_cart_detail_id = int(item.get('id', 0))
                    print(f"-> Found matching item in cart! cart_detail_id = {found_cart_detail_id}")
                    break
            if found_cart_detail_id:
                break
                
        if not found_cart_detail_id:
            print("-> Could not find the item in the cart. Did the add1688 API succeed earlier?")
            return
            
        print(f"\nStep 2: Calling updateSkuNumberData with cart_detail_id = {found_cart_detail_id}")
        payload = {
            "cart_detail_id": found_cart_detail_id,
            "custom_sku": {"sku": target_sku},
            "amazon_sku": {
                "sku": target_sku,
                "url": "",
                "asin": "",
                "fnsku": "",
                "child_id": ""
            },
            "self_sku": []
        }
        
        update_resp = requests.post(
            "https://api.hubbuyer.com/api_b2b/cartQuoteStep1/updateSkuNumberData", 
            json=payload, 
            headers=headers, 
            timeout=10
        )
        print(f"Update Result: {update_resp.text}")
        
    except Exception as e:
        print(f"Exception: {e}")

if __name__ == "__main__":
    test_add_sku()
