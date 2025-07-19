import requests

headers = {
    'accept': 'application/json, text/plain, */*',
    'accept-language': 'zh-CN,zh;q=0.9',
    'content-type': 'application/json;charset=UTF-8',
    'origin': 'https://www.qianyinghui.net',
    'priority': 'u=1, i',
    'referer': 'https://www.qianyinghui.net/',
    'sec-ch-ua': '"Not)A;Brand";v="8", "Chromium";v="138", "Google Chrome";v="138"',
    'sec-ch-ua-mobile': '?0',
    'sec-ch-ua-platform': '"Windows"',
    'sec-fetch-dest': 'empty',
    'sec-fetch-mode': 'cors',
    'sec-fetch-site': 'cross-site',
    'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36',
    'user-token': 'eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJkYXRhIjp7InVzZXJfaWQiOjExNTE4NzcsInRpY2tldCI6dHJ1ZSwid2ViX3Rva2VuIjoiNnZPU014IiwiZXhwIjoiMjAyNC0wMS0yMyJ9LCJpc3MiOiJtYW5nbyIsImlhdCI6MTc1MjIwMTQ1OCwiZXhwIjoxNzU0NzkzNDU4fQ.ZVdib1z1qfs7Q2pFGHYDFJe2cpXiV-KksrF9fNFx0lY',
    'zhua-ch-ua': 'zh',
}

json_data = {
    'page': 1,
    'page_size': 200,
    'sort_field': 'created_at',
    'sort_order': 'desc',
    'source': 'pc',
}

response = requests.post('https://supplier.mgmovie.net/v2/api/67d77db66adac', headers=headers, json=json_data,verify=False)
print(response.text)

# Note: json_data will not be serialized by requests
# exactly as it was in the original request.
#data = '{"page":1,"page_size":20,"sort_field":"created_at","sort_order":"desc","source":"pc"}'
#response = requests.post('https://supplier.mgmovie.net/v2/api/67d77db66adac', headers=headers, data=data)