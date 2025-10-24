import os
import re
import sys
import time
from datetime import datetime

import requests

#------------------------define logging-----------------------------------

def log(text):
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    LOG_FILE = os.path.join(BASE_DIR, "log.txt")
    if not os.path.exists(LOG_FILE):
        with open(LOG_FILE, "w") as f:
            f.write("")

    now = datetime.now()
    formatted_time = now.strftime("%d/%b/%Y %H:%M:%S.%f")[:-4]
    output = f"[{formatted_time}] > {text}"
    fd = os.open(LOG_FILE, os.O_WRONLY | os.O_CREAT | os.O_APPEND)
    os.write(fd, f"{output}\n".encode("utf-8"))
    os.close(fd)

#-------------------------get Config file---------------------------------

def parse_line(line, expected_keyword):
    try:
        keyword, value = map(str.strip, line.split('=', 1))
    except BaseException as e:
            raise ValueError(f"{expected_keyword} line invalid - {e}")

    if keyword != expected_keyword or not value:
        raise ValueError(f"{keyword} line invalid")

    if expected_keyword == 'DOMAINS':
        try:
            value = value.split(',') if ',' in value else [value]
            value = [s.strip().strip("'") for s in value]
            if all(v != "" for v in value):
                return value
            else:
                raise ValueError(f"{keyword} line invalid")

        except BaseException as e:
            raise ValueError(f"{keyword} line invalid - {e}")

    else:
        try:
            if not re.fullmatch(r"\s*'[^']*'\s*", value):
                raise ValueError(f"{keyword} line invalid")
            value = value.strip().strip("'")
            if value != "":
                return value
            else:
                raise ValueError(f"{keyword} line invalid")
        except BaseException as e:
            raise ValueError(f"{keyword} line invalid - {e}")

def read_config_file():
    try:
        BASE_DIR = os.path.dirname(os.path.abspath(__file__))
        CONF_FILE = os.path.join(BASE_DIR, "updater.conf")
        if not os.path.exists(CONF_FILE):
            raise ValueError(f"config file 'updater.conf' is missing")
        with open(CONF_FILE, 'r') as f:
            lines = f.readlines()

        if len(lines) != 3:
            raise ValueError("config file format is invalid")

        conf_dict = {
            'API_KEY': "",
            'SECRET_KEY': "",
            'DOMAINS': ""
        }

        for idx, (key, _) in enumerate(conf_dict.items()):
            conf_dict[key] = parse_line(lines[idx], key)

        return conf_dict
    except BaseException as e:
        log(f"Error while reading config file - {e}")
        sys.exit()

conf = read_config_file()

#-------------------------main process--------------------------------

def get_public_ip():
    try:
        response = requests.get('https://api.ipify.org?format=json')
        response.raise_for_status()
        ip = response.json()['ip']
        return ip.strip()
    except requests.RequestException as e:
        log(f"public ip service couldn't be reach - {e}")


def update_ip(new_ip, discrepancies = None):
    # update IPs on porkbun


    domains = discrepancies if discrepancies else conf['DOMAINS']

    for domain in domains:
        url_parts = domain.split(".")
        url = f'https://api.porkbun.com/api/json/v3/dns/editByNameType/{url_parts[1]}.{url_parts[2]}/A/{url_parts[0]}'
        payload = {
            'secretapikey': conf['SECRET_KEY'],
            'apikey': conf['API_KEY'],
            "content": new_ip,
            "ttl": "600"
        }
        response = requests.post(url, json=payload)
        if response.status_code == 200:
            log(f"{domain} IP successfully updated to : {new_ip}")
        else:
            log(f"{domain} IP couldn't be updated to : {new_ip} - {response.status_code}")


def get_ips():
    #check current IPs on porkbun to see if they fit your IP

    #define api payload
    payload = {
        'secretapikey': conf['SECRET_KEY'],
        'apikey': conf['API_KEY']
    }

    IPs = {}


    for domain in conf['DOMAINS']:
        url_parts = domain.split(".")
        url = f'https://api.porkbun.com/api/json/v3/dns/retrieveByNameType/{url_parts[1]}.{url_parts[2]}/A/{url_parts[0]}'
        response = requests.post(url, json=payload)
        if response.status_code == 200:
            data = response.json()
            record = data.get('records')
            ip = record[0]["content"]
            IPs[domain] = ip.strip()
        else:
            log(f"{domain} IP couldn't be retrieved")

    return IPs


def normal_check():
    #check if your public ip as change compare to local
    try:
        global current_ip
        ip = get_public_ip()
        if current_ip != ip:
            log(f"IP change detected - starting IP update")
            update_ip(ip)
            current_ip = ip
    except Exception as e:
        log(f"Error while checking for IP - {e}")

def error_check():
    try:
        ip = get_public_ip()
        IPs = get_ips()
        discrepancies = [key for key, value in IPs.items() if value != ip]
        if len(discrepancies) > 0:
            log(f"IP discrepancy detected - starting IP update")
            update_ip(ip, discrepancies)
    except Exception as e:
        log(f"Error while checking for discrepancy - {e}")

def ip_init():
    global current_ip
    current_ip = get_public_ip()



if __name__ == "__main__":
    global current_ip
    try:
        ip_init()
        error_check()

        normal_time = error_time = time.monotonic()

        log("Application started successfully")

        while True:
            now = time.monotonic()

            if int(now - normal_time) >= 60:
                normal_check()
                normal_time = now

            if now - error_time >= 1800:
                error_check()
                error_time = now

            time.sleep(0.1)
    except BaseException as e:
        log(f"Error during execution - {e}")

