import requests,base64
import logging
import json,re,threading
import random,time
from concurrent.futures import ThreadPoolExecutor,wait,ALL_COMPLETED

def loadInfo():
    info={}
    with open('info.txt') as f:
        data=f.read()
    for i in data.split('\n'):
        line=i.split('=')
        if len(line)==2:
            info.update({line[0]:line[1]})
    return info


def OCR(img:bytes):

    verifycode=base64.b64encode(img).decode()
    data = {"softwareId": 15938, "softwareSecret": "12meeHZInDL2S8irCzZPUvJ3AoWz7n77oOVNLy8Q",
            "username": "wzp123456", "password": "wzp123456.", "captchaData": verifycode, "captchaType": 1001,
            "captchaMinLength": 4, "captchaMaxLength": 5, "workerTipsId": 0}
    try:
        req = requests.post(url='https://v2-api.jsdama.com/upload', json=data).json()
        if req['code'] == 0:
            code = req['data']['recognition']
            captchaId = req['data']['captchaId']
            return code
        else:
            return False
    except:
        return False



class MMSH():
    def __init__(self, username, password):
        self._username = username
        self._password = password
        self.session = requests.session()
        self._work=False
        self._status=False


    @property
    def work(self):
        return self._work

    @property
    def status(self):
        return self._status

    def _req(self, method, url, params=None, data=None, header=None, ):
        if not header:
            header = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/53.0.2785.116 Safari/537.36 QBCore/3.53.1159.400 QQBrowser/9.0.2524.400 Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/39.0.2171.95 Safari/537.36 MicroMessenger/6.5.2.501 NetType/WIFI WindowsWechat'}
        req = self.session.request(method, url=url, params=params, data=data, headers=header)
        if req.headers.get('Content-Type', None) == 'application/json; charset=utf-8':
            return req.json()
        return req.content

    def login(self):
        result = self._req('POST',
                           f'http://mmyx.mmsh.sinopec.com/Booking/LoginCoporationByBillNo?BillNo={self._username}&BillPwd={self._password}')
        if result['Status']:
            logging.info('登录成功')
            return True
        else:
            info = result['Explain']
            logging.error(info)
            return False

    def getOrders(self):
        url = 'http://mmyx.mmsh.sinopec.com/Booking/GetLadingBillByCoporation'
        result = self._req('POST', url=url)
        ps = []
        i = 0
        for p in result:
            i += 1
            q=p['Quantity']-p['ShipQty']
            ps.append({'序号': i, '产品名称:': p['ProductName'], 'ID': p['ID'], 'ProductID': p['ProductID'],
                       'QYShipPlaceID': p['QYShipPlaceID'],'TaskUndoneQty':q},)
        return ps

    def getLading(self, order):
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/53.0.2785.116 Safari/537.36 QBCore/3.53.1159.400 QQBrowser/9.0.2524.400 Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/39.0.2171.95 Safari/537.36 MicroMessenger/6.5.2.501 NetType/WIFI WindowsWechat',
            'Referer': f'http://mmyx.mmsh.sinopec.com/Booking/BookingOrderInfoM?productID={order["ProductID"]}&qYShipPlaceID={order["QYShipPlaceID"]}&Id={order["ID"]}'}
        req = self._req('GET', f"http://mmyx.mmsh.sinopec.com/Booking/GetLadingBillByID?ID={order['ID']}",
                        header=headers)
        return req

    def getVerifyCode(self):
        try:
            url = f'http://mmyx.mmsh.sinopec.com/WXHandler/Codeimg.aspx?{random.randint(2000000, 9999999)}'
            req = self._req('GET',url=url)
            return req
        except:
            return False

    def SaveRecord(self,code,order,planId,info):  # 提交预约
        if self._work or self._status:
            return
        url = 'http://mmyx.mmsh.sinopec.com/Booking/SaveBookingRecord'
        params = {'OpenID': 'opPd8w0N0ZqItyL1njVOHQN64QEE', 'WxName': 'qingting',
                  'PlanID': planId,
                  'LadingBillID': order['ID'], 'BookingDate': info['date'], 'Quantity': info['weight'],
                  'MobilePhone': info['phone'], 'DriverName':info['name'], 'PreTruckNo': info['card'], 'AfterTruckNo': None,
                  'IDCardNO': info['idnum'], 'InpCode': code,
                  'IsMerge': '0'}
        try:
            result=self._req('GET',url=url,params=params)
            if result['Status']==False:
                logging.warning(f'预约失败,提示信息:{result["Explain"]}')
                if result["Explain"]=='预约数量不能大于剩余可预约量！':
                    self._status=True
                if result["Explain"]=='选定的预约提货时间预约车数已满，请选下一时段！':
                    self._status=True
            else:
                print(result)
                self._work=True
                logging.warning(f'预约成功:{round(time.time()*1000)}')
            return result
        except Exception as e:
            pass

    def getPlanList(self,order,info):
        url = 'http://mmyx.mmsh.sinopec.com/Booking/GetBookingPlanList'
        params = {'ProductID': order['ProductID'], 'ShipPlaceID': order['QYShipPlaceID'],'BookingDate': info['date'],
                  'PreTruckNo': info['card'],'LadingBillID':order['ID']}
        req = self._req('GET', url=url, params=params)

        result=[]
        a=0
        try:
            for i in req:
                a+=1
                Now=re.search('(\d+)',i['NowDate']).group(1)
                Begin=re.search('(\d+)',i['BeginTime']).group(1)
                BeginTime=time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(eval(Begin) / 1000))
                End = re.search('(\d+)', i['EndTime']).group(1)
                EndTime = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(eval(End) / 1000))
                MaxBookNum=i['MaxBookNum']
                BookedNum = i['BookedNum']
                if a<=2:
                    Now=(eval(Now)+43200000) #前两个时间段,前天晚上就可以开始抢了
                    Now=str(Now)

                freeTime=(round(eval(Now))+9000000)-eval(Begin)
                freeTime=round(freeTime/1000,1)
                i['IsBooking']=freeTime
                ID=i['ID']
                _={'序号':a,'时间':BeginTime+'-'+EndTime,'最大预约数:':MaxBookNum,'剩余预约数':MaxBookNum-BookedNum,'ID':ID,'IsBooking':i['IsBooking']}
                result.append(_)
            return result
        except Exception as e:
            return False

def API_Task(info):
    info = loadInfo()
    print(info)

    Pool = ThreadPoolExecutor(max_workers=10)

    logging.basicConfig(level=logging.INFO)
    obj = MMSH(info['账号'], info['密码'])
    ##test
    while True:
        img = obj.getVerifyCode()
        if not img:
            continue
        code = OCR(img=img)
        if not code:
            continue
        with open(f'{code}.jpg', 'wb') as f:
            f.write(img)
        break
    exit()
    # end
    if not obj.login():
        exit('登录失败')

    orders = obj.getOrders()
    for i in orders:
        print(i)

    num = eval(input('输入序号进行下一步:'))
    order = orders[num - 1]
    print(order)
    if order['TaskUndoneQty'] == 0.0:
        exit('可预约数量不足,退出程序....')

    result = obj.getLading(order)[0]
    print(f'交易单号:{result["BillNo"]},送达方:{result["ShipToName"]},装运点:{result["QYShipPlaceName"]}')

    plans = obj.getPlanList(order, info=info)
    for i in plans:
        print(i)
    planId = eval(input('请输入时间段序号:')) - 1
    img = obj.getVerifyCode()
    code = OCR(img=img)
    print('识别验证码:code')
    order['TaskUndoneQty'] = info['质量']
    count = 0
    task = []
    while True:
        freeTime = obj.getPlanList(order, info=info)[planId]['IsBooking']
        print(f'倒计时{abs(freeTime)}秒')
        if freeTime >= -30:
            if freeTime >= 0:
                break
            time.sleep(abs(freeTime) - 0.1)
            break
        elif freeTime >= -120:  # 倒计时剩余120秒的时候,加快刷新速度
            time.sleep(10)
        else:  # 时间还有150秒之前,都是以30秒为刷新间隔
            time.sleep(60)

    while not obj.work and not obj.status:
        p = Pool.submit(obj.SaveRecord, code, order, plans[planId]['ID'], info)
        task.append(p)
        time.sleep(0.3)
    wait(task, return_when=ALL_COMPLETED)

if __name__ == '__main__':


    info=loadInfo()
    print(info)

    Pool=ThreadPoolExecutor(max_workers=10)

    logging.basicConfig(level=logging.INFO)
    obj = MMSH(info['user'], info['password'])
    ##test
    while True:
        img=obj.getVerifyCode()
        if not img:
            continue
        code = OCR(img=img)
        if not code:
            continue
        with open(f'{code}.jpg','wb') as f:
            f.write(img)
        break
    exit()
    #end
    if not obj.login():
        exit('登录失败')

    orders = obj.getOrders()
    for i in orders:
        print(i)

    num = eval(input('输入序号进行下一步:'))
    order=orders[num-1]
    print(order)
    if order['TaskUndoneQty']==0.0:
        exit('可预约数量不足,退出程序....')

    result = obj.getLading(order)[0]
    print(f'交易单号:{result["BillNo"]},送达方:{result["ShipToName"]},装运点:{result["QYShipPlaceName"]}')

    plans=obj.getPlanList(order,info=info)
    for i in plans:
        print(i)
    planId=eval(input('请输入时间段序号:'))-1
    img=obj.getVerifyCode()
    code=OCR(img=img)
    print('识别验证码:code')
    count=0
    task=[]
    while True:
        freeTime=obj.getPlanList(order,info=info)[planId]['IsBooking']
        print(f'倒计时{abs(freeTime)}秒')
        if freeTime>=-30:
            if freeTime>=0:
                break
            time.sleep(abs(freeTime)-0.1)
            break
        elif freeTime>=-120:#倒计时剩余120秒的时候,加快刷新速度
            time.sleep(10)
        else:#时间还有150秒之前,都是以30秒为刷新间隔
            time.sleep(60)

    while not obj.work and not obj.status:
        p=Pool.submit(obj.SaveRecord,code,order,plans[planId]['ID'],info)
        task.append(p)
        time.sleep(0.3)
    wait(task,return_when=ALL_COMPLETED)
    input()
