import requests
import json
import logging
import subprocess
import os
import time
import json
import argparse

parser = argparse.ArgumentParser(description='Process some integers.')
parser.add_argument('--filename', type=str, help='the log filename', default='/home/cagcak/codes/scripts/mhrs_checker.log')
parser.add_argument('--level', type=str, help='the log level', default='INFO')
parser.add_argument('--kullaniciAdi', type=int, help='MHRS user id (TCKN)', default=-1)
parser.add_argument('--parola', type=str, help='MHRS user password', default='password')
parser.add_argument('--mhrsIlId', type=int, help='City plate in search', default=-1)
parser.add_argument('--mhrsKlinikId', type=int, help='Hospital department ID', default=103)

args = parser.parse_args()

log_filename = args.filename
kullaniciAdi = args.kullaniciAdi
parola = args.parola
mhrsIlId = args.mhrsIlId
mhrsKlinikId = args.mhrsKlinikId
log_level = getattr(logging, args.level.upper(), logging.INFO)

logging.basicConfig(
    filename=log_filename,
    level=log_level,
    format='%(asctime)s:%(levelname)s:%(message)s'
)

# logging.basicConfig(filename='/home/cagcak/codes/scripts/mhrs_checker.log', level=logging.INFO, 
#                     format='%(asctime)s:%(levelname)s:%(message)s')

TOKEN_FILE = '/home/cagcak/codes/scripts/mhrs_token.json'

login_url = "https://prd.mhrs.gov.tr/api/vatandas/login"
search_url = "https://prd.mhrs.gov.tr/api/kurum-rss/randevu/slot-sorgulama/arama"

credentials = {
    "kullaniciAdi": kullaniciAdi,
    "parola": parola,
    "islemKanali": "VATANDAS_WEB",
    "girisTipi": "PAROLA",
    "captchaKey": None
}

search_payload = {
    "aksiyonId": "200",
    "cinsiyet": "F",
    "mhrsHekimId": -1,
    "mhrsIlId": mhrsIlId,
    "mhrsIlceId": -1,
    "mhrsKlinikId": mhrsKlinikId,
    "mhrsKurumId": -1,
    "muayeneYeriId": -1,
    "tumRandevular": True,
    "ekRandevu": True,
    "randevuZamaniList": []
}

headers = {
    "Accept": "application/json, text/plain, */*",
    "Accept-Encoding": "gzip, deflate, br, zstd",
    "Accept-Language": "tr-TR",
    "Content-Type": "application/json",
    "Origin": "https://mhrs.gov.tr",
    "Referer": "https://mhrs.gov.tr/",
    "Connection": "keep-alive"
}

def show_notification(message, title="MHRS Notification"):
    subprocess.Popen(['notify-send', title, message])

    
def login():
    response = requests.post(login_url, json=credentials)
    if response.status_code == 200:
        token_data = response.json().get('data', {})
        token = token_data.get('jwt')
        token_expiration = time.time() + 3600  # Assume the token expires in 1 hour
        logging.info(f"Login successful. Token: {token}")
        show_notification("Login successful")
        save_token(token, token_expiration)
        return token
    else:
        error_message = f"Login failed. Status code: {response.status_code}, Response: {response.text}"
        logging.error(error_message)
        show_notification(error_message, "MHRS Error")
        return None

def save_token(token, expiration):
    with open(TOKEN_FILE, 'w') as f:
        json.dump({'token': token, 'expiration': expiration}, f)

def load_token():
    if os.path.exists(TOKEN_FILE):
        with open(TOKEN_FILE, 'r') as f:
            data = json.load(f)
            if data['expiration'] > time.time():
                return data['token']
    return None

def search_record(token):
    headers['Authorization'] = f'Bearer {token}'
    response = requests.post(search_url, headers=headers, json=search_payload)
    if response.status_code == 200:
        message = f"Response: {response.text}"
        if not response.json().get('data', {}).get('hastane'):
            logging.info("No records found.")
            show_notification("No records found.")
        else:
            message = json.loads(response.text)["infos"][0]["mesaj"]
            result = '\n'.join(
                map(
                    lambda item: f"{item.get('kurum', {}).get('kurumAdi', '')} {item.get('baslangicZamani', '')}",
                    filter(lambda item: 'kurum' in item and 'kurumAdi' in item['kurum'] and 'baslangicZamani' in item, json.loads(response.text)["data"]["hastane"])
                )
            )
            logging.info("%s\nRecord found!", result)
            show_notification(message, "Record found!")
    elif response.status_code == 401:
        logging.warning("Token expired or invalid. Re-authenticating.")
        show_notification("Token expired or invalid. Re-authenticating.")
        return False
    else:
        error_message = f"Search failed. Status code: {response.status_code}, Response: {response.text}"
        logging.error(error_message)
        show_notification(json.loads(response.text)["errors"][0]["mesaj"], "MHRS Error")
    return True

def main():
    token = load_token()
    if not token:
        token = login()
    if token:
        if not search_record(token):
            token = login()
            if token:
                search_record(token)

if __name__ == "__main__":
    main()