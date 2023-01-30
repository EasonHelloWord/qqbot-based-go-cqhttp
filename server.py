import json
import time
from flask import Flask, request
import requests
from bs4 import BeautifulSoup
import threading
import yaml
import shutil
import os
import datetime
app = Flask(__name__)


@app.route('/', methods=["POST"])
def post_data():
    data = request.get_json()
    if data['post_type'] != 'meta_event':
        if data['post_type'] == 'message':
            receive(data)
        log(f"[post_receive] {data}")
    return ('200')


def receive(data):
    if data.get('message')[0] == ".":
        data['message'] = data['message'][1:]
        # print(data)
        if data['message'] == "vpn" or data['message'] == "vpn_all":
            if config['vpn']['attitude']:
                vpn(data)
            else:
                mes = config['messages']['vpn_off']
                send_new(data, mes)


def log(mes, out=True, write=True, type='info'):
    if not os.path.exists('logs'):
        os.makedirs('logs')
    mes = f'[{datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")}] [{type}] {mes}'
    if write:
        open(f'./logs/{time.strftime("%Y-%m-%d.txt",time.localtime())}',
             'a', encoding='utf-8').write(f'{mes}\n')
    if out:
        print(mes)


def send(URL, data):
    requests.post(f"{config['config']['send_address']}{URL}", data)
    log(f"[post_send] {config['config']['send_address']}{URL} {data}")


def send_new(datas, mes):
    if datas['message_type'] == 'group':
        url = f"{config['config']['send_address']}send_group_msg"
        data = {'group_id': f'{datas["group_id"]}',
                'message': f'{mes}'
                }
        requests.post(url, data)

    if datas['message_type'] == 'private':
        url = f"{config['config']['send_address']}send_private_msg"
        data = {'user_id': f'{datas["user_id"]}',
                'message': f'{mes}'
                }
        requests.post(url, data)
    log(f"[post_send] {url} {data}")


def vpn(data):
    data_vpn = json.loads(requests.get(
        config['vpn']['request']['info_path'], headers=config['vpn']['request']['info_headers']).text)['data']

    data_vpn2 = json.loads(requests.get(config['vpn']['request']['getSubscribe_path'],
                           headers=config['vpn']['request']['getSubscribe_heasers']).text)['data']



    if data['message'] == 'vpn_all':
        price_plans = [
        ("月", "month_price"),
        ("季", "quarter_price"),
        ("半年", "half_year_price"),
        ("年", "year_price"),
        ("两年", "two_year_price"),
        ("三年", "three_year_price"),
        ("单次", "onetime_price"),
        ]
        for ran, price_plan in price_plans:
            if data_vpn2['plan'][price_plan]:
                money = f"{float(data_vpn2['plan'][price_plan])/100}"
                break
        mes = eval(config['messages']['vpn_all'])

    if data['message'] == 'vpn':
        mes = eval(config['messages']['vpn_short'])

    send_new(data, mes)


def vpn_alarm():
    if config['vpn']['attitude']:
        global twentyu
        last_u = False
        alarm_day = True
        while True:
            log('请求vpn数据')
            data_vpn = json.loads(requests.get(
                config['vpn']['request']['getSubscribe_path'], headers=config['vpn']['request']['getSubscribe_heasers']).text)['data']
            u = data_vpn['u']
            if config['vpn']['alarm'] and alarm_day:
                if u >= 21474836480:  # 21474836480
                    data = {'group_id': config['vpn']['alarm_group'],
                            'message': eval(config['messages']['vpn_everyday_alarm'])
                            }
                    send("send_group_msg", data)
                    alarm_day = False
            if last_u:
                twentyu = u - last_u
                if config['vpn']['alarm'] and twentyu >= 5368709120:  # 5368709120
                    data = {'group_id': config['vpn']['alarm_group'],
                            'message': eval(config['messages']['vpn_twentyu_alarm'])}
                    send("send_group_msg", data)
            last_u = u
            time.sleep(1200)  # 1200


if __name__ == '__main__':
    global twentyu, config
    twentyu = 0
    if not os.path.exists('config.yml'):
        shutil.copy('config_backup.yml', 'config.yml')
        log('配置文件创建完成')
        input("按回车继续")
    config = yaml.safe_load(open("./config.yml", 'r', encoding='utf-8'))
    threading.Thread(target=vpn_alarm).start()
    app.run(config['config']["receive_address"],
            config['config']["receive_port"], False)
