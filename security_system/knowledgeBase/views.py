# -*- coding:utf-8 -*-
import json

from django.http import HttpResponse

from knowledgeBase.models import vulnerability, device, vendor, instance, dev2vul


# reload(sys)
# sys.setdefaultencoding("utf-8")


def groupCount(request, type):
    list = []
    if type == "vulYear":
        list = vulnerability.objects.values_list('date')
    elif type == "devType":
        list = device.objects.values_list('vendor')
    elif type == "venCountry":
        list = vendor.objects.values_list('country')
    elif type == "insCountry":
        list = instance.objects.values_list('country')
    elif type == "insProtocol":
        list = instance.objects.values_list('ins_type')
    elif type == "venDevice":
        list = device.objects.values_list('vendor')

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
    result = list(instance.objects.values('ip', 'city', 'country', 'ins_type', 'timestamp', 'lat', 'lon', 'port'))
    return HttpResponse(json.dumps(result))


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
