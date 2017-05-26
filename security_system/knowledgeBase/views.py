# -*- coding:utf-8 -*-
import json

from django.db import connection
from django.http import HttpResponse

from knowledgeBase.models import vulnerability, VulnerabilityDevice, vendor, instance, dev2vul


# reload(sys)
# sys.setdefaultencoding("utf-8")


def groupCount(request, type):
    list = []
    if type == "vulYear":
        list = vulnerability.objects.values_list('date')
    elif type == "devType":
        list = VulnerabilityDevice.objects.values_list('vendor')
    elif type == "venCountry":
        list = vendor.objects.values_list('country')
    elif type == "insCountry":
        list = instance.objects.values_list('country')
    elif type == "insProtocol":
        list = instance.objects.values_list('ins_type')
    elif type == "venDevice":
        list = VulnerabilityDevice.objects.values_list('vendor')

    temp = []
    for item in list:
        temp.append(item[0])

    if type == "vulYear":
        for i in range(len(temp)):
            temp[i] = temp[i][0:4]

    dic = {}
    for item in temp:
        if item == "":
            continue
        if item in dic:
            dic[item] += 1
        else:
            dic[item] = 1

    return HttpResponse(json.dumps(dic))


def getInstance(request):
    """
    设备探针菜单的地图显示设备使用此API
    :param request: 
    :return: 
    """
    cursor = connection.cursor()
    sql = 'SELECT a.ip, a.city, a.country, a.timestamp, a.lat, a.lon, b.port, b.protocol ' \
          'FROM knowledgeBase_instance a ' \
          'left join knowledgeBase_instanceport b on a.name = b.instance_id'
    cursor.execute(sql)
    rowset = cursor.fetchall()

    devices = []
    for row in rowset:
        dev = dict()
        dev['ip'] = row[0]
        if row[1]:
            dev['city'] = row[1]
        else:
            dev['city'] = ''
        dev['country'] = row[2]
        dev['timestamp'] = row[3]
        dev['lat'] = row[4]
        dev['lon'] = row[5]
        dev['port'] = row[6]
        dev['ins_type'] = row[7]
        devices.append(dev)

    return HttpResponse(json.dumps(devices))


def getVulnerability(request):
    vulDeviceDic = {}
    for item in list(dev2vul.objects.values('device', 'vulnerability')):
        dev = item['device']
        vul = item['vulnerability']
        if vul in vulDeviceDic:
            vulDeviceDic[vul].append(dev)
        else:
            vulDeviceDic[vul] = [dev]

    result = list(vulnerability.objects.values())
    for vul in result:
        if vul['name'] in vulDeviceDic:
            vul['devices'] = vulDeviceDic[vul['name']]
        else:
            vul['devices'] = []

    return HttpResponse(json.dumps(result))
