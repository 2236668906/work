from flask import Flask,request,jsonify,render_template
from concurrent.futures import ThreadPoolExecutor,wait,ALL_COMPLETED
from multiprocessing import Process
from common.isBooking import API_Task
import redis


app = Flask(__name__)

r=redis.Redis(host='127.0.0.1',port=6379,db=0,decode_responses=True)
def a():
    print('threading')


@app.route('/adduser',methods=['POST'])
def add_user():
    name=request.form.get("name",None)
    phone = request.form.get("phone", None)
    card = request.form.get("card", None)
    idnum = request.form.get("idnum", None)
    if all([name,phone,card,idnum]):
        if r.hmset(name,{'phone':phone,'card':card,'idnum':idnum}):
            r.sadd('users',name)
            result={'code':0,'info':'添加成功'}
        else:
            result = {'code': -2, 'info': '添加失败'}
    else:
        result={'code':-1,'info':'参数错误'}

    return jsonify(result)

@app.route('/deluser',methods=['POST'])
def del_user():
    name = request.form.get("name", None)
    if not name:
        result={'code':-1,'info':'参数错误'}
    if r.delete(name):
        result={'code':0,'info':'删除成功'}
    else:
        result={'code':-2,'info':'删除失败'}

    return jsonify(result)

@app.route('/getuser')
def get_user():
    name=request.args.get('name',None)
    if not name:
        result={'code':-1,'info':'参数错误'}
    else:
        data=r.hvals(name=name)
        if data:
            _ = {'name': name, 'phone': data[0], 'card': data[1], 'idnum': data[2]}
            result = {'code': 0, 'info': 'success','data':_}
        else:
            result={'code':-2,'info':'用户不存在'}
    return jsonify(result)

def test():
    Pool=ThreadPoolExecutor(max_workers=10)
    tasks=[]
    for i in range(10):
        tasks.append(Pool.submit(a))
    print('process')
    wait(tasks,return_when=ALL_COMPLETED)
    print('end')

@app.route('/booking',methods=['POST'])
def add_task():
    info={}
    user=request.form.get('user',None)
    password=request.form.get('password',None)
    name=request.form.get('name',None)
    u=r.hmget(name)
    if u:
        phone,_,idnum=u
    else:
        return jsonify({'code':-100,'info':'司机资料不存在'})
    card=request.form.get('card',None)
    weight=request.form.get('weight',None)
    date=request.form.get('date',None)
    if all([user,password,name,phone,card,weight,date]):
        info.update({'user':user,'password':password,'name':name,'phone':phone,'card':card,'weight':weight,'date':date,'idnum':idnum})
    pass


@app.route('/')
def hello_world():
    # Process(target=test).start()
    result = []
    a = r.smembers('users')
    for key in a:
        data = r.hvals(name=key)
        if data:
            _ = {'name': key, 'phone': data[0], 'card': data[1], 'idnum': data[2]}
            result.append(_)
        else:
            r.srem('users', key)
    print(result)
    return render_template('index.html',users=result)

if __name__ == '__main__':
    app.run(port=5001)
