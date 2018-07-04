# coding=utf-8
from flask import *
import pymysql
import redis
import os
import hashlib
import time
import sys
import requests
import uuid
import random
from werkzeug.utils import secure_filename

from config import *
from wxpay import WxPay, get_nonce_str, dict_to_xml, xml_to_dict

reload(sys)
sys.setdefaultencoding('utf8')
os.chdir(os.path.split(os.path.realpath(__file__))[0])

app = Flask(__name__)
app.debug = True

# keys config
###############
app.secret_key = os.urandom(16)
randomkey = os.urandom(48)

# admin config
###############
# admin_username = 'admin'
# admin_password = 'zhixuechuangke++'
admin_username = '1'
admin_password = '1'

# mysql config
###############
# db = pymysql.connect("localhost", "zxck", "zhixuechuangke++", "zxck")
db = pymysql.connect("116.255.247.68", "zxck", "1", "zxck")
cursor = db.cursor()

# redis config
###############
pool = redis.ConnectionPool(host='localhost', port=6379, decode_responses=True)
r = redis.Redis(connection_pool=pool)


def checkkey():
    key = session.get('key')
    if key == None:
        return False
    if key == randomkey:
        return True
    else:
        return False


def outstrtime(in_time):
    return time.strftime("%B %d, %Y at %H:%M", time.localtime(float(in_time)))


def getopenid(code):
    url = 'https://api.weixin.qq.com/sns/jscode2session?appid={}&secret={}&js_code={}&grant_type=authorization_code'.format(
        appid, secret, code)
    req = requests.post(url)
    openid = json.loads(req.text)['openid']
    # print openid
    return openid


def wxid_add(sid, openid, gx):
    cursor.execute(
        "INSERT INTO t_wxid(sid,openid,gx,adddate) VALUE ('{}','{}','{}','{}')".format(sid, openid, gx, time.time()))
    db.commit()


def selectclass(cid='all'):
    if cid != 'all':
        # print cid
        execstr = "SELECT c.id,c.name,c.address,c.date,c.time FROM t_class c WHERE " + (
            ' or '.join('c.id=' + str(i) for i in cid))
        cursor.execute(execstr)
    else:
        cursor.execute("SELECT c.id,c.name,c.address,c.date,c.time FROM t_class c")

    itemlist = [{'id': i[0],
                 'name': i[1],
                 'address': i[2],
                 'date': i[3],
                 'time': i[4]} for i in cursor.fetchall()]
    return itemlist


def keygetsid(method):
    if method == 'GET':
        if not request.args.has_key('key'):
            return False
        key = request.args['key']
    if method == 'POST':
        if request.data == None:
            return False
        key = json.loads(request.data)['key']
    sid = r.get(key)
    if sid == None:
        return False
    return sid


def getstudentphoto(sid):
    cursor.execute("SELECT photo FROM t_student WHERE id = {}".format(sid))
    photo = cursor.fetchone()[0]
    if photo == None:
        return 'error'
    else:
        imgname = 'temp/{}.jpg'.format(str(random.randint(1000, 2000)))
        f = open(imgname, 'wb')
        f.write(photo)
        f.close()
        return imgname


@app.route('/', methods=['GET', 'POST'])
def webindex():
    if request.method == 'GET':
        if checkkey() == True:
            return render_template('index.html')
        else:
            return render_template('login.html')
    if request.method == 'POST':
        if request.form['username'] == hashlib.md5(admin_username).hexdigest() \
                and request.form['password'] == hashlib.md5(admin_password).hexdigest():
            session['key'] = randomkey
            return redirect('/')
        else:
            return abort(404)


@app.route('/webstudent', methods=['GET'])
def webstudent():
    if checkkey() == True:
        cursor.execute("SELECT * FROM t_student")
        itemlist = [{'id': i[0],
                     'name': i[1],
                     'phonenumber': i[2],
                     'sex': i[3],
                     'age': i[4],
                     'adddate': outstrtime(i[5])} for i in
                    cursor.fetchall()]

        return render_template('webstudent.html', itemlist=itemlist)
    else:
        return abort(404)


@app.route('/webstudent/<id>', methods=['GET'])
def webstudentid(id):
    if checkkey() == True:
        cursor.execute("SELECT * FROM t_student WHERE id = {}".format(id))
        i = cursor.fetchone()
        item = {'id': i[0],
                'name': i[1],
                'phonenumber': i[2],
                'sex': i[3],
                'age': i[4],
                'adddate': outstrtime(i[5]),
                'photo': getstudentphoto(id)}

        cursor.execute("SELECT id,openid,gx,adddate FROM t_wxid where sid = {}".format(id))
        item['wx'] = [{'id': w[0],
                       'openid': w[1],
                       'gx': w[2],
                       'adddate': outstrtime(w[3])} for w in
                      cursor.fetchall()]

        cursor.execute(
            "SELECT x.id,x.cid,c.name,x.adddate FROM t_xkb x JOIN t_class c ON x.cid=c.id WHERE x.sid = {}".format(id))
        item['xk'] = [{'id': x[0],
                       'cid': x[1],
                       'name': x[2],
                       'adddate': outstrtime(x[3])} for x in
                      cursor.fetchall()]

        return render_template('webstudentid.html', item=item)
    else:
        return abort(404)


@app.route('/webdeletestudent/<id>', methods=['GET'])
def webdeletestudent(id):
    if checkkey() == True:
        cursor.execute("DELETE FROM t_student WHERE id = {}".format(id))
        db.commit()
        return redirect('/webstudent')
    else:
        return abort(404)


@app.route('/webaddstudent', methods=['GET', 'POST'])
def webaddstudent():
    if checkkey() == True:
        if request.method == 'GET':
            return render_template('webaddstudent.html')
        if request.method == 'POST':
            cursor.execute(
                "INSERT INTO t_student(name,phonenumber,sex,age,adddate) VALUE ('{}','{}','{}','{}','{}')".format(
                    request.form['name'], request.form['phonenumber'], request.form['sex'], request.form['age'],
                    time.time()))
            db.commit()
            return redirect('/webstudent')
    else:
        return abort(404)


@app.route('/websaddc/<id>', methods=['GET', 'POST'])
def websaddc(id):
    if checkkey() == True:
        if request.method == 'GET':
            cursor.execute("SELECT id,name,date FROM t_class")
            itemlist = [{'id': i[0],
                         'name': i[1],
                         'date': i[2]} for i in cursor.fetchall()]

            return render_template('websaddc.html', id=id, itemlist=itemlist)
        if request.method == 'POST':
            cursor.execute("INSERT INTO t_xkb(sid,cid,adddate) VALUE ({},{},{})".format(id, request.form['classRadios'],
                                                                                        time.time()))
            db.commit()
            return redirect('/webstudent/{}'.format(id))
    else:
        return abort(404)


@app.route('/webclass', methods=['GET'])
def webclass():
    if checkkey() == True:
        cursor.execute(
            "SELECT c.id,c.name,c.address,c.date,c.time,c.adddate,count(x.id) FROM t_class c LEFT JOIN t_xkb x ON x.cid=c.id GROUP BY c.id")
        itemlist = [{'id': i[0],
                     'name': i[1],
                     'address': i[2],
                     'date': i[3],
                     'time': i[4],
                     'adddate': outstrtime(i[5]),
                     'sum': i[6]} for i in cursor.fetchall()]

        return render_template('webclass.html', itemlist=itemlist)
    else:
        return abort(404)


@app.route('/webclass/<id>', methods=['GET'])
def webclassid(id):
    if checkkey() == True:
        cursor.execute(
            "SELECT x.id,s.name,s.phonenumber,s.sex,s.age,x.adddate FROM t_xkb x JOIN t_student s ON x.sid=s.id WHERE x.cid = {}".format(
                id))
        itemlist = [{'id': i[0],
                     'name': i[1],
                     'phonenumber': i[2],
                     'sex': i[3],
                     'age': i[4],
                     'adddate': outstrtime(i[5])} for i in cursor.fetchall()]

        return render_template('webclassid.html', itemlist=itemlist)
    else:
        return abort(404)


@app.route('/webcdels/<xid>', methods=['DELETE'])
def webcdels(xid):
    if checkkey() == True:
        cursor.execute('DELETE FROM t_xkb WHERE id = {}'.format(xid))
        db.commit()
        return ''
    else:
        return abort(404)


@app.route('/webaddclass', methods=['GET', 'POST'])
def webaddclass():
    if checkkey() == True:
        if request.method == 'GET':
            return render_template('webaddclass.html')
        if request.method == 'POST':
            cursor.execute(
                "INSERT INTO t_class(name,address,date,time,adddate) VALUE ('{}','{}','{}','{}','{}')".format(
                    request.form['name'], request.form['address'], request.form['date'], request.form['time'],
                    time.time()))
            db.commit()
            return redirect('/webclass')
    else:
        return abort(404)


@app.route('/webdeleteclass/<id>', methods=['GET'])
def webdeleteclass(id):
    if checkkey() == True:
        cursor.execute("DELETE FROM t_class WHERE id = {}".format(id))
        db.commit()
        return redirect('/webclass')
    else:
        return abort(404)


@app.route('/webdatashow', methods=['GET'])
def webdatashow():
    return render_template('webdatashow.html', itemlist=selectclass())


@app.route('/wxlogin', methods=['GET'])
def wxlogin():
    cursor.execute(
        "SELECT w.sid,w.gx,s.name,s.phonenumber FROM t_wxid w JOIN t_student s ON w.sid=s.id WHERE w.openid = '{}'".format(
            getopenid(request.args['code'])))
    if cursor.rowcount == 0:
        return ''
    else:
        data = cursor.fetchone()
        key = uuid.uuid1()
        # print key
        r.set(key, data[0], ex=600)
        sres = {'key': key, 'name': data[2], 'gx': data[1], 'phonenumber': data[3]}
        return jsonify(sres)


@app.route('/wxlogup', methods=['POST'])
def wxlogup():
    rdata = json.loads(request.data)
    cursor.execute(
        "INSERT INTO t_student(name,phonenumber,age,sex,adddate) VALUE ('{}','{}','{}','{}','{}')".format(rdata['name'],
                                                                                                          rdata[
                                                                                                              'phonenumber'],
                                                                                                          rdata['age'],
                                                                                                          rdata['sex'],
                                                                                                          time.time()))
    db.commit()
    cursor.execute("SELECT max(id) FROM t_student WHERE name = '{}'".format(rdata['name']))
    sid = cursor.fetchone()[0]

    if rdata['image'] != '':
        imgurl = rdata['image']
        imgname = 'temp/' + imgurl[imgurl.rfind('tmp_',1):]
        f = open(imgname, 'rb')
        img = f.read()
        f.close()
        os.remove(imgname)
        cursor.execute("UPDATE t_student SET photo = '{}' WHERE id = {}".format(pymysql.escape_string(img), sid))
        db.commit()

    wxid_add(sid, getopenid(rdata['code']), rdata['gx'])

    return ''


@app.route('/wxidadd', methods=['POST'])
def wxidadd():
    rdata = json.loads(request.data)
    cursor.execute(
        "SELECT id FROM t_student WHERE name='{}' and phonenumber='{}'".format(rdata['name'], rdata['phonenumber']))
    if cursor.rowcount == 0:
        return 'error'
    else:
        sid = cursor.fetchone()
        wxid_add(sid[0], getopenid(rdata['code']), rdata['gx'])
    return 'success'


@app.route('/wxclass', methods=['GET'])
def wxclass():
    if request.args:
        sid = keygetsid('GET')
        if sid:
            cursor.execute("SELECT cid FROM t_xkb WHERE sid = '{}'".format(sid))
            if cursor.rowcount == 0:
                return 'none'
            cidlist = [i[0] for i in cursor.fetchall()]
            return jsonify(selectclass(cidlist))
        else:
            return 'error'
    else:
        return jsonify(selectclass())


@app.route('/wxsaddc', methods=['GET', 'POST'])
def wxsaddc():
    if request.method == 'GET':
        sid = keygetsid('GET')
        if sid:
            cursor.execute("SELECT cid FROM t_xkb WHERE sid = '{}'".format(sid))
            if cursor.rowcount != 0:
                cidlist = [i[0] for i in cursor.fetchall()]
                cursor.execute("SELECT id FROM t_class")
                alist = [i[0] for i in cursor.fetchall()]

                lostlist = list(set(alist).difference(set(cidlist)))  # alist V blist X --> send add
                if len(lostlist) == 0:
                    return 'none'

                addlist = selectclass(lostlist)
            else:
                addlist = selectclass()

            return jsonify(addlist)
        else:
            return 'error'
    if request.method == 'POST':
        sid = keygetsid('POST')
        if sid:
            for i in range(0, 3):
                if r.exists(sid):
                    cid = r.get(sid)
                    r.delete(sid)
                    cursor.execute(
                        "INSERT INTO t_xkb(sid,cid,adddate) VALUE ('{}','{}','{}')".format(sid, cid, time.time()))
                    db.commit()
                    return 'success'

                time.sleep(1)
            return 'error'
        else:
            return 'error'


@app.route('/wxpay/pay', methods=['POST'])
def create_pay():
    '''
    请求支付
    :return:
    '''
    sid = keygetsid('POST')
    if sid:
        cid=json.loads(request.data)['cid']
        cursor.execute("SELECT name,money FROM t_class WHERE id = {}".format(cid))
        n, m = cursor.fetchone()
        m=str(int(m)*100)

        data = {
            'appid': appid,
            'mch_id': mch_id,
            'nonce_str': get_nonce_str(),
            'body': n,  # 商品描述
            'out_trade_no': str(int(time.time())),  # 商户订单号
            'total_fee': m,
            'spbill_create_ip': spbill_create_ip,
            'notify_url': notify_url,
            'trade_type': trade_type,
            'attach': cid,
            'openid': getopenid(json.loads(request.data)['code'])
        }

        wxpay = WxPay(merchant_key, **data)
        pay_info = wxpay.get_pay_info()
        if pay_info:
            return jsonify(pay_info)
        return 'error'

    else:
        return 'error'


@app.route('/wxpay/notify', methods=['POST'])
def wxpay():
    '''
    支付回调通知
    :return:
    '''
    if request.method == 'POST':
        data = xml_to_dict(request.data)
        f = open('wxpay.log', 'a+')
        f.write(json.dumps(data))
        f.close()

        cursor.execute("SELECT sid FROM t_wxid WHERE openid = '{}'".format(data['openid']))
        sid = cursor.fetchone()[0]
        r.set(sid, data['attach'])

        # logging.info(xml_to_dict(request.data))
        result_data = {
            'return_code': 'SUCCESS',
            'return_msg': 'OK'
        }
        return dict_to_xml(result_data), {'Content-Type': 'application/xml'}


@app.route('/wxphoto', methods=['GET', 'POST'])
def wxphoto():
    if request.method == 'GET':
        sid = keygetsid('GET')
        if sid:
            return getstudentphoto(sid)
        else:
            return 'error'
    if request.method == 'POST':
        f = request.files['image']
        filename = secure_filename(f.filename)
        f.save('temp/' + str(filename))
        return ''


@app.route('/temp/<file>', methods=['GET'])
def gettemp(file):
    path = "temp/{}".format(file)
    if os.path.exists(path):
        image = open(path, 'rb')
        resp = Response(image, mimetype="image/jpeg")
        os.remove(path)
        return resp
    else:
        return ''


if __name__ == '__main__':
    app.run()
