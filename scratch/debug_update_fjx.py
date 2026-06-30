import requests
import json

def test_update_fjx():
    headers = {
        "authorization": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJpYXQiOjE3NzgwNTI5NjEsIm5iZiI6MTc3ODA1Mjk2MSwiZXhwIjoxODA5ODQ4MTYxLCJ0dGwiOjE4NDEzODQxNjEsImxvZ2luX2V4cCI6MTgwOTU4ODk2MSwibG9naW5faWQiOjU2LCJsb2dpbl91dWlkIjoiS09SOCIsImxvZ2luX21haW5faWQiOjU2LCJsb2dpbl9tYWluX3V1aWQiOiJLT1I4IiwibG9naW5fdHlwZSI6InVzZXIiLCJsb2dpbl9zaXRlIjpbIkIyQiJdLCJsb2dpbl9uYXRpb24iOiJLb3JlYSJ9.s-OurAj0yooRFDNYWczUjry8AZb2u7fFw6zeB0lWkXY",
        "userlogintoken": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJpYXQiOjE3NzgxMjI3MzUsIm5iZiI6MTc3ODEyMjczNSwiZXhwIjoxODA5OTE3OTM1LCJ0dGwiOjE4NDE0NTM5MzUsImxvZ2luX2V4cCI6MTgwOTY1ODczNSwibG9naW5faWQiOjU2LCJsb2dpbl91dWlkIjoiS09SOCIsImxvZ2luX21haW5faWQiOjU2LCJsb2dpbl9tYWluX3V1aWQiOiJLT1I4IiwibG9naW5fdHlwZSI6InVzZXIiLCJsb2dpbl9zaXRlIjpbIkIyQiJdLCJsb2dpbl9uYXRpb24iOiJLb3JlYSJ9.BUMfHiBm2WzoqTOdptC0kFDIOHsMbBm8vAu2jS-_dDk",
        "content-type": "application/json",
        "language": "korean",
        "nation": "Korea"
    }

    item_id_to_find = "783382159597"

    print(f"Step 1: Fetching cart list to find cart_detail_id for item {item_id_to_find}...")
    
    try:
        resp = requests.post("https://api.hubbuyer.com/api_b2b/cart/list", json={}, headers=headers, timeout=10)
        cart_data = resp.json()
        
        found_cart_detail_id = 0
        seller_data_list = cart_data.get('data', {}).get('seller_data', [])
        for seller in seller_data_list:
            items = seller.get('data', [])
            for item in items:
                if str(item.get('item_id')) == item_id_to_find:
                    found_cart_detail_id = int(item.get('id', 0))
                    print(f"-> Found matching item! cart_detail_id = {found_cart_detail_id}")
                    break
            if found_cart_detail_id:
                break
                
        if not found_cart_detail_id:
            print("-> Could not find the item in the cart.")
            return
            
        print(f"\nStep 2: Calling updateCheckFjx with cart_detail_id = {found_cart_detail_id}")
        fjx_payload = {
            "cart_detail_id_arr": [found_cart_detail_id],
            "check_config_uuid": "C25-0617-8133",
            "fjx_config_uuid_arr": ["F25-0821-5931"],
            "user_fjx_config_uuid_arr": []
        }
        
        fjx_resp = requests.post(
            "https://api.hubbuyer.com/api_b2b/cartQuoteStep1/updateCheckFjx", 
            json=fjx_payload, 
            headers=headers, 
            timeout=10
        )
        print(f"Update FJX Result: {fjx_resp.text}")
        
    except Exception as e:
        print(f"Exception: {e}")

if __name__ == "__main__":
    test_update_fjx()
