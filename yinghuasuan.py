import requests

headers = {
    'Accept': '*/*',
    'Accept-Language': 'zh-CN,zh;q=0.9',
    'Authorization': 'Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJpc3MiOiJodWIueWluZ2h1YXN1YW4uY29tIiwiYXVkIjoiaHViLnlpbmdodWFzdWFuLmNvbSIsImlhdCI6MTc1MjExMjkzMywibmJmIjoxNzUyMTEyOTMzLCJleHAiOjE3NTI3MTc3MzMsImV4dGVuZCI6eyJpZCI6MjQ3OCwibW9iaWxlIjoiMTUxNTU3MTIzMTYiLCJjbGllbnQiOiJNT0JJTEVfOTMifX0.5_EfFj1U7E0XzXNxQXAOf8ER5uQ5Yb4HPak9bPErzbk',
    'Connection': 'keep-alive',
    'Content-Type': 'application/json',
    'Origin': 'https://hub.yhs.cn',
    'Referer': 'https://hub.yhs.cn/',
    'Sec-Fetch-Dest': 'empty',
    'Sec-Fetch-Mode': 'cors',
    'Sec-Fetch-Site': 'cross-site',
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36',
    'client-type': '3',
    'sec-ch-ua': '"Not)A;Brand";v="8", "Chromium";v="138", "Google Chrome";v="138"',
    'sec-ch-ua-mobile': '?0',
    'sec-ch-ua-platform': '"Windows"',
}

json_data = {
    'city_name': '',
    'film_id': '',
    'seat_num': '',
    'accept_change_seat': '',
    'net_price': '',
    'keywords': '',
    'sort': 'desc',
}

response = requests.post('https://merchant-api.yinghuasuan.com/broker/v1/invitation/list', headers=headers, json=json_data,verify=False)
print(response.text)

# Note: json_data will not be serialized by requests
# exactly as it was in the original request.
#data = '{"city_name":"","film_id":"","seat_num":"","accept_change_seat":"","net_price":"","keywords":"","sort":"desc"}'
#response = requests.post('https://merchant-api.yinghuasuan.com/broker/v1/invitation/list', headers=headers, data=data)