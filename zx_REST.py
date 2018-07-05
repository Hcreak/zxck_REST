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
from olimysql import olimysql

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
# db = pymysql.connect("116.255.247.68", "zxck", "1", "zxck")
# db = olimysql("116.255.247.68", "zxck", "1", "zxck")
db = olimysql("127.0.0.1", "zxck", "zhixuechuangke++", "zxck")

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
    db.insert(
        "INSERT INTO t_wxid(sid,openid,gx,adddate) VALUE ('{}','{}','{}','{}')".format(sid, openid, gx, time.time()))


def selectclass(cid='all'):
    if cid != 'all':
        # print cid
        execstr = "SELECT c.id,c.name,c.address,c.date,c.time FROM t_class c WHERE " + (
            ' or '.join('c.id=' + str(i) for i in cid))
        data = db.select(execstr)
        print data
    else:
        data = db.select("SELECT c.id,c.name,c.address,c.date,c.time,c.pageurl FROM t_class c")

    itemlist = [{'id': i[0],
                 'name': i[1],
                 'address': i[2],
                 'date': i[3],
                 'time': i[4],
                 'pageurl': '' if len(i)==5 else i[5]} for i in data]
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
    data = db.select("SELECT photo FROM t_student WHERE id = {}".format(sid))
    photo = data[0][0]
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
        data = db.select("SELECT id,name,phonenumber,sex,age,adddate FROM t_student")
        itemlist = [{'id': i[0],
                     'name': i[1],
                     'phonenumber': i[2],
                     'sex': i[3],
                     'age': i[4],
                     'adddate': outstrtime(i[5])} for i in data]

        return render_template('webstudent.html', itemlist=itemlist)
    else:
        return abort(404)


@app.route('/webstudent/<id>', methods=['GET'])
def webstudentid(id):
    if checkkey() == True:
        data = db.select("SELECT id,name,phonenumber,sex,age,adddate FROM t_student WHERE id = {}".format(id))
        i = data[0]
        item = {'id': i[0],
                'name': i[1],
                'phonenumber': i[2],
                'sex': i[3],
                'age': i[4],
                'adddate': outstrtime(i[5]),
                'photo': getstudentphoto(id)}

        data = db.select("SELECT id,openid,gx,adddate FROM t_wxid where sid = {}".format(id))
        item['wx'] = [{'id': w[0],
                       'openid': w[1],
                       'gx': w[2],
                       'adddate': outstrtime(w[3])} for w in data]

        data = db.select(
            "SELECT x.id,x.cid,c.name,x.adddate FROM t_xkb x JOIN t_class c ON x.cid=c.id WHERE x.sid = {}".format(id))
        item['xk'] = [{'id': x[0],
                       'cid': x[1],
                       'name': x[2],
                       'adddate': outstrtime(x[3])} for x in data]

        return render_template('webstudentid.html', item=item)
    else:
        return abort(404)


@app.route('/webdeletestudent/<id>', methods=['GET'])
def webdeletestudent(id):
    if checkkey() == True:
        db.delete("DELETE FROM t_student WHERE id = {}".format(id))
        return redirect('/webstudent')
    else:
        return abort(404)


@app.route('/webaddstudent', methods=['GET', 'POST'])
def webaddstudent():
    if checkkey() == True:
        if request.method == 'GET':
            return render_template('webaddstudent.html')
        if request.method == 'POST':
            db.insert(
                "INSERT INTO t_student(name,phonenumber,sex,age,adddate) VALUE ('{}','{}','{}','{}','{}')".format(
                    request.form['name'], request.form['phonenumber'], request.form['sex'], request.form['age'],
                    time.time()))
            return redirect('/webstudent')
    else:
        return abort(404)


@app.route('/websaddc/<id>', methods=['GET', 'POST'])
def websaddc(id):
    if checkkey() == True:
        if request.method == 'GET':
            data = db.select("SELECT id,name,date FROM t_class")
            itemlist = [{'id': i[0],
                         'name': i[1],
                         'date': i[2]} for i in data]

            return render_template('websaddc.html', id=id, itemlist=itemlist)
        if request.method == 'POST':
            db.insert("INSERT INTO t_xkb(sid,cid,adddate) VALUE ({},{},{})".format(id, request.form['classRadios'],
                                                                                   time.time()))
            return redirect('/webstudent/{}'.format(id))
    else:
        return abort(404)


@app.route('/webclass', methods=['GET'])
def webclass():
    if checkkey() == True:
        data = db.select(
            "SELECT c.id,c.name,c.address,c.date,c.time,c.adddate,count(x.id),c.money FROM t_class c LEFT JOIN t_xkb x ON x.cid=c.id GROUP BY c.id")
        itemlist = [{'id': i[0],
                     'name': i[1],
                     'address': i[2],
                     'date': i[3],
                     'time': i[4],
                     'adddate': outstrtime(i[5]),
                     'money': i[7],
                     'sum': i[6]} for i in data]

        return render_template('webclass.html', itemlist=itemlist)
    else:
        return abort(404)


@app.route('/webclass/<id>', methods=['GET', 'POST'])
def webclassid(id):
    if checkkey() == True:
        if request.method == 'GET':
            data = db.select(
                "SELECT x.id,s.name,s.phonenumber,s.sex,s.age,x.adddate FROM t_xkb x JOIN t_student s ON x.sid=s.id WHERE x.cid = {}".format(
                    id))
            itemlist = [{'id': i[0],
                         'name': i[1],
                         'phonenumber': i[2],
                         'sex': i[3],
                         'age': i[4],
                         'adddate': outstrtime(i[5])} for i in data]

            data = db.select("SELECT pageurl FROM t_class WHERE id = {}".format(id))
            urldict = {'id': id, 'url': data[0][0]}

            return render_template('webclassid.html', itemlist=itemlist, urldict=urldict)
        if request.method == 'POST':
            db.update("UPDATE t_class SET pageurl = '{}' WHERE id = {}".format(request.form['url'], id))
            return redirect('/webclass/' + id)

    else:
        return abort(404)


@app.route('/webcdels/<xid>', methods=['DELETE'])
def webcdels(xid):
    if checkkey() == True:
        db.delete('DELETE FROM t_xkb WHERE id = {}'.format(xid))
        return ''
    else:
        return abort(404)


@app.route('/webaddclass', methods=['GET', 'POST'])
def webaddclass():
    if checkkey() == True:
        if request.method == 'GET':
            return render_template('webaddclass.html')
        if request.method == 'POST':
            db.insert(
                "INSERT INTO t_class(name,address,date,time,adddate,money) VALUE ('{}','{}','{}','{}','{}','{}')".format(
                    request.form['name'], request.form['address'], request.form['date'], request.form['time'],
                    time.time(), request.form['money']))
            return redirect('/webclass')
    else:
        return abort(404)


@app.route('/webdeleteclass/<id>', methods=['GET'])
def webdeleteclass(id):
    if checkkey() == True:
        db.delete("DELETE FROM t_class WHERE id = {}".format(id))
        return redirect('/webclass')
    else:
        return abort(404)


@app.route('/webdatashow', methods=['GET'])
def webdatashow():
    return render_template('webdatashow.html', itemlist=selectclass())


@app.route('/webinfopage', methods=['GET', 'POST'])
def webinfopage():
    if checkkey() == True:
        if request.method == 'GET':
            data = db.select("SELECT page,url FROM t_infopage")
            pageurl = {}
            for i in data:
                pageurl[i[0]] = i[1]

            return render_template('webinfopage.html', pageurl=pageurl)

        if request.method == 'POST':
            rdata = dict(request.form)
            # print rdata.keys()[0]
            # print rdata.values()[0][0]

            db.update(
                "UPDATE t_infopage SET url = '{1}' WHERE page = '{0}'".format(rdata.keys()[0], rdata.values()[0][0]))
            return redirect('/webinfopage')
    else:
        return abort(404)


@app.route('/wxinfopage', methods=['GET'])
def wxinfopage():
    data = db.select("SELECT page,url FROM t_infopage")
    pageurl = {}
    for i in data:
        pageurl[i[0]] = i[1]

    return jsonify(pageurl)


@app.route('/wxlogin', methods=['GET'])
def wxlogin():
    data = db.select(
        "SELECT w.sid,w.gx,s.name,s.phonenumber FROM t_wxid w JOIN t_student s ON w.sid=s.id WHERE w.openid = '{}'".format(
            getopenid(request.args['code'])))
    if len(data) == 0:
        return ''
    else:
        data = data[0]
        key = uuid.uuid1()
        # print key
        r.set(key, data[0], ex=600)
        sres = {'key': key, 'name': data[2], 'gx': data[1], 'phonenumber': data[3]}
        return jsonify(sres)


@app.route('/wxlogup', methods=['POST'])
def wxlogup():
    rdata = json.loads(request.data)
    db.insert(
        "INSERT INTO t_student(name,phonenumber,age,sex,adddate) VALUE ('{}','{}','{}','{}','{}')".format(rdata['name'],
                                                                                                          rdata[
                                                                                                              'phonenumber'],
                                                                                                          rdata['age'],
                                                                                                          rdata['sex'],
                                                                                                          time.time()))
    data = db.select("SELECT max(id) FROM t_student WHERE name = '{}'".format(rdata['name']))
    sid = data[0][0]

    if rdata['image'] != '':
        imgurl = rdata['image']
        imgname = 'temp/' + imgurl[imgurl.rfind('tmp_', 1):]
        f = open(imgname, 'rb')
        img = f.read()
        f.close()
        os.remove(imgname)
        db.update("UPDATE t_student SET photo = '{}' WHERE id = {}".format(pymysql.escape_string(img), sid))

    wxid_add(sid, getopenid(rdata['code']), rdata['gx'])

    return ''


@app.route('/wxidadd', methods=['POST'])
def wxidadd():
    rdata = json.loads(request.data)
    data = db.select(
        "SELECT id FROM t_student WHERE name='{}' and phonenumber='{}'".format(rdata['name'], rdata['phonenumber']))
    if len(data) == 0:
        return 'error'
    else:
        sid = data[0][0]
        wxid_add(sid, getopenid(rdata['code']), rdata['gx'])
    return 'success'


@app.route('/wxclass', methods=['GET'])
def wxclass():
    if request.args:
        sid = keygetsid('GET')
        if sid:
            data = db.select("SELECT cid FROM t_xkb WHERE sid = '{}'".format(sid))
            if len(data) == 0:
                return 'none'
            cidlist = [i[0] for i in data]
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
            data = db.select("SELECT cid FROM t_xkb WHERE sid = '{}'".format(sid))
            if len(data) != 0:
                cidlist = [i[0] for i in data]
                data = db.select("SELECT id FROM t_class")
                alist = [i[0] for i in data]

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
                    db.insert(
                        "INSERT INTO t_xkb(sid,cid,adddate) VALUE ('{}','{}','{}')".format(sid, cid, time.time()))
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
        cid = json.loads(request.data)['cid']
        data = db.select("SELECT name,money FROM t_class WHERE id = {}".format(cid))
        n, m = data[0]
        m = str(int(m) * 100)

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
        rdata = xml_to_dict(request.data)
        f = open('wxpay.log', 'a+')
        f.write(json.dumps(rdata))
        f.close()

        data = db.select("SELECT sid FROM t_wxid WHERE openid = '{}'".format(rdata['openid']))
        sid = data[0][0]
        r.set(sid, rdata['attach'])

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
