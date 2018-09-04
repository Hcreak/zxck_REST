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
admin_username = 'zxck'
admin_password = '***REMOVED***'

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
        execstr = "SELECT c.id,c.name,c.address,c.date,c.time FROM v_curclass c WHERE " + (
            ' or '.join('c.id=' + str(i) for i in cid))
        data = db.select(execstr)
        # print data
    else:
        data = db.select("SELECT c.id,c.name,c.address,c.date,c.time,c.pageurl FROM v_curclass c")

    itemlist = [{'id': i[0],
                 'name': i[1],
                 'address': i[2],
                 'date': i[3],
                 'time': i[4],
                 'pageurl': '' if len(i) == 5 else i[5]} for i in data]
    return itemlist

def selectclass_wx(cid='all'):
    if cid != 'all':
        # print cid
        execstr = "SELECT c.id,c.name,c.address,c.date,c.time FROM v_wxsaddc c WHERE " + (
            ' or '.join('c.id=' + str(i) for i in cid))
        data = db.select(execstr)
        # print data
    else:
        data = db.select("SELECT c.id,c.name,c.address,c.date,c.time,c.pageurl FROM v_wxsaddc c")

    itemlist = [{'id': i[0],
                 'name': i[1],
                 'address': i[2],
                 'date': i[3],
                 'time': i[4],
                 'pageurl': '' if len(i) == 5 else i[5]} for i in data]
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


@app.route('/webstudent', methods=['GET','POST'])
def webstudent():
    if checkkey() == True:
        if request.method=='GET':
            data = db.select("SELECT id,name,phonenumber,sex,age,adddate FROM t_student")
            itemlist = [{'id': i[0],
                         'name': i[1],
                         'phonenumber': i[2],
                         'sex': i[3],
                         'age': i[4],
                         'adddate': outstrtime(i[5])} for i in data]

            return render_template('webstudent.html', itemlist=itemlist)

        if request.method == 'POST':
            db.insert(
                "INSERT INTO t_student(name,phonenumber,sex,age,adddate) VALUE ('{}','{}','{}','{}','{}')".format(
                    request.form['name'], request.form['phonenumber'], request.form['sex'], request.form['age'],
                    time.time()))
            return redirect('/webstudent')
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


# @app.route('/webaddstudent', methods=['GET', 'POST'])
# def webaddstudent():
#     if checkkey() == True:
#         if request.method == 'GET':
#             return render_template('webaddstudent.html')
#         if request.method == 'POST':
#             db.insert(
#                 "INSERT INTO t_student(name,phonenumber,sex,age,adddate) VALUE ('{}','{}','{}','{}','{}')".format(
#                     request.form['name'], request.form['phonenumber'], request.form['sex'], request.form['age'],
#                     time.time()))
#             return redirect('/webstudent')
#     else:
#         return abort(404)


@app.route('/websaddc/<id>', methods=['GET', 'POST'])
def websaddc(id):
    if checkkey() == True:
        if request.method == 'GET':
            data = db.select("SELECT id,name,date FROM v_wxsaddc")
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


@app.route('/webteacher', methods=['GET', 'POST', 'DELETE'])
def webteacher():
    if checkkey() == True:
        if request.method == 'GET':
            data = db.select("SELECT id,name,adddate,openid FROM t_teacher")
            itemlist = [{'id': i[0],
                         'name': i[1],
                         'adddate': outstrtime(i[2]),
                         'openid': '' if len(i) == 3 else i[3]} for i in data]

            return render_template('webteacher.html', itemlist=itemlist)
        if request.method == 'POST':
            db.insert("INSERT INTO t_teacher(name,adddate,pwkey) VALUE ('{}','{}','{}')".format(request.form['name'],
                                                                                                time.time(),
                                                                                                request.form['pwkey']))
            return redirect('/webteacher')
        if request.method == 'DELETE':
            id = json.loads(request.form['id'])
            db.delete('DELETE FROM t_teacher WHERE id = {}'.format(id))
            return ''

    else:
        return abort(404)


@app.route('/webclass', methods=['GET','POST'])
def webclass():
    if checkkey() == True:
        if request.method=='GET':
            data = db.select(
                "SELECT c.id,c.name,c.address,c.date_start,c.time_start,c.adddate,count(x.id),c.money,c.date_end,c.time_end FROM t_class c LEFT JOIN t_xkb x ON x.cid=c.id GROUP BY c.id")

            itemlist = [{'id': i[0],
                         'name': i[1],
                         'address': i[2],
                         'date': str(i[3]) + ' - ' + str(i[8]),
                         'time': str(i[4]) + ' - ' + str(i[9]),
                         'adddate': outstrtime(i[5]),
                         'money': i[7],
                         'sum': i[6]} for i in data]

            return render_template('webclass.html', itemlist=itemlist)

        if request.method == 'POST':
            date_start = request.form['date'][:10]
            date_end = request.form['date'][13:]
            time_start = request.form['time'][:8]
            time_end = request.form['time'][11:]
            # print date_start, date_end, time_start, time_end
            db.insert(
                "INSERT INTO t_class(name,address,date_start,date_end,time_start,time_end,adddate,money) VALUE ('{}','{}','{}','{}','{}','{}','{}','{}')".format(
                    request.form['name'], request.form['address'], date_start, date_end, time_start, time_end,
                    time.time(), request.form['money']))
            return redirect('/webclass')

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

            data = db.select("SELECT pageurl,tid FROM t_class WHERE id = {}".format(id))
            classinfo = {'id': id, 'url': data[0][0], 'tid': data[0][1]}

            return render_template('webclassid.html', itemlist=itemlist, classinfo=classinfo)
        if request.method == 'POST':
            rdata = dict(request.form)

            # db.update("UPDATE t_class SET pageurl = '{}' WHERE id = {}".format(request.form['url'],  id))
            db.update("UPDATE t_class SET {} = '{}' WHERE  id = {}".format(rdata.keys()[0], rdata.values()[0][0], id))
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


# @app.route('/webaddclass', methods=['GET', 'POST'])
# def webaddclass():
#     if checkkey() == True:
#         if request.method == 'GET':
#             return render_template('webaddclass.html')
#         if request.method == 'POST':
#             date_start = request.form['date'][:10]
#             date_end = request.form['date'][13:]
#             time_start = request.form['time'][:8]
#             time_end = request.form['time'][11:]
#             # print date_start, date_end, time_start, time_end
#             db.insert(
#                 "INSERT INTO t_class(name,address,date_start,date_end,time_start,time_end,adddate,money) VALUE ('{}','{}','{}','{}','{}','{}','{}','{}')".format(
#                     request.form['name'], request.form['address'], date_start, date_end, time_start, time_end,
#                     time.time(), request.form['money']))
#             return redirect('/webclass')
#     else:
#         return abort(404)


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
        imgname = 'temp/' + imgurl[imgurl.rfind('tmp/') + 4:]
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
            return jsonify(selectclass_wx(cidlist))
        else:
            return 'error'
    else:
        return jsonify(selectclass_wx())


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

                addlist = selectclass_wx(lostlist)
            else:
                addlist = selectclass_wx()

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


@app.route('/wxtealogin', methods=['GET', 'POST'])
def wxtealogin():
    if request.method == 'GET':
        data = db.select("SELECT id,name FROM t_teacher WHERE openid = '{}'".format(getopenid(request.args['code'])))

        if len(data) == 0:
            return ''
        else:
            tid = data[0][0]
            name = data[0][1]
            data = db.select("SELECT id FROM t_class WHERE tid = {}".format(tid))
            if len(data) != 0:
                cidlist = [i[0] for i in data]
                clist = selectclass_wx(cidlist)
            else:
                clist = ''
            sres = {'tid': tid, 'name': name, 'clist': clist}
            return jsonify(sres)

    if request.method == 'POST':
        rdata = json.loads(request.data)
        data = db.select(
            "SELECT id FROM t_teacher WHERE name='{}' and pwkey='{}'".format(rdata['name'], rdata['pwkey']))
        if len(data) == 0:
            return 'error'
        else:
            tid = data[0][0]
            db.update("UPDATE t_teacher SET openid = '{}' WHERE id = {}".format(getopenid(rdata['code']), tid))
        return 'success'


@app.route('/wxteacomment', methods=['GET', 'POST'])
def wxteacomment():
    if request.method == 'GET':
        data = db.select("SELECT id,name FROM v_xklist WHERE cid = '{}'".format(request.args['cid']))
        return jsonify(data)
    if request.method == 'POST':
        curdate = time.strftime("%Y-%m-%d", time.localtime(time.time()))
        res = json.loads(request.data)
        cid = res['cid']
        commentlist = res['commentlist']
        for key, value in commentlist.items():
            # print key,value
            if value != '':
                db.insert(
                    "INSERT INTO t_comment(date,yes,comment,cid,sid) VALUE ('{}','1','{}','{}','{}')".format(curdate,
                                                                                                             value, cid,
                                                                                                             key))
            else:
                db.insert(
                    "INSERT INTO t_comment(date,yes,cid,sid) VALUE ('{}','0','{}','{}')".format(curdate, cid, key))

        return 'success'


@app.route('/wxstucomment', methods=['GET'])
def wxstucomment():
    data = db.select("SELECT date,yes,comment FROM t_comment WHERE cid='{}' AND sid='{}'".format(request.args['cid'],
                                                                                                 keygetsid('GET')))
    # print data
    return jsonify(data)


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


# 以下为抽奖部分

def getluckcur(openid):
    data = db.select("SELECT COUNT(*) FROM t_luckcount WHERE S='{}'".format(openid))
    num = int(data[0][0])
    data = db.select("SELECT COUNT(*) FROM t_luckthing WHERE openid='{}'".format(openid))
    num -= int(data[0][0])
    return num


@app.route('/wxgetluck', methods=['GET', 'POST'])
def wxgetluck():
    if request.method == 'GET':
        openid = getopenid(request.args['code'])
        data = db.select("SELECT COUNT(*) FROM t_luckphone  WHERE openid='{}'".format(openid))
        if int(data[0][0]) != 0:
            return jsonify({'num':getluckcur(openid),'openid':openid})
        else:
            return jsonify({'info': 'getphonenumber','openid':openid})
    if request.method == 'POST':
        res = json.loads(request.data)
        openid = getopenid(res['code'])
        db.insert("INSERT INTO t_luckphone(openid,phonenumber) VALUE('{}','{}')".format(openid, res['phonenumber']))
        db.insert("INSERT INTO t_luckcount(S,J) VALUE('{}','{}')".format(openid, openid))
        return 'success'


@app.route('/wxsetluck', methods=['GET', 'POST'])
def wxsetluck():
    if request.method == 'GET':
        openid = getopenid(request.args['code'])
        lastid = request.args['lastid']
        data = db.select("SELECT COUNT(*) FROM t_luckcount WHERE S='{}' AND J='{}'".format(lastid, openid))
        if int(data[0][0]) == 0:
            db.insert("INSERT INTO t_luckcount(S,J) VALUE('{}','{}')".format(lastid, openid))
        return 'success'
    if request.method == 'POST':
        res = json.loads(request.data)
        openid = getopenid(res['code'])
        db.insert("INSERT INTO t_luckthing(openid,thing,uselog) VALUE('{}','{}',0)".format(openid, res['thing']))
        return jsonify({'num':getluckcur(openid)})

@app.route('/wxgetluckthing', methods=['GET'])
def wxgetluckthing():
    openid = getopenid(request.args['code'])
    data=db.select("SELECT thing FROM t_luckthing WHERE openid='{}' AND uselog=0 AND thing != 'None'".format(openid))
    thinglist=[i[0] for i in data]
    return jsonify(thinglist)

@app.route('/wxgetlucklevel', methods=['GET'])
def wxgetlucklevel():
    data = db.select("SELECT text FROM t_lucklevel ORDER BY level")
    lucklist = [i[0] for i in data]
    return jsonify(lucklist)

@app.route('/webluck', methods=['GET','POST','DELETE'])
def webluck():
    if checkkey() == True:
        if request.method=='GET':
            data=db.select("SELECT id,phonenumber,thing,uselog FROM t_luckthing t JOIN t_luckphone p ON t.openid=p.openid")
            thinglist=[list(i) for i in data]
            # print thinglist
            data=db.select("SELECT text FROM t_lucklevel ORDER BY level")
            lucklist=[i[0] for i in data]
            return render_template('webluck.html',itemlist=thinglist,luck=lucklist)
        if request.method=='POST':
            rdata = dict(request.form)
            for i in range(len(rdata)):
                db.update("UPDATE t_lucklevel SET text='{1}' WHERE level={0}".format(rdata.keys()[i],rdata.values()[i][0]))
                # print rdata.keys()[i]
                # print rdata.values()[i]
            return redirect('/webluck')
        if request.method=='DELETE':
            db.update("UPDATE t_luckthing SET uselog=1 WHERE id={}".format(request.form['id']))
            return ''
    else:
        return abort(404)


if __name__ == '__main__':
    app.run()
