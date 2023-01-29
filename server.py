import json
import time
from flask import Flask, request
import requests
from bs4 import BeautifulSoup
import threading
import yaml
import shutil
import os
app = Flask(__name__)


@app.route('/', methods=["POST"])
def post_data():
    data = request.get_json()
    # print(data)
    if data.get('post_type') == 'message':
        receive(data)
    return ('200')


def receive(data):
    if data.get('message')[0] == ".":
        data['message'] = data['message'][1:]
        # print(data)
        if config['vpn']['attitude'] and (data['message'] == "vpn" or data['message'] == "vpn_all"):
            vpn(data)


def send(URL, data):
    print('send')
    requests.post(f"{config['config']['send_address']}{URL}", data)


def vpn(data):
    data_vpn = json.loads(requests.get(
        config['vpn']['request']['info_path'], headers=config['vpn']['request']['info_headers']).text)['data']

    data_vpn2 = json.loads(requests.get(config['vpn']['request']['getSubscribe_path'],
                           headers=config['vpn']['request']['getSubscribe_heasers']).text)['data']

    if data_vpn2['plan']['month_price']:
        ran = "月"
        money = f"{float(data_vpn2['plan']['month_price'])/100}"

    if data_vpn2['plan']['quarter_price']:
        ran = "季"
        money = f"{float(data_vpn2['plan']['quarter_price'])/100}"

    if data_vpn2['plan']['half_year_price']:
        ran = "半年"
        money = f"{float(data_vpn2['plan']['half_year_price'])/100}"

    if data_vpn2['plan']['year_price']:
        ran = "年"
        money = f"{float(data_vpn2['plan']['year_price'])/100}"

    if data_vpn2['plan']['two_year_price']:
        ran = "两年"
        money = f"{float(data_vpn2['plan']['two_year_price'])/100}"

    if data_vpn2['plan']['three_year_price']:
        ran = "三年"
        money = f"{float(data_vpn2['plan']['three_year_price'])/100}"

    if data_vpn2['plan']['onetime_price']:
        ran = "单次"

    if data['message'] == 'vpn_all':
        mes = eval(config['messages']['vpn_all'])

    if data['message'] == 'vpn':
        mes = eval(config['messages']['vpn_short'])

    if data['message_type'] == 'group':
        data = {'group_id': f'{data["group_id"]}',
                'message': f'{mes}'
                }
        send("send_group_msg", data)

    if data['message_type'] == 'private':
        data = {'user_id': f'{data["user_id"]}',
                'message': f'{mes}'
                }
        send("send_private_msg", data)


def vpn_alarm():
    if config['vpn']['alarm'] and config['vpn']['attitude']:
        last_u = False
        alarm_day = True
        while True:
            data_vpn = json.loads(requests.get(
                config['vpn']['request']['getSubscribe_path'], headers=config['vpn']['request']['getSubscribe_heasers']).text)['data']
            u = data_vpn['u']
            if alarm_day:
                if u >= 21474836480:  # 21474836480
                    data = {'group_id': config['vpn']['alarm_group'],
                            'message': eval(config['messages']['vpn_everyday_alarm'])
                            }
                    send("send_group_msg", data)
                    alarm_day = False
            if last_u:
                twentyu = u - last_u
                if twentyu >= 5368709120:  # 5368709120
                    data = {'group_id': config['vpn']['alarm_group'],
                            'message': eval(config['messages']['vpn_twentyu_alarm'])}
                    send("send_group_msg", data)
                last_u = u
            time.sleep(1200)


if __name__ == '__main__':
    global twentyu, config
    twentyu = 0
    if not os.path.exists('config.yml'):
        shutil.copy('config_backup.yml', 'config.yml')
        print('配置文件创建完成')
        input("按回车继续")
    config = yaml.safe_load(open("./config.yml", 'r', encoding='utf-8'))
    threading.Thread(target=vpn_alarm).start()
    app.run(config['config']["receive_address"],
            config['config']["receive_port"], False)
