#-*-coding:utf-8-*-
from queryAPI.models import QueryAPI
from django.http import HttpResponse
from client import GremlinRestClient
import json
import time
from django.views.decorators.csrf import csrf_exempt 
import sys
reload(sys)
sys.setdefaultencoding("utf-8")
import threading

import datetime

JSON = json.load(file("/usr/local/security-system-server/security_system/queryAPI/properties.json"))
server = JSON["server"]
graphs = JSON["graphs"]
proConvert = JSON["proConvert"]

userAgentDic = {}
def getGraph(userAgent):
    if userAgent in userAgentDic:
        return userAgentDic[userAgent]
    else:
        return "knowledgeBase"
 
def switchGraph(request, graph):
    if graph in graphs:
        userAgentDic[request.META['HTTP_USER_AGENT']] = graph
        return HttpResponse(json.dumps({"message" : "finished"}))
    else:
        return HttpResponse(json.dumps({"message" : "graph %s does not exist" % graph}))

def index(srcV, dstV):
    return srcV + "-****-" + dstV

# isV(Bool): v-True, e-False
# increase(Bool): show label --> database label: True
def labelConvert(isV, increase, label):
    str = ""
    if isV == True:
        str += "v_"
    else:
        str += "e_"
    
    if increase == True: #show --> database
        return str + label
    else:
        return label.replace(str, "")

#convert a single vertex information from database format to front end format
def convertNode(graph, dic):
    result = {}
    for key, value in dic.items():
        if key in proConvert:
            result[proConvert[key]] = value
    result['type'] = labelConvert(True, False, result['type'])
    if "properties" not in dic:
        return result
    pro = graphs[graph]["properties"]
    for key, value in dic['properties'].items():
        if key in pro:
            result[key] = value[0]['value']
    return result

#convert a series of vertices information from databse format to front end format
def convertNodes(graph, response, nodes):
    for item in response:
        if (item['type'] == 'vertex' and item['label'] != 'vertex'):
            nodes.append(convertNode(graph, item))
    return nodes

#convert a single edge information from database format to front end format
def convertEdge(graph, dic):
    result = {}
    for key, value in dic.items():
        if key in proConvert:
            result[proConvert[key]] = value
    result['type'] = labelConvert(False, False, result['type'])
    if "properties" not in dic:
        return result
    pro = graphs[graph]["properties"]
    for key, value in dic['properties'].items():
        if key in pro:
            result[key] = value
    return result

#convert a series of edges information from databse format to front end format
def convertEdges(graph, response, edges):
    for item in response:
        if (item['type'] == 'edge' and item['label'] != 'vertex'):
            edges.append(convertEdge(graph, item))
    return edges


def getNode(request, key, value):
    graph = getGraph(request.META['HTTP_USER_AGENT'])
    abstract = graphs[graph]["abstract"]
    script = ""
    if key  == "id":
        script += "%s.V(%s);" % (abstract, value)
    elif key == "name":
        script += "%s.V().has('name', textContainsPrefix('%s'));" % (abstract, value)
    response = GremlinRestClient(server).execute(script)[1]
    return HttpResponse(json.dumps(convertNodes(graph, response, [])))

def getEdge(request, source, destination):
    graph = getGraph(request.META['HTTP_USER_AGENT'])
    abstract = graphs[graph]["abstract"]
    script = "%s.V().has('name', 'INDEX').union(" % abstract
    script += "%s.E().has('INDEX', '%s'), " % (abstract, index(source, destination))
    script += "%s.E().has('INDEX', '%s')).limit(%d).unique()" % (abstract, index(destination, source), JSON["CountLimit"])
    response = GremlinRestClient(server).execute(script)[1]
    return HttpResponse(json.dumps(convertEdges(graph, response, [])))

@csrf_exempt
def addNode(request):
    graph = getGraph(request.META['HTTP_USER_AGENT'])
    abstract = graphs[graph]["abstract"]
    dic = json.loads(request.body)
    if "type" not in dic:
        return HttpResponse(json.dumps({"message": "dictionary needs 'type' field."}))
    if "name" not in dic:
        return HttpResponse(json.dumps({"message": "dictionary needs 'name' field."}))
    script = "%s.V().hasLabel('%s').has('name', '%s').count()" % (abstract, labelConvert(True, True, dic['type']), dic['name'])
    count = GremlinRestClient(server).execute(script)[1][0]
    if count > 0:
        return HttpResponse(json.dumps({"message": "database already has this vertex(type: '%s', name: '%s')" % (dic['type'], dic['name'])}))
    
    script = "%s.addV(label, '%s', " % (abstract, labelConvert(True, True, dic['type']))
    pro = graphs[graph]["properties"]
    for key, value in dic.items():
        if key in pro:
            script += "'%s', '%s', " % (key, value)
    script += ")"
    response = GremlinRestClient(server).execute(script)[1]
    
    return HttpResponse(json.dumps(convertNodes(graph, response, [])))

@csrf_exempt
def addEdge(request):
    graph = getGraph(request.META['HTTP_USER_AGENT'])
    abstract = graphs[graph]["abstract"]
    dic = json.loads(request.body)
    if  "type" not in dic:
        return HttpResponse(json.dumps({"message": "dictionary needs 'type' field."}))
    if "srcID" not in dic:
        return HttpResponse(json.dumps({"message": "dictionary needs 'srcID' field."}))
    if "dstID" not in dic:
        return HttpResponse(json.dumps({"message": "dictionary needs 'dstID' field."}))
    srcName = ""
    dstName = ""

    #check whether srcID and dstID exist in database
    script = "%s.V(%s).values('name')" % (abstract, dic['srcID'])
    if len(GremlinRestClient(server).execute(script)[1]) == 0:
        return HttpResponse(json.dumps({"message" : "srcID doesn't exist in database"}))
    else:
        srcName = GremlinRestClient(server).execute(script)[1][0]
    script = "%s.V(%s).values('name')" % (abstract, dic['dstID'])
    if len(GremlinRestClient(server).execute(script)[1]) == 0:
        return HttpResponse(json.dumps({"message" : "dstID doesn't exist in database"}))
    else:
        dstName = GremlinRestClient(server).execute(script)[1][0]
    
    #insert edge into database
    script = "%s.V(%s).next().addEdge('%s', %s.V(%s).next(), " % (abstract, dic['srcID'], labelConvert(False, True, dic['type']), abstract, dic['dstID'])
    pro = graphs[graph]["properties"]
    for key, value in dic.items():
        if key in pro:
            script += "'%s', '%s', " % (key, value)
    script += "'INDEX', '%s')" % index(srcName, dstName)
    response = GremlinRestClient(server).execute(script)[1]
    return HttpResponse(json.dumps(convertEdges(graph, response, [])))

@csrf_exempt
def dropNode(request, id):
    graph = getGraph(request.META['HTTP_USER_AGENT'])
    abstract = graphs[graph]["abstract"]
    script = "%s.V(%s).drop()" % (abstract, id)
    GremlinRestClient(server).execute(script)
    return HttpResponse(json.dumps({"message" : "finished"}))

@csrf_exempt
def dropEdge(request, id):
    graph = getGraph(request.META['HTTP_USER_AGENT'])
    abstract = graphs[graph]["abstract"]
    script = "%s.E('%s').drop()" % (abstract, id)
    GremlinRestClient(server).execute(script)
    return HttpResponse(json.dumps({"message" : "finished"}))

def getNeighborType(request, id):
    graph = getGraph(request.META['HTTP_USER_AGENT'])
    abstract = graphs[graph]["abstract"]
    result = {}

    #get neighborhoods vertices types
    VTypeList = []
    script = "%s.V(%s).both().label().unique()" % (abstract, id)
    response = GremlinRestClient(server).execute(script)[1]
    for type in response:
        if "v_" in type:
            VTypeList.append(labelConvert(True, False, type))
    result["VType"] = VTypeList

    #get neighborhoods edges types
    ETypeList = []
    script = "%s.V(%s).bothE().label().unique()" % (abstract, id)
    response = GremlinRestClient(server).execute(script)[1]
    for type in response:
        if "e_" in type:
            ETypeList.append(labelConvert(False, False, type))
    result["EType"] = ETypeList

    return HttpResponse(json.dumps(result))


@csrf_exempt
def getNeighborhoods(request):
    graph = getGraph(request.META['HTTP_USER_AGENT'])
    abstract = graphs[graph]["abstract"]
    global edgeIndex, resultEdges
    result = {}
    VLimit = ""
    ELimit = ""
    dic = json.loads(request.body)
    
    if "id" not in dic:
        return HttpResponse(json.dumps({"message": "dictionary needs 'id' field."}))
    if "VType" in dic and dic['VType'] != "all":
        VLimit = ".hasLabel('%s')" % labelConvert(True, True, dic['VType'])
    if "EType" in dic and dic['EType'] != "all":
        ELimit = ".hasLabel('%s')" % labelConvert(False, True, dic['EType'])

    #get neighborhoods vertices
    script = "%s.V(%s)%s.both().unique()" % (abstract, dic['id'], VLimit)
    response = GremlinRestClient(server).execute(script)[1]
    if len(response) == 0:
        return HttpResponse(json.dumps({'nodes' : [], 'edges' : []}))
    result['nodes'] = convertNodes(graph, response, [])
    types = {}
    temp = []
    for node in result['nodes']:
        if node['type'] not in types:
            types[node['type']] = 0
        if types[node['type']] < 10:
            temp.append(node)
            types[node['type']] += 1
    result['nodes'] = temp

    #get input node
    script = "%s.V(%s).values('name').limit(1)" % (abstract, dic['id'])
    inputNode = GremlinRestClient(server).execute(script)[1][0]

    #get neighborhoods edges
    edgeIndex = set()
    resultEdges = []
    for node in result['nodes']:
        edgeIndex.add(index(inputNode, node['name']))
        edgeIndex.add(index(node['name'], inputNode))

    threadList = []
    for i in range(0, JSON["threadNum"]):
        thread = getAdjEdgesThread(graph, ELimit)
        threadList.append(thread)
        thread.start()
    for thread in threadList:
        thread.join()
    
    result['edges'] = resultEdges

    return HttpResponse(json.dumps(result))

def getNeigh(request, key, value):
    graph = getGraph(request.META['HTTP_USER_AGENT'])
    abstract = graphs[graph]["abstract"]
    if key != "id":
        return HttpResponse(json.dumps([]))
    
    #get neighborhoods vertices
    script = "%s.V(%s).both().limit(%d).unique();" % (abstract, value, JSON["CountLimit"])
    response = GremlinRestClient(server).execute(script)[1]
    nodes = convertNodes(graph, response, [])
    
    #get neighborhoods edges
    script = "%s.V(%s).bothE().limit(%d).unique();" % (abstract, value, JSON["CountLimit"])
    response = GremlinRestClient(server).execute(script)[1]
    edges = convertEdges(graph, response, [])


    result = {}
    result['edges'] = edges
    result['nodes'] = nodes
    return HttpResponse(json.dumps(result))


def judgeAdj(graph, singleV, multipleV):
    abstract = graphs[graph]["abstract"]
    script = "%s.V().has('name', 'INDEX').limit(1).union(" % abstract
    for vertex in multipleV:
        script += "%s.E().has('INDEX', within('%s', '%s')).limit(1), " % (abstract, index(singleV, vertex), index(vertex, singleV))
    script += ").values('INDEX').unique()"
    result = set()

    for item in GremlinRestClient(server).execute(script)[1]:
        result.add(item.split("-****-")[0])
        result.add(item.split("-****-")[1])
    return result & multipleV

def getAdjNodes(graph, resultNodes):
    abstract = graphs[graph]["abstract"]
    if len(resultNodes) == 0:
        return []
    script = "%s.V().has('name', within(" % abstract
    for vertex in resultNodes:
        script += "'%s', " % vertex
    script += "))"

    response = GremlinRestClient(server).execute(script)[1]
    return convertNodes(graph, response, [])


@csrf_exempt
def commonAdjacent(request):
    graph = getGraph(request.META['HTTP_USER_AGENT'])
    abstract = graphs[graph]["abstract"]
    global inputSet, inputs, edgeIndex, resultEdges
    inputs = {}
    inputNodes = set(json.loads(request.body))
    inputSet = inputNodes.copy()
    
    #get vertices' adjacent edges' counts and sort
    threadList = []
    for i in range(0, JSON["threadNum"]):
        thread = adjCountThread(graph)
        threadList.append(thread)
        thread.start()
    for thread in threadList:
        thread.join()

    inputs = sorted(inputs.iteritems(), key = lambda x:x[1])

    resultNodes = set()
    if len(inputs) != 0:
        script = "%s.V().has('name', '%s').both().values('name').unique()" % (abstract, inputs[0][0])
        resultNodes = set(GremlinRestClient(server).execute(script)[1])

    for i in range(1, len(inputs)):
        if len(resultNodes) == 0:
            break
        resultNodes = judgeAdj(graph, inputs[i][0], resultNodes)
    
    result = {}
    result['nodes'] = getAdjNodes(graph, resultNodes)
    edgeIndex = set()
    resultEdges = []


    for nodeA in inputNodes:
        for nodeB in resultNodes:
            edgeIndex.add(index(nodeA, nodeB))
            edgeIndex.add(index(nodeB, nodeA))

    threadList = []
    for i in range(0, JSON["threadNum"]):
        thread = getAdjEdgesThread(graph)
        threadList.append(thread)
        thread.start()
    for thread in threadList:
        thread.join()

    result['edges'] = resultEdges

    return HttpResponse(json.dumps(result))

inputSet = set()
inputs = {}
threadLock = threading.Lock()
class adjCountThread(threading.Thread):
    def __init__(self, graph):
        threading.Thread.__init__(self)
        self.graph = graph
    
    def run(self):
        abstract = graphs[self.graph]["abstract"]
        while True:
            threadLock.acquire()
            if len(inputSet) == 0:
                threadLock.release()
                break
            name = inputSet.pop()
            threadLock.release()
            
            script = "%s.V().has('name', '%s').bothE().limit(20000).count()" % (abstract, name)
            response = GremlinRestClient(server).execute(script)[1][0]
            inputs[name] = response

edgeIndex = set()
resultEdges = []
class getAdjEdgesThread(threading.Thread):
    def __init__(self, graph, ELimit = ""):
        threading.Thread.__init__(self)
        self.graph = graph
        self.ELimit = ELimit

    def run(self):
        abstract = graphs[self.graph]["abstract"]
        global edgeIndex, resultEdges
        while True:
            threadLock.acquire()
            if len(edgeIndex) == 0:
                threadLock.release()
                return
            script = "%s.V().has('name', 'INDEX').limit(1).union(" % abstract
            for i in range(0, min(8, len(edgeIndex))):
                script += "%s.E().has('INDEX', '%s')%s.limit(%d), " % (abstract, edgeIndex.pop(), self.ELimit, JSON["CountLimit"] / 5)
            script += ")"
            threadLock.release()

            response = GremlinRestClient(server).execute(script)[1]

            threadLock.acquire()
            resultEdges = convertEdges(self.graph, response, resultEdges)
            threadLock.release()

#knowledgeBase only
def groupCount(request, type):
    graph = getGraph(request.META['HTTP_USER_AGENT'])
    abstract = graphs[graph]["abstract"]
    script = "%s." % abstract
    if type == "vulYear":
        script += "V().hasLabel('v_vulnerability').values('timestamp')"
    elif type == "devType":
        script += "V().hasLabel('v_deviceType').outE('e_devType2dev').outV().values('name')"
    elif type == "venCountry":
        script += "V().hasLabel('v_vendor').values('country')"
    elif type == "insCountry":
        script += "V().hasLabel('v_instance').values('country')"
    elif type == "insProtocol":
        script += "V().hasLabel('v_protocol').inE('e_ins2pro').inV().values('name')"
    elif type == "venDevice":
        script += "V().hasLabel('v_vendor').inE('e_dev2vendor').inV().values('name')"

    response = GremlinRestClient(server).execute(script)[1]
    if type == "vulYear":
        for i in range(len(response)):
            response[i] = response[i][0:4]

    dic = {}
    for item in response:
        if item == "":
            continue
        if dic.has_key(item):
            dic[item] += 1
        else:
            dic[item] = 1
    return HttpResponse(json.dumps(dic))

def getInstance(request):
    graph = getGraph(request.META['HTTP_USER_AGENT'])
    abstract = graphs[graph]["abstract"]
    script = "%s.V().has('type_index', 'instance').limit(10000);" %abstract
    response = GremlinRestClient(server).execute(script)[1]
    return HttpResponse(json.dumps(convertNodes(graph, response, [])))

import MySQLdb
import random

def createConnect():

    conn= MySQLdb.connect(
        host='localhost',
        port = 3306,
        user='root',
        passwd='123456',
        db ='ics',
        charset = 'utf8'

    )
    cur = conn.cursor()
    return conn,cur


def getDate(year,month,day,c = -1):
    day = day - 1
    while (day <=0):
        if (month >0):
            month-=1
        else:
            year-=1
            month=12
        day= day+daysOfMonth(month , year)
    date= {"month": month ,"year" : year ,"day":day}
    return date

import time
dateDict = getDate(time.localtime(time.time())[0],time.localtime(time.time())[1],time.localtime(time.time())[2])

thisyear= dateDict["year"]
thismonth=dateDict["month"]
thisday=dateDict["day"]

def getSex(request):
    result = {"Male": 61 , "Female": 39}
    return HttpResponse(json.dumps(result))




def getPlace(request):
#result={}
    #conn, cur = createConnect()
    #province={"beijing":11,"tianjin":12,"hebei":13,"shanxi":14,"neimenggu":15,"liaoning":21,"jilin":22,"heilongjiang":23,"shanghai":31,"jiangsu":32,"zhejiang":33,"anhui":34,"fujian":35,"jiangxi":36,"shandong":37,"henan":41,"hubei":42,"hunan":43,"guangdong":44,"guangxi":45,"hainan":46,"chongqing":50,"sichuan":51,"guizhou":52,"yunnan":53,"xizang":54,"shan_xi":61,"gansu":62,"qinghai":63,"ningxia":64,"xinjiang":65,"taiwan":71,"xianggang":81,"aomen":82}
    #for (k,v) in province.items():
        #cur.execute("select count(*) from weibo inner join userinfo on weibo.uid = userinfo.rowkey and userinfo.province = \'"+str(v)+"\'")
        #row=cur.fetchone()
        #result[k]=row[0]
    #cur.close()
    #conn.close()
    result = {"beijing": 4936, "shandong": 1322, "hunan": 696, "guangxi": 420, "xianggang": 209, "qinghai": 173, "jiangsu": 1460, "ningxia": 256, "sichuan": 892, "aomen": 67, "liaoning": 712, "taiwan": 123, "guangdong": 7125, "jilin": 358, "shanxi": 554, "anhui": 702, "tianjin": 482, "shanghai": 1757, "xizang": 97, "shan_xi": 609, "gansu": 361, "hebei": 860, "hainan": 241, "neimenggu": 309, "yunnan": 756, "hubei": 760, "zhejiang": 1233, "heilongjiang": 472, "chongqing": 408, "xinjiang": 220, "henan": 876, "guizhou": 287, "fujian": 976, "jiangxi": 391}
    return HttpResponse(json.dumps(result))

def daysOfMonth(month,year):
    if(month==1|month==3|month==5|month==7|month==8|month==10|month==12):
        return 31
    elif(month==4|month == 6|month ==9|month==11):
        return 30
    else:
        if(year % 4==0):
            return 29
        else:
            return 28

import calendar
def add_months(dt,months):
    month = dt.month - 1 + months
    year = dt.year + month // 12
    month = month % 12 + 1
    print(year,month)
    day = min(dt.day,calendar.monthrange(year,month)[1])
    print(year,month,day)
    return dt.replace(year=year, month=month, day=day)

def timeRange(flag):
    start = datetime.datetime.now()
    end = 0
    if(flag == '1day'):
        end = start-datetime.timedelta(hours=24)
    elif(flag == '7days'):
        end = start-datetime.timedelta(hours=24*7)
    elif(flag == '1month'):
        end = add_months(start,-1)
    elif(flag == '3months'):
        end = add_months(start,-3)
    elif(flag == 'all'):
        end = start.replace(year = 2014, month = 1, day = 1)
    return start,end

def getLine(request,flag='3months'):
    conn,cur=createConnect()
    rows = {}
    start,end = timeRange(flag) 
    while(start!=end):
        cur.execute("select count(*) from weibo where  date = \'"+start.strftime('%Y%m%d')+"\'")
        row = cur.fetchone()
        rows[start.strftime('%Y%m%d')] = row[0]
        start = start - datetime.timedelta(hours=24)
    cur.close()
    conn.close()
    return HttpResponse(json.dumps(rows))
    

def getFans(request,flag='3months'):
    conn, cur = createConnect()
    result={"<100":0,"100-1000":0,"1000-10000":0,"10000-100000":0,"100000-1000000":0,">1000000":0}

    start,end = timeRange(flag)

    while(start!=end):
        cur.execute("select  count(username) from weibo where  fans < \'100\' and date = \'"+start.strftime('%Y%m%d')+"\'")
        row = cur.fetchone()
        result["<100"]+=row[0]
        cur.execute("select  count(username) from weibo where  fans < \'1000\' and fans > \'100\' and date = \'"+start.strftime('%Y%m%d')+"\'")
        row = cur.fetchone()
        result["100-1000"]+=row[0]
        cur.execute("select  count(username) from weibo where  fans < \'10000\' and fans > \'1000\' and date = \'"+start.strftime('%Y%m%d')+"\'")
        row = cur.fetchone()
        result["1000-10000"]+=row[0]
        cur.execute("select  count(username) from weibo where  fans < \'100000\' and fans > \'10000\' and date = \'"+start.strftime('%Y%m%d')+"\'")
        row = cur.fetchone()
        result["10000-100000"]+=row[0]
        cur.execute("select  count(username) from weibo where  fans < \'1000000\' and fans > \'100000\' and date = \'"+start.strftime('%Y%m%d')+"\'")
        row = cur.fetchone()
        result["100000-1000000"]+=row[0]
        cur.execute("select  count(username) from weibo where  fans > \'1000000\' and date = \'"+start.strftime('%Y%m%d')+"\'")
        row = cur.fetchone()
        result[">1000000"]+=row[0]
        start = start - datetime.timedelta(hours=24)
    print row
    cur.close()
    conn.close()
    return HttpResponse(json.dumps(result))


def getRepost(request,flag='3months'):
    conn, cur = createConnect()
    result={"<5":0,"5-10":0,"10-50":0,"50-100":0,"100-500":0,"500-1000":0,">1000":0}
    
    start,end = timeRange(flag)
    while(start!=end):
        cur.execute("select  count(*) from weibo where  repostcount < \'5\' and fans > \'100\' and date = \'"+start.strftime('%Y%m%d')+"\'")
        row = cur.fetchone()
        result["<5"]+=row[0]
        cur.execute("select  count(*) from weibo where  repostcount < \'10\' and repostcount > \'5\' and fans > \'100\' and date = \'"+start.strftime('%Y%m%d')+"\'")
        row = cur.fetchone()
        result["5-10"]+=row[0]
        cur.execute("select  count(*) from weibo where  repostcount < \'50\' and repostcount > \'10\' and fans > \'100\' and date = \'"+start.strftime('%Y%m%d')+"\'")
        row = cur.fetchone()
        result["10-50"]+=row[0]
        cur.execute("select  count(*) from weibo where  repostcount < \'100\' and repostcount > \'50\' and fans > \'100\' and date = \'"+start.strftime('%Y%m%d')+"\'")
        row = cur.fetchone()
        result["50-100"]+=row[0]
        cur.execute("select  count(*) from weibo where  repostcount < \'500\' and repostcount > \'100\' and fans > \'100\' and date = \'"+start.strftime('%Y%m%d')+"\'")
        row = cur.fetchone()
        result["100-500"]+=row[0]
        cur.execute("select  count(*) from weibo where  repostcount < \'1000\' and repostcount > \'500\' and fans > \'100\' and date = \'"+start.strftime('%Y%m%d')+"\'")
        row = cur.fetchone()
        result["500-1000"]+=row[0]
        cur.execute("select  count(*) from weibo where  repostcount > \'1000\' and fans > \'100\' and date = \'"+start.strftime('%Y%m%d')+"\'")
        row = cur.fetchone()
        result[">1000"]+=row[0]
        start = start - datetime.timedelta(hours=24)
    cur.close()
    conn.close()
    return HttpResponse(json.dumps(result))

def getweiboInfo(request):
    conn, cur = createConnect()
    result =[]
    year=2016
    month=8
    day=26
    i = 0
    while (i<30):
        if month<10:
            theMonth="0"+str(month)
        else:
            theMonth=str(month)
        if(day<10):
            theDay="0"+str(day)
        else:
            theDay=str(day)
        date=str(year)+theMonth+theDay
        cur.execute("select fans,repostcount,id,date from weibo where repostcount >0 and date =" +date)
        results = cur.fetchall()
        for row in results:
            weibo = {}
            weibo["fans"] = row[0]
            weibo["repostcount"] = row[1]
            weibo["id"] = row[2]
            weibo["date"] = row[3]
            result.append(weibo)
            if i == 30:
                break
        newdate = getDate(year, month, day)
        year = newdate["year"]
        month = newdate["month"]
        day = newdate["day"]
        i += 1
    cur.close()
    conn.close()
    return HttpResponse(json.dumps(result))

def getWeibo(request):
    conn, cur = createConnect()
    result=[]
    year=thisyear
    month=thismonth
    day=thisday
    i=0
    while (i<20):
        if month<10:
            theMonth="0"+str(month)
        else:
            theMonth=str(month)
        if(day<10):
            theDay="0"+str(day)
        else:
            theDay=str(day)
        date=str(year)+theMonth+theDay
        cur.execute("select con,date,fans,location,uid,headpic,username,repostcount,id from weibo where creator !=0 ORDER BY date DESC")
        results = cur.fetchall()
        for row in results:
            i+=1
            weibo = {}
            weibo["content"] = row[0]
            weibo["date"] = row[1]
            weibo["fans"] = row[2]
            weibo["location"] = row[3]
            weibo["uid"] = row[4]
            weibo["headpic"] = row[5]
            weibo["username"] = row[6]
            weibo["repostcount"] = row[7]
            weibo["id"] = row[8]
            result.append(weibo)
            if i == 20:
                break
        newdate=getDate(year,month,day)
        year=newdate["year"]
        month=newdate["month"]
        day=newdate["day"]
    cur.close()
    conn.close()
    return HttpResponse(json.dumps(result))

def getPaper(request):
    conn, cur = createConnect()
    result = []
    cur.execute("select title,ee from papercisr")
    results = cur.fetchall()
    for row in results:
        paper = {}
        paper["title"] = row[0]
        paper["url"] = row[1]
        paper["keywords"] = "scada,ics,security"
        result.append(paper)

    cur.execute("select title,url from papericscsr")
    results = cur.fetchall()
    for row in results:
        paper = {}
        paper["title"] = row[0]
        paper["url"] = row[1]
        paper["keywords"] = "scada,ics,security"
        result.append(paper)
    cur.execute("select title,url from paperwcicss")
    results = cur.fetchall()
    for row in results:
        paper = {}
        paper["title"] = row[0]
        paper["url"] = row[1]
        paper["keywords"] = "scada,ics,security"
        result.append(paper)
    
    cur.execute("select title,url,keywords from papersp")
    results = cur.fetchall()
    for row in results:
        paper = {}
        paper["title"] = row[0]
        paper["url"] = row[1]
        paper["keywords"] = row[2]
        result.append(paper)
    cur.close()
    conn.close()
    return HttpResponse(json.dumps(result))


def getShop(request):
    conn, cur = createConnect()
    result = []
    cur.execute("select name,contact,phone,mobile,fox,email,QQ,url,address,postcode,products,introduction from shoplist")
    results = cur.fetchall()
    for row in results:
        shop = {}
        shop["name"] = row[0]
        shop["contact"] = row[1]
        shop["phone"] = row[2]
        shop["mobile"] = row[3]
        shop["fox"] = row[4]
        shop["email"] = row[5]
        shop["QQ"] = row[6]
        shop["url"] = row[7]
        shop["address"] = row[8]
        shop["postcode"] = row[9]
        shop["products"] = row[10]
        #shop["introduction"] = row[11]
        result.append(shop)
    cur.close()
    conn.close()
    return HttpResponse(json.dumps(result))
def getCNContent(request,date,source):
    conn, cur = createConnect()
    result=[]
    if date == '0':
        dateSearch=""
    else:
        dateSearch = " where time =" + str(date)
    if(source=='0' or source=="workspace"):
        cur.execute("select time,content,url from workspace" + dateSearch)
        results = cur.fetchall()
        for row in results:
            workspace = {}
            workspace["date"] = row[0]
            workspace["content"] = row[1]
            workspace["source"] = "workspace"
            workspace["url"] = row[2]
            result.append(workspace)
    if(source=='0' or source =='news'):
        cur.execute("select time,con,url from news"+dateSearch)
        results = cur.fetchall()
        for row in results:
            news = {}
            news["date"] = row[0]
            news["content"] = row[1]
            news["source"] = "ringnews"
            news["url"] = row[2]
            result.append(news)
    if (source == '0' or source == 'weibo'):
        cur.execute("select date,con,time from weibo where date ="+ str(date))
        results = cur.fetchall()
        for row in results:
            weibo = {}
            if row[2]!= None:
                weibo["date"] = row[0]+row[2]
            else:
                weibo["date"] = row[0]
            weibo["content"] = row[1]
            weibo["source"] = "ringweibo"
            weibo["url"] = "weibo"
            result.append(weibo)
			
    if (source == '0' or source == 'aqniulist'):
        cur.execute("select title,time,author,contents from aqniulist where date ="+ str(date))
        results = cur.fetchall()
        for row in results:
            aqniu = {}
            aqniu['title'] = row[0]
            aqniu['time'] = row[1]
            aqniu['author'] = row[2]
            aqniu['contents'] = row[3]
            result.append(aqniu)
    
    if (source == '0' or source == 'yqms'):
        cur.execute("select time,source,kind,link,content from yqms where date ="+ str(date))
        results = cur.fetchall()
        for row in results:
            yqms = {}
            yqms['time'] = row[0]
            yqms['source'] = row[1]
            yqms['kind'] = row[2]
            yqms['link'] = row[3]
            yqms['content'] = row[4]
            result.append(yqms)

########################################## update on 2016.12.12 ##################################################
    if (source == '0' or source == 'anqniu'):
        cur.execute("select title,author,time,article,tags,kind from anqniu" + dateSearch)
        results = cur.fetchall()
        for row in results:
            anqniu = {}
            anqniu['title'] = row[0]
            anqniu['author'] = row[1]
            anqniu['time'] = row[2]
            anqniu['article'] = row[3]
            anqniu['tags'] = row[4]
            anqniu['kind'] = row[5]
            result.append(anqniu)
##################################################################################################################

    cur.close()
    conn.close()
    return HttpResponse(json.dumps(result))

def getENContent(request,date,source):
    conn, cur = createConnect()
    result = []
    if(date=='0'):
        dateSearch=""
    else:
        dateSearch=" where time ="+str(date)
    if (source == '0' or source == 'scadablog'):
        cur.execute("select time,content,url from scadablog"+dateSearch)
        results = cur.fetchall()
        for row in results:
            blog = {}
            blog["date"] = row[0]
            blog["content"] = row[1]



            blog["source"] = "scadahacker"
            blog["url"] = row[2]
            result.append(blog)
    if (source == '0' or source == 'scadanews'):
        cur.execute("select time,content,sourceurl from scadanews" + dateSearch)
        results = cur.fetchall()
        for row in results:
            scadanews = {}
            scadanews["date"] = row[0]
            scadanews["content"] = row[1]
            scadanews["source"] = "scadahacker"
            scadanews["url"] = row[2]
            result.append(scadanews)
########################################## update on 2016.12.12 ##################################################
##    if (source == '0' or source == 'icscert'):
##        cur.execute("select title,name,date,contents from icscert where date ="+ str(date))
##        results = cur.fetchall()
##        for row in results:
##            icscert = {}
##            icscert['title'] = row[0]
##            icscert['name'] = row[1]
##            icscert['date'] = row[2]
##            icscert['content'] = row[3]
##            result.append(icscert)

    if (source == '0' or source == 'icscert'):
        if(date=='0'):
            dateSearch=""
        else:
            dateSearch=" where date ="+str(date)
        cur.execute("select title,name,date,contents from icscert" + dateSearch)
        results = cur.fetchall()
        for row in results:
            icscert = {}
            icscert['title'] = row[0]
            icscert['name'] = row[1]
            icscert['date'] = row[2]
            icscert['content'] = row[3]
            result.append(icscert)


        

    
    if (source == '0' or source == 'securityweek'):
        cur.execute("select title,author,time,article,Tags,kind from securityweek" + dateSearch)
        results = cur.fetchall()
        for row in results:
            securityweek = {}
            securityweek["title"] = row[0]
            securityweek["author"] = row[1]
            securityweek["time"] = row[2]
            securityweek["article"] = row[3]
            securityweek["tags"] = row[4]
            securityweek["kind"] = row[5]
            result.append(securityweek)
##################################################################################################################
    cur.close()
    conn.close()
    return HttpResponse(json.dumps(result))

##########################################update on 2016.12.14 #####################################
def getENBlog(request,i_d,source):
    conn, cur = createConnect()
    result = []
    if(i_d=='0'):
        idSearch=""
    else:
        idSearch=" where id ="+str(i_d)

    if (source == '0' or source == 'securityweek'):
        cur.execute("select title,author,time,article,Tags,kind from securityweek" + idSearch)
        results = cur.fetchall()
        for row in results:
            securityweek = {}
            securityweek["source"] = "securityweek"
            securityweek["title"] = row[0]
            securityweek["author"] = row[1]
            securityweek["time"] = row[2]
            securityweek["article"] = row[3]
            securityweek["tags"] = row[4]
            securityweek["kind"] = row[5]
            result.append(securityweek)
            
    if (source == '0' or source == 'arc_europe'):
        cur.execute("select title,author,time,article,curtime from arc_europe" + idSearch)
        results = cur.fetchall()
        for row in results:
            arc_europe = {}
            arc_europe["source"] = "arc_europe"
            arc_europe["title"] = row[0]
            arc_europe["author"] = row[1]
            arc_europe["time"] = row[2]
            arc_europe["article"] = row[3]
            arc_europe["curtime"] = row[4]
            result.append(arc_europe)

    if (source == '0' or source == 'arc_industrial_iot'):
        cur.execute("select title,author,time,categories,tags,article,curtime from arc_industrial_iot" + idSearch)
        results = cur.fetchall()
        for row in results:
            arc_industrial_iot = {}
            arc_industrial_iot["source"] = "arc_industrial_iot"
            arc_industrial_iot["title"] = row[0]
            arc_industrial_iot["author"] = row[1]
            arc_industrial_iot["time"] = row[2]
            arc_industrial_iot["categories"] = row[3]
            arc_industrial_iot["tags"] = row[4]
            arc_industrial_iot["article"] = row[5]
            arc_industrial_iot["curtime"] = row[6]
            result.append(arc_industrial_iot)
            
    if (source == '0' or source == 'arc_logisticsviewpoints'):
        cur.execute("select title,author,time,categories,tags,article,curtime from arc_logisticsviewpoints" + idSearch)
        results = cur.fetchall()
        for row in results:
            arc_logisticsviewpoints = {}
            arc_logisticsviewpoints["source"] = "arc_logisticsviewpoints"
            arc_logisticsviewpoints["title"] = row[0]
            arc_logisticsviewpoints["author"] = row[1]
            arc_logisticsviewpoints["time"] = row[2]
            arc_logisticsviewpoints["categories"] = row[3]
            arc_logisticsviewpoints["tags"] = row[4]
            arc_logisticsviewpoints["article"] = row[5]
            arc_logisticsviewpoints["curtime"] = row[6]
            result.append(arc_logisticsviewpoints)

    if (source == '0' or source == 'arcnews'):
        cur.execute("select title,author,news,keywords,time,curtime from arcnews" + idSearch)
        results = cur.fetchall()
        for row in results:
            arcnews = {}
            arcnews["source"] = "arcnews"
            arcnews["title"] = row[0]
            arcnews["author"] = row[1]
            arcnews["article"] = row[2]
            arcnews["keywords"] = row[3]
            arcnews["time"] = row[4]
            arcnews["curtime"] = row[5]
            result.append(arcnews)

    if (source == '0' or source == 'ibm_securityintelligence'):
        cur.execute("select title,time,timeandauthor,tags,article,curtime from ibm_x_f_e_securityintelligence" + idSearch)
        results = cur.fetchall()
        for row in results:
            ibm_securityintelligence = {}
            ibm_securityintelligence["source"] = "ibm_securityintelligence"
            ibm_securityintelligence["title"] = row[0]
            ibm_securityintelligence["time"] = row[1]
            ibm_securityintelligence["timeandauthor"] = row[2]
            ibm_securityintelligence["tags"] = row[3]
            ibm_securityintelligence["article"] = row[4]
            ibm_securityintelligence["curtime"] = row[5]
            result.append(ibm_securityintelligence)

    if (source == '0' or source == 'infosecisland'):
        cur.execute("select title,time,author,article,Categories,Tags from infosecisland" + idSearch)
        results = cur.fetchall()
        for row in results:
            infosecisland = {}
            infosecisland["source"] = "infosecisland"
            infosecisland["title"] = row[0]
            infosecisland["time"] = row[1]
            infosecisland["author"] = row[2]
            infosecisland["article"] = row[3]
            infosecisland["categories"] = row[4]
            infosecisland["tags"] = row[5]
            result.append(infosecisland)

    if (source == 'url' or source == '0' or source == 'nakedsecurity'):
        cur.execute("select titlet,time,author,article,tags,authorinfo,url,curtime from nakedsecurity" + idSearch)
        results = cur.fetchall()
        for row in results:
            nakedsecurity = {}
            nakedsecurity["source"] = "nakedsecurity"
            nakedsecurity["title"] = row[0]
            nakedsecurity["time"] = row[1]
            nakedsecurity["author"] = row[2]
            nakedsecurity["article"] = row[3]
            nakedsecurity["tags"] = row[4]
            nakedsecurity["authorinfo"] = row[5]
            nakedsecurity["url"] = row[6]
            nakedsecurity["curtime"] = row[7]
            result.append(nakedsecurity)

    if (source == 'url' or source == '0' or source == 'trustwave'):
        cur.execute("select title,time,author,article,tags,curtime,url from trustwave_blog" + idSearch)
        results = cur.fetchall()
        for row in results:
            trustwave = {}
            trustwave["source"] = "trustwave"
            trustwave["title"] = row[0]
            trustwave["time"] = row[1]
            trustwave["author"] = row[2]
            trustwave["article"] = row[3]
            trustwave["tags"] = row[4]
            trustwave["curtime"] = row[5]
            trustwave["url"] = row[6]
            result.append(trustwave)

    if (source == 'url' or source == '0' or source == 'scadablog'):
        cur.execute("select time,title,content,author,url from scadablog" + idSearch)
        results = cur.fetchall()
        for row in results:
            scadablog = {}
            scadablog["source"] = "scadahacker"
            scadablog["time"] = row[0]
            scadablog["title"] = row[1]         
            scadablog["article"] = row[2]
            scadablog["author"] = row[3]
            scadablog["url"] = row[4]
            result.append(scadablog)
            
    if (source == 'url' or source == '0' or source == 'scadanews'):
        cur.execute("select title,type,content,time,sourceurl from scadanews" + idSearch)
        results = cur.fetchall()
        for row in results:
            scadanews = {}
            scadanews["source"] = "scadahacker"
            scadanews["title"] = row[0]
            scadanews["type"] = row[1]
            scadanews["article"] = row[2]
            scadanews["time"] = row[3]
            scadanews["url"] = row[4]
            result.append(scadanews)

    if (source == 'url' or source == '0' or source == 'spiderlabs_blog'):
        cur.execute("select time,title,article,author,url,tags,curtime from 'spiderlabs_blog" + idSearch)
        results = cur.fetchall()
        for row in results:
            spiderlabs = {}
            spiderlabs["source"] = "spiderlabs"
            spiderlabs["time"] = row[0]
            spiderlabs["title"] = row[1]         
            spiderlabs["article"] = row[2]
            spiderlabs["author"] = row[3]
            spiderlabs["url"] = row[4]
            spiderlabs["tags"] = row[5]
            spiderlabs["curtime"] = row[6]
            result.append(spiderlabs)

    if (source == 'url' or source == '0' or source == 'threadpost'):
        cur.execute("select titlet,time,author,article,aboutauthor,catagories,url,curtime from threadpost" + idSearch)
        results = cur.fetchall()
        for row in results:
            threadpost = {}
            threadpost["source"] = "threadpost"
            threadpost["title"] = row[0]
            threadpost["time"] = row[1]
            threadpost["author"] = row[2]
            threadpost["article"] = row[3]
            threadpost["aboutauthor"] = row[4]
            threadpost["catagories"] = row[5]
            threadpost["url"] = row[6]
            threadpost["curtime"] = row[7]
            result.append(threadpost)

    cur.close()
    conn.close()
    return HttpResponse(json.dumps(result))


def getCNBlog(request,i_d,source):
    conn, cur = createConnect()
    result = []
    if(i_d=='0'):
        idSearch=""
    else:
        idSearch=" where id ="+str(i_d)

    if (source == '0' or source == 'anqniu'):
        cur.execute("select title,author,time,article,tags,kind from anqniu" + idSearch)
        results = cur.fetchall()
        for row in results:
            anqniu = {}
            anqniu["source"] = "anqniu"
            anqniu['title'] = row[0]
            anqniu['author'] = row[1]
            anqniu['time'] = row[2]
            anqniu['article'] = row[3]
            anqniu['tags'] = row[4]
            anqniu['kind'] = row[5]
            result.append(anqniu)

    if (source == '0' or source == 'tower'):
        cur.execute("select title,timeandfrom,article,kind from tower" + idSearch)
        results = cur.fetchall()
        for row in results:
            tower = {}
            tower["source"] = "tower"
            tower['title'] = row[0]
            tower['timeandfrom'] = row[1]
            tower['article'] = row[2]
            tower['kind'] = row[3]
            result.append(tower)


    cur.close()
    conn.close()
    return HttpResponse(json.dumps(result))

#####################################################################################################

def countYears(request):
    conn, cur = createConnect()
    result = []
    cur.execute("select finddate from cve")
    results = cur.fetchall()
    num = [0 for x in range(0, 17)]
    count0 = {}

    for row in results:
        if (row[0][6:10] == '2000'):
           num[0] += 1
        elif (row[0][6:10] == '2001'):
            num[1] += 1
        elif (row[0][6:10] == '2002'):
            num[2] += 1
        elif (row[0][6:10] == '2003'):
            num[3] += 1
        elif (row[0][6:10] == '2004'):
            num[4] += 1
        elif (row[0][6:10] == '2005'):
            num[5] += 1
        elif (row[0][6:10] == '2006'):
            num[6] += 1
        elif (row[0][6:10] == '2007'):
            num[7] += 1
        elif (row[0][6:10] == '2008'):
            num[8] += 1
        elif (row[0][6:10] == '2009'):
            num[9] += 1
        elif (row[0][6:10] == '2010'):
            num[10] += 1
        elif (row[0][6:10] == '2011'):
            num[11] += 1
        elif (row[0][6:10] == '2012'):
            num[12] += 1
        elif (row[0][6:10] == '2013'):
            num[13] += 1
        elif (row[0][6:10] == '2014'):
            num[14] += 1
        elif (row[0][6:10] == '2015'):
            num[15] += 1
        elif (row[0][6:10] == '2016'):
            num[16] += 1
    for i in range(0,17):
        if (i >= 10):
            year = '20' + str(i)
        else:
            year = '200' + str(i)
        count0[year] = str(num[i])
    
    cur.close()
    conn.close()
    return HttpResponse(json.dumps(count0))

def getCve(request):
    conn,cur = createConnect()
    result = []
    cur.execute("select num,score,finddate,summary from cve")
    results = cur.fetchall()
    for row in results:
        cves = {}
        cves["id"] = row[0]
        cves["score"] = row[1][1:3]
        cves["finddate"] = row[2][6:16]
        cves["summary"] = row[3][4:]
        result.append(cves)

    cur.close()
    conn.close()
    return HttpResponse(json.dumps(result))

def getIps(request):
    conn,cur = createConnect()
    result = []
    cur.execute("select * from ips")
    results = cur.fetchall()
    for row in results:
        cves = {}
        cves["ip"] = row[0]
        cves["country"] = row[1]
        cves["totals"] = row[2]
        cves["first"] = row[3]
        cves["last"] = row[4]
        cves["kind"] = row[5]
        result.append(cves)

    cur.close()
    conn.close()
    return HttpResponse(json.dumps(result))

def getNews(request):
    conn, cur = createConnect()
    result=[]
    year=thisyear
    month=thismonth
    day=thisday

    i=0
    while (True):
        if month<10:
            theMonth="0"+str(month)
        else:
            theMonth=str(month)
        if(day<10):
            theDay="0"+str(day)
        else:
            theDay=str(day)
        date=str(year)+theMonth+theDay
        cur.execute("select time,con,source,url,title from news ORDER BY time DESC")
        results = cur.fetchall()
        for row in results:
            i= i + 1
            news = {}
            news["time"]=row[0]
            news["content"]=row[1][0:100]
            news["source"]=row[2]
            news["url"]=row[3]
            news["title"]=row[4]
            result.append(news)
            if i >= 20:
                break
        newdate=getDate(year,month,day)
        year=newdate["year"]
        month=newdate["month"]
        day=newdate["day"]
        if i>=20:
            break
    print i
    cur.close()
    conn.close()
    return HttpResponse(json.dumps(result))


def getScadablog(request):
    conn, cur = createConnect()
    result=[]
    year=thisyear
    month=thismonth
    day=thisday
    i=0

    while (True):
        """if month<10:
            theMonth="0"+str(month)
        else:
            theMonth=str(month)
        if(day<10):
            theDay="0"+str(day)
        else:
            theDay=str(day)
        date=str(year)+theMonth+theDay"""
        cur.execute("select time,content,author,url,title from scadablog  ORDER BY time DESC")
        results = cur.fetchall()
        for row in results:
            i+=1
            blog = {}
            blog["time"]=row[0]
            blog["content"]=row[1]
            blog["author"]=row[2]
            blog["url"]=row[3]
            blog["title"]=row[4]
            result.append(blog)
            if i>=40:
                break
        break
        newdate=getDate(year,month,day)
        year=newdate["year"]
        month=newdate["month"]
        day=newdate["day"]
    cur.close()
    conn.close()
    return HttpResponse(json.dumps(result))

def getScadanews(request):
    conn, cur = createConnect()
    result=[]
    year=thisyear
    month=thismonth
    day=thisday
    i=0

    while (True):
        cur.execute("select time,text1,type,sourceurl,title,source,photourl from scadanews ORDER BY time DESC")
        results = cur.fetchall()
        for row in results:
            i+=1
            news = {}
            news["time"]=row[0]
            news["text1"]=row[1]
            news["type"]=row[2]
            news["url"]=row[3]
            news["title"]=row[4]
            news["source"]=row[5]
            news["photourl"]=row[6]
            result.append(news)
            if i >= 40:
                break
        break
    cur.close()
    conn.close()
    return HttpResponse(json.dumps(result))

def getAttackMap(request,size=-1):
    conn, cur = createConnect()
    map = {}

    if size == -1:
        cur.execute("select time,attacker,attackIP,attackerGeo,targetGeo,attackType,port from attackmap ")
    else:
        type=random.randint(1, 11)
        cur.execute("select time,attacker,attackIP,attackerGeo,targetGeo,attackType,port from attackmap where type = \'"+str(type)+"\'")
    results = cur.fetchall()
    for row in results:
        print row
        time=row[0]
        attack = {}
        attack["attacker"]=row[1]
        attack["attackIP"]=row[2]
        attack["attackGeo"]=row[3]
        attack["targetGeo"]=row[4]
        attack["attackType"]=row[5]
        attack["port"]=row[6]
        cur.execute("select latitude , longitude from location where place = \'"+attack["attackGeo"]+"\'")
        row= cur.fetchone()
        print row
        if row==None:
            attack["attackLatitude"]=0
            attack["attackLongitude"]=0
        else:
            attack["attackLatitude"]=row[0]
            attack["attackLongitude"]=row[1]
        cur.execute("select latitude , longitude from location where place = \'" + attack["targetGeo"] + "\'")
        row = cur.fetchone()
        print row
        if row==None:
            attack["targetLatitude"]=0
            attack["targetLongitude"]=0
        else:
            attack["targetLatitude"] = row[0]
            attack["targetLongitude"] = row[1]
        map[time]=attack
    cur.close()
    conn.close()
    return HttpResponse(json.dumps(map))

def getAttacker(request):
    conn, cur = createConnect()
    result={}
    cur.execute("select attackerGeo from attackmap ")
    results = cur.fetchall()
    for row in results:
        attacker=row[0]
        cur.execute("select count(*) from attackmap where attackerGeo=\'"+attacker+"\'")
        row=cur.fetchone()
        result[attacker]=row[0]
    cur.close()
    conn.close()
    return HttpResponse(json.dumps(result))
def getTarget(request):
    conn, cur = createConnect()
    result = {}
    cur.execute("select targetGeo from attackmap ")
    results = cur.fetchall()
    for row in results:
        target = row[0]
        cur.execute("select count(*) from attackmap where targetGeo=\'" + target + "\'")
        row = cur.fetchone()
        result[target] = row[0]
    cur.close()
    conn.close()
    return HttpResponse(json.dumps(result))

def getType(request):
    conn, cur = createConnect()
    result={}
    cur.execute("select attackType from attackmap ")
    results = cur.fetchall()
    for row in results:
        type=row[0]
        cur.execute("select count(*) from attackmap where attackType = \'"+type+"\'")
        row=cur.fetchone()
        result[type]=row[0]
    cur.close()
    conn.close()
    return HttpResponse(json.dumps(result))

from knowledgeBase.models import vulnerability,device,instance

def VulIndex():
    result={}
    index={}
    year = thisyear
    month = thismonth
    day = thisday
    max=0
    list=vulnerability.objects.values('level','date')
    for vulner in list:
        i=0
        time=vulner["date"]
        if time =="":
            continue
        date=time[0:4]+time[5:7]+time[8:10]
        if vulner["level"]==u'\u4f4e':
            i=2
        elif vulner["level"]==u'\u4e2d':
            i=5
        elif vulner["level"]==u'\u9ad8':
            i=10
        if time in result:
            result[date] += i
        else:
            result[date]=i
    for number in result:
        if max< result[number]:
            max=result[number]
    #result = sorted(result.iteritems(),key=lambda d:d[0])
    for i in range(0,100):
        loopyear = year
        loopmonth = month
        loopday = day
        if month < 10:
            tMonth = "0" + str(loopmonth)
        else:
            tMonth = str(loopmonth)
        if day < 10:
            tDay = "0" + str(loopday)
        else:
            tDay = str(day)
        date = str(year) + tMonth + tDay
        tindex=float(0)
        for j in range(1,101):
            if loopmonth < 10:
                theMonth = "0" + str(loopmonth)
            else:
                theMonth = str(loopmonth)
            if loopday < 10:
                theDay = "0" + str(loopday)
            else:
                theDay = str(loopday)
            loopdate = str(year) + theMonth + theDay
            if loopdate in result:
                tindex += 100*result[loopdate]/float(j*max)
            newdate = getDate(loopyear, loopmonth, loopday)
            loopyear = newdate["year"]
            loopmonth = newdate["month"]
            loopday = newdate["day"]
        index[date]=tindex
        newdate = getDate(year, month, day)
        year = newdate["year"]
        month = newdate["month"]
        day = newdate["day"]
    #index = sorted(index.iteritems(),key=lambda d:d[0])
    return index

def getVulIndex(request):
    result=VulIndex()
    return HttpResponse(json.dumps(result))

threaten={}
for i in range(0,100):
    threaten[i]=random.randint(30, 60)
def ThreatenIndex():
    result={}
    year = thisyear
    month = thismonth
    day = thisday
    for i in range(0, 100):
        if month < 10:
            theMonth = "0" + str(month)
        else:
            theMonth = str(month)
        if (day < 10):
            theDay = "0" + str(day)
        else:
            theDay = str(day)
        date = str(year) + theMonth + theDay
        result[date]=threaten[i]
        newdate = getDate(year, month, day)
        year = newdate["year"]
        month = newdate["month"]
        day = newdate["day"]
    return result


def getThreatenIndex(request):
    return HttpResponse(json.dumps(ThreatenIndex()))

def PublicIndex():
    conn, cur = createConnect()
    year = thisyear
    month = thismonth
    day = thisday
    result = {}
    rows = {}
    max1 = 0
    max2 = 0
    for i in range(0, 200):
        if month < 10:
            theMonth = "0" + str(month)
        else:
            theMonth = str(month)
        if (day < 10):
            theDay = "0" + str(day)
        else:
            theDay = str(day)

        date = str(year) + theMonth + theDay
        cur.execute("select count(*) from weibo where date = \'" + date + "\'")
        row1 = cur.fetchone()
        cur.execute("select count(*) from news where time = \'" + date + "\'")
        row2 = cur.fetchone()
        newdate = getDate(year, month, day)
        year = newdate["year"]
        month = newdate["month"]
        day = newdate["day"]
        num = {}
        #num["weibo"] = row1[0]
        #num["news"] = row2[0]
        num["value"]=0.7*row2[0]+0.3*row1[0]
        num["date"]=date
        rows[i] = num
    for j in range(0,100):
        num2=rows[j]
        date=num2["date"]
        result[date]=0
        for dayNumber in range(j,j+100):
            thisNum = rows[dayNumber]
            if num2["value"]>= thisNum["value"]:
                result[date] +=1
        # print row1[0] ,"**", row2[0] ,"******\n"
        # print num
        # rows.setdefault(date,num)
        # print rows
        #if max1 < row1[0]:
        #    max1 = row1[0]
        #if max2 < row2[0]:
        #    max2 = row2[0]
        
    """"print rows
    for key, value in rows.items():
        print value["weibo"], value["news"]
        if (max1 == 0):
            num1 = 0
        else:
            num1 = 0.3 * value["weibo"] / max1
        if (max2 == 0):
            num2 = 0
        else:
            num2 = 0.7 * value["news"] / max2
        result[key] = 100*(num1 + num2)"""""
    cur.close()
    conn.close()
    return result

def getIndex(request):
    result={}
    result=PublicIndex()
    return HttpResponse(json.dumps(result))

def getSecurityIndex(request):
    year = thisyear
    month = thismonth
    day = thisday
    publicindex=PublicIndex()
    vulindex=VulIndex()
    threatenindex=ThreatenIndex()
    result={}
    for i in range(0,100):
        if month < 10:
            theMonth = "0" + str(month)
        else:
            theMonth = str(month)
        if (day < 10):
            theDay = "0" + str(day)
        else:
            theDay = str(day)
        date = str(year) + theMonth + theDay
        result[date]=(publicindex[date]+vulindex[date]+threatenindex[date])/3
        newdate = getDate(year, month, day)
        year = newdate["year"]
        month = newdate["month"]
        day = newdate["day"]
    return HttpResponse(json.dumps(result))

def getConpots(request):
    conn, cur = createConnect()
    result=[]
    cur.execute("select * from conpot_log_1 ORDER BY time DESC")
    results = cur.fetchall()
    for row in results:
        news = {}
        news["date"]=str(row[0])
        news["time"]=str(row[1])
        news["function_id"]=row[2]
        news["protocol"]=row[3]
        news["request"]=row[4]
        news["destiIP"]=row[5]
        news["sourcePort"]=row[6]
        news["DestiPort"]=row[7]
        news["slaveID"]=row[8]
        news["sourceIP"]=row[9]
        news["response"]=row[10]
        news["country"]=row[11]
        news["subdivision"]=row[12]
        news["city"]=row[13]
        news["coordinate"]=row[14]
        result.append(news)
    cur.close()
    conn.close()
    return HttpResponse(json.dumps(result))

global a
a=7641
def getStatistics(request):
    result={}
    conn, cur = createConnect()
    global a
    num=random.randint(1, 50)
    a+=num
    result["attack"]=a
    cur.execute("select count(*) from weibo")
    row = cur.fetchone()
    result["public"]=row[0]
    cur.execute("select count(*) from news")
    row = cur.fetchone()
    result["public"] += row[0]
    result["vul"]=0
    result["device"]=0
    list = vulnerability.objects.values()
    for vulner in list:
        result["vul"]+=1
    list = instance.objects.values()
    for dev in list:
        result["device"] += 1
    cur.close()
    conn.close()
    return HttpResponse(json.dumps(result))






