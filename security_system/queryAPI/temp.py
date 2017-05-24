# encoding:utf-8
import datetime

import MySQLdb

conn = MySQLdb.connect(
    host='localhost',
    port=3306,
    user='root',
    passwd='123456',
    db='ics'
)
cur = conn.cursor()

result = []
k = 0


def changedate():
    global cur
    global k
    s = 'SELECT date FROM icscert'  # 选择数据�?
    try:
        cur.execute(s)
        result = cur.fetchall()
        for row in result:
            date = row[0][23:41]
            # September 19, 2016
            print(date + " $")
            l = len(date)
            for i in range(l):
                if (date[i] == '|'):
                    ndate = date[:i - 1]
            #####找出所需要的日期######
            print(ndate)
            newdate = datetime.datetime.strptime(ndate, '%B %d, %Y')  # 当前日期格式
            ###这个函数用的格式化方法中%的代表搜索这个函数名字就能找�?
            newdate = newdate.strftime('%Y%m%d')  # 目标日期格式
            print(newdate)
            com = 'update icscert set date={0} where id={1}'.format(newdate, str(k))
            print(com)
            cur.execute(com)
            k += 1
        print(k)

    except Exception as e:
        print(e)


changedate()
conn.commit()
