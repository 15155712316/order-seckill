import requests

cookies = {
    '_c_WBKFRo': 'CbkeIVy2jCMFQKiSKiNZIOjL0rfGmOzcfROYTyCm',
    'PHPSESSID': '37j7uepablh17vn6rkh6k1pute',
}

headers = {
    'accept': 'application/json, text/plain, */*',
    'accept-language': 'zh-CN,zh;q=0.9',
    'content-type': 'application/x-www-form-urlencoded',
    'origin': 'https://hahapiao.cn',
    'priority': 'u=1, i',
    'referer': 'https://hahapiao.cn/pc/',
    'sec-ch-ua': '"Not)A;Brand";v="8", "Chromium";v="138", "Google Chrome";v="138"',
    'sec-ch-ua-mobile': '?0',
    'sec-ch-ua-platform': '"Windows"',
    'sec-fetch-dest': 'empty',
    'sec-fetch-mode': 'cors',
    'sec-fetch-site': 'same-origin',
    'token': '64932f01040374d3a7d3c9438a48c5178',
    'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36',
    # 'cookie': '_c_WBKFRo=CbkeIVy2jCMFQKiSKiNZIOjL0rfGmOzcfROYTyCm; PHPSESSID=37j7uepablh17vn6rkh6k1pute',
}

data = {
    'cinemaName': '乐松',
    'limit': '15',
    'cinema[0]': '%乐松%',
}

response = requests.post('https://hahapiao.cn/api/Synchro/pcToList', cookies=cookies, headers=headers, data=data)
print(response.text)    