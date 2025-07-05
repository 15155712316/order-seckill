import requests
import json
import time
import hashlib

# --- 1. 全局基础配置 ---
DEV_CODE = "b2b4378b42df47518fc3511488d6d555"
SECRET_KEY = "69eaf6b39da442809644dc2e3e233cf5"
CHANNEL_ID = 'OP0002'

def get_token():
    """
    调用用户/设备登录接口，获取Token。
    """
    print("--- 正在尝试登录并获取Token ---")
    api_url = "https://openapi.quanma51.com/api/user-server/user/dev/login"
    body_json_str = "{}"
    txntime_ms = str(int(time.time() * 1000))
    
    # 根据规则生成签名
    string_to_sign = body_json_str + SECRET_KEY + txntime_ms
    md5 = hashlib.md5()
    md5.update(string_to_sign.encode('utf-8'))
    sign = md5.hexdigest()

    headers = {
        'channelid': CHANNEL_ID, 'txntime': txntime_ms,
        'devCode': DEV_CODE, 'sign': sign,
        'Content-Type': 'application/json; charset=utf-8'
    }

    try:
        response = requests.post(api_url, data=body_json_str.encode('utf-8'), headers=headers, timeout=10)
        response.raise_for_status()
        response_data = response.json()
        
        if response_data.get("rtnCode") == "000000":
            token = response_data.get("rtnData", {}).get("token")
            if token:
                print(f"✅ 成功获取Token: {token}")
                return token
        print(f"❌ 获取Token失败: {response_data.get('rtnMsg')}")
        return None
    except requests.exceptions.RequestException as e:
        print(f"❌ 请求Token时发生网络错误: {e}")
        return None

def get_order_list(token: str, filters: dict = None):
    """
    调用订单列表接口，可按条件筛选。
    """
    print("\n--- 正在尝试查询订单列表 ---")
    if not token:
        print("错误：必须提供有效的`token`。")
        return None

    api_url = "https://openapi.quanma51.com/api/movie-server/movie/bidding/info/list"
    
    # 根据传入的筛选条件构建请求体
    body_data = filters if filters else {"pageNum": 1, "pageLimit": 10}
    body_json_str = json.dumps(body_data, separators=(',', ':'))
    
    txntime_ms = str(int(time.time() * 1000))

    # 使用新的请求体生成签名
    string_to_sign = body_json_str + SECRET_KEY + txntime_ms
    md5 = hashlib.md5()
    md5.update(string_to_sign.encode('utf-8'))
    sign = md5.hexdigest()

    # 构建包含Token的请求头
    headers = {
        'channelid': CHANNEL_ID, 'txntime': txntime_ms,
        'devCode': DEV_CODE, 'token': token, 'sign': sign,
        'Content-Type': 'application/json; charset=utf-8'
    }
    
    print(f"请求体: {body_json_str}")
    print(f"请求头中的Token: {token[:10]}...") # 仅为演示，打印部分token

    try:
        response = requests.post(api_url, data=body_json_str.encode('utf-8'), headers=headers, timeout=15)
        response.raise_for_status()
        response_data = response.json()
        print("✅ 查询成功!")
        # 仅为演示，打印返回数据的条数
        if response_data.get("rtnCode") == "000000":
             print(f"返回订单数量: {len(response_data.get('rtnData', []))}")
        else:
            print(f"查询出错: {response_data.get('rtnMsg')}")
        return response_data
    except requests.exceptions.RequestException as e:
        print(f"❌ 查询订单时发生网络错误: {e}")
        return None


# --- 主程序: 演示完整的调用流程 ---
if __name__ == "__main__":
    # 步骤1: 获取Token
    access_token = get_token()

    if access_token:
        # 步骤2: 使用获取到的Token调用业务接口
        
        # 示例1: 查询默认订单列表
        get_order_list(access_token)
        
        # 示例2: 按条件筛选订单列表
        search_filters = {
            "cityName": "上海",
            "pageNum": 1,
            "pageLimit": 5 
        }
        get_order_list(access_token, filters=search_filters)