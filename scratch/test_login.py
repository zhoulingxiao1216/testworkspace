import requests
import json

url = "https://api.hubbuyer.com/api/login/login"
headers = {
    "accept": "application/json, text/plain, */*",
    "content-type": "application/json",
    "language": "korean",
    "nation": "Korea",
    "logintype": "user"
}
data = {"email":"mxnrq@airsworld.net","password":"123456","code":"","jump_url":""}

response = requests.post(url, json=data, headers=headers)
print("Status Code:", response.status_code)
print("Response Headers:", json.dumps(dict(response.headers), indent=2))
print("Response Body:", response.text)
