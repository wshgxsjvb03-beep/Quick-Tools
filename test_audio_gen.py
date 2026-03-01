import requests

def check_my_avatars():
    url = "https://api.heygen.com/v2/photo_avatar/list"
    headers = {
        "accept": "application/json",
        "x-api-key": "sk_V2_hgu_kBH6KPzeEDa_fZMQdhkhj0JC8ilYNUPAOolWKCkgXqYv"
    }
    response = requests.get(url, headers=headers)
    print(f"状态码: {response.status_code}")
    print(f"返回内容: {response.text}")

check_my_avatars()