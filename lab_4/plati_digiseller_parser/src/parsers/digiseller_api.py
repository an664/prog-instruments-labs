import requests
import hashlib
import time
import logging

logging.basicConfig(filename='logs/digiseller_api.log', level=logging.INFO)

def get_token(seller_id, api_key):
    timestamp = int(time.time())
    sign = hashlib.sha256((api_key + str(timestamp)).encode()).hexdigest()
    
    data = {
        "seller_id": seller_id,
        "timestamp": timestamp,
        "sign": sign
    }
    
    response = requests.post("https://api.digiseller.ru/api/apilogin", json=data)
    if response.status_code == 200:
        return response.json()['token']
    else:
        logging.error(f"Failed to get token: {response.text}")
        return None

def get_ad_data(token, owner):
    headers = {
        'Accept': 'application/json'
    }
    params = {
        'token': token,
        'owner': owner,
        'lang': 'ru-RU'
    }
    response = requests.get("https://api.digiseller.ru/api/rekl", headers=headers, params=params)
    if response.status_code == 200:
        return response.json()
    else:
        logging.error(f"Failed to get ad data: {response.text}")
        return None

def process_digiseller_data(config):
    seller_id = config['digiseller_seller_id']
    api_key = config['digiseller_api_key']
    owner = config['digiseller_owner']
    
    logging.info(f"Attempting to get token for seller_id: {seller_id}")
    token = get_token(seller_id, api_key)
    if token:
        logging.info("Successfully obtained token, fetching ad data")
        return get_ad_data(token, owner)
    logging.error("Failed to obtain token")
    return None
