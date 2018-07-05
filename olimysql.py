import pymysql


class olimysql:
    def __init__(self, host, user, passwd, db):
        self.host = host
        self.user = user
        self.passwd = passwd
        self.db = db

    def select(self, sql):
        db = pymysql.connect(self.host, self.user, self.passwd, self.db)
        cursor = db.cursor()

        data = []
        try:
            cursor.execute(sql)
            data = cursor.fetchall()
        except:
            print("MySQL Error: unable to fecth data of station_stock")

        cursor.close()
        db.close()
        return data

    def insert(self, sql):
        db = pymysql.connect(self.host, self.user, self.passwd, self.db)
        cursor = db.cursor()

        try:
            cursor.execute(sql)
        except:
            print("MySQL Error :unable to insert data")

        db.commit()
        cursor.close()
        db.close()

    def update(self, sql):
        db = pymysql.connect(self.host, self.user, self.passwd, self.db)
        cursor = db.cursor()

        try:
            cursor.execute(sql)
        except:
            print("MySQL Error :unable to update data")

        db.commit()
        cursor.close()
        db.close()

    def delete(self, sql):
        db = pymysql.connect(self.host, self.user, self.passwd, self.db)
        cursor = db.cursor()

        try:
            cursor.execute(sql)
        except:
            print("MySQL Error :unable to delete data")

        db.commit()
        cursor.close()
        db.close()
