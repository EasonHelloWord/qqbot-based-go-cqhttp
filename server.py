import json
import time
import traceback
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
        if data['message'][:4] == 'bill':
            if data['message'] == 'bill':
                send_new(
                    data, '用法：.bill&<账单名称>&<操作：read/add/remove/back>&参数\nread:<标题>&<收入>&<支出>&<备注>\n其余皆为订单id')
            else:
                message = data['message'].split('&amp;')
                log(f"[bill] 账单更改，用户指令: {message}")
                if len(message) <= 2:
                    mes = '[error] 参数不足'
                    message = [None, None, None]
                else:
                    bills = Bill(message[1])
                if message[2] == 'read':
                    try:
                        id = message[3]
                    except:
                        id = None
                    mes = bills.read(id)
                if message[2] == 'add':
                    if len(message) <= 6:
                        mes = '[error] 参数不足'
                    else:
                        datas = {
                            'topic': message[3], 'in': message[4], 'out': message[5], 'note': message[6]}
                        mes = bills.add(datas, data['user_id'])
                if message[2] == 'remove':
                    try:
                        id = message[3]
                    except:
                        id = None
                    mes = bills.remove(id)
                if message[2] == 'back':
                    try:
                        id = message[3]
                    except:
                        id = None
                    mes = bills.back(id)
                send_new(data, mes)


def log(mes, out=True, write=True, type='info'):
    if not os.path.exists('logs'):
        os.makedirs('logs')
    mes = f'[{datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")}] [{type}] {mes}'
    if write:
        open(f'./logs/{time.strftime(f"%Y-%m-%d.{os.getpid()}.txt",time.localtime())}',
             'a', encoding='utf-8').write(f'{mes}\n')
    if out:
        print(mes)
    if type == 'error':
        os._exit(2)


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


class Bill:
    def __init__(self, name):
        self.name = name
        self.path = f'bill/{name}.json'
        if not os.path.exists('bill'):
            os.mkdir('bill')
        if not os.path.exists(self.path):
            open(self.path, "w",
                 encoding='utf-8').write('{"main":{},"backup":{}}')
        self.data = json.load(open(self.path, 'r', encoding='utf-8'))

    def read(self, id=None):
        if id:
            id = str(id)
            mes = f"{self.name}:\nID  状态  标题  收入  支出  总计  备注  时间  用户ID\n"
            if id in self.data['main'].keys():
                state = '正常'
                this_data = self.data['main'][id]
            elif id in self.data['backup'].keys():
                state = '挂起'
                this_data = self.data['backup'][id]
            else:
                return ('未找到此ID')
            mes = f"{mes}{id}  {state}  {this_data['topic']}  {this_data['in']}  {this_data['out']}  {this_data['all']}  {this_data['note']}  {time.strftime('%Y-%m-%d %H:%M:%S',time.localtime(this_data['add_time']))}  {this_data['user_id']}"
        else:
            mes = f"{self.name}:\nID  状态  标题  收入  支出  总计  备注  时间\n"
            for id, this_data in self.data['main'].items():
                mes = f"{mes}{id}  正常  {this_data['topic']}  {this_data['in']}  {this_data['out']}  {this_data['all']}  {this_data['note']}  {time.strftime('%Y-%m-%d %H:%M:%S',time.localtime(this_data['add_time']))}\n"
            for id, this_data in self.data['backup'].items():
                mes = f"{mes}{id}  挂起  {this_data['topic']}  {this_data['in']}  {this_data['out']}  {this_data['all']}  {this_data['note']}  {time.strftime('%Y-%m-%d %H:%M:%S',time.localtime(this_data['add_time']))}\n"
        return (mes)

    def add(self, data, userid):
        time_now = time.time()
        id = len(self.data["main"].keys())+len(self.data["backup"].keys())+1
        self.data['main'][f'{id}'] = {"topic": data['topic'],
                                      "in": data['in'], "out": data['out'], "all": int(data['in'])-int(data['out']), "note": data["note"], "add_time": time_now, "user_id": userid}
        with open(self.path, 'w', encoding='utf-8') as w:
            json.dump(self.data, w, ensure_ascii=False, indent=4)
        return ('操作成功')

    def remove(self, id):
        id = str(id)
        if id in self.data['main'].keys():
            this_data = self.data['main'][id]
            del self.data['main'][id]
            self.data['backup'][id] = this_data
            with open(self.path, 'w', encoding='utf-8') as w:
                json.dump(self.data, w, ensure_ascii=False, indent=4)
            return ('操作成功')
        else:
            return ('未找到此ID')

    def back(self, id):
        id = str(id)
        if id in self.data['backup'].keys():
            this_data = self.data['backup'][id]
            del self.data['backup'][id]
            self.data['main'][id] = this_data
            with open(self.path, 'w', encoding='utf-8') as w:
                json.dump(self.data, w, ensure_ascii=False, indent=4)
            return ('操作成功')
        else:
            return ('未找到此ID')


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
            data_vpn = json.loads(requests.get(
                config['vpn']['request']['getSubscribe_path'], headers=config['vpn']['request']['getSubscribe_heasers']).text)['data']
            log(f'请求到vpn数据{data_vpn}')
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
    log('===================程序启动===================')
    global twentyu, config
    twentyu = 0
    if not os.path.exists('config.yml'):
        log('未检测到配置，将重新生成配置文件。', type='warn')
        try:
            shutil.copy('config_backup.yml', 'config.yml')
        except:
            log(traceback.format_exc(), type='error')
        log('配置文件创建完成')
        input("按回车继续")
    log('===================读取配置===================')
    try:
        config = yaml.load(open("./config.yml", 'r', encoding='utf-8'))
    except:
        log(traceback.format_exc(), type='error')
    else:
        log('successful!')
    threading.Thread(target=vpn_alarm).start()
    app.run(config['config']["receive_address"],
            config['config']["receive_port"], False)
