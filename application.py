# -*- coding: utf-8 -*-
import cv2
import json
import operator
import re
import math
import http.client, urllib.request, urllib.parse, urllib.error, base64
from flask import Flask, render_template, request
from werkzeug import secure_filename
from difflib import SequenceMatcher
app = Flask(__name__)

@app.route("/")
def hello():
    return "Hello World!"

@app.route("/upload")
def render_file():
    return render_template('upload.html')

@app.route('/fileUpload', methods = ['GET', 'POST'])
def upload_file():
    if request.method == 'POST':
        f = request.files['file']
        f.save(secure_filename(f.filename))

        imgResize(f.filename)

        # MS ocr api 호출
        ocrData = get_Ocr_Info("/home/taihoinst/icrRest/" + f.filename)

        print(str(ocrData))

        # Y축정렬
        ocrData = sortArrLocation(ocrData)

        docTopType, docType = findDocType(ocrData)

        ocrData = splitLabel(ocrData)

        ocrData = compareLabel(ocrData)

        labelData = findColByML(ocrData)

        entryData = findColByML(ocrData)

        ocrData = findEntry(ocrData)

        obj = {}
        obj["docCategory"] = {"DOCTYPE":docType, "DOCTOPTYPE": docTopType}
        obj["data"] = ocrData

        return str(obj)
    else:
        return "upload GET"

def get_Ocr_Info(filePath):
    headers = {
        # Request headers
        'Content-Type': 'application/octet-stream',
        'Ocp-Apim-Subscription-Key': 'c4af1927bf124533bcf2bcc92fd4c63d',
    }

    params = urllib.parse.urlencode({
        # Request parameters
        'language': 'unk',
        'detectOrientation ': 'true',
    })

    try:
        body = open(filePath, 'rb').read()

        conn = http.client.HTTPSConnection('japaneast.api.cognitive.microsoft.com')
        conn.request("POST", "/vision/v2.0/ocr?%s" % params, body, headers)
        response = conn.getresponse()
        data = response.read()
        data = json.loads(data)
        data = ocrParsing(data)
        conn.close()

        return data
    except Exception as e:
        print("[Errno {0}] {1}".format(e.errno, e.strerror))

def ocrParsing(body):
    data = []
    for i in body["regions"]:
        for j in i["lines"]:
            item = ""
            for k in j["words"]:
                item += k["text"] + " "
            data.append({"location":j["boundingBox"], "text":item[:-1]})
    return data

# y축 정렬
def sortArrLocation(inputArr):
    tempArr = []
    retArr = []
    for item in inputArr:
        tempArr.append((makeindex(item['location']), item))
    tempArr.sort(key=operator.itemgetter(0))
    for tempItem in tempArr:
        retArr.append(tempItem[1])
    return retArr

def makeindex(location):
    if len(location) > 0:
        temparr = location.split(",")
        for i in range(0, 5):
            if (len(temparr[0]) < 5):
                temparr[0] = '0' + temparr[0]
        return int(temparr[1] + temparr[0])
    else:
        return 999999999999

def similar(a, b):
    return SequenceMatcher(None, a, b).ratio()

def findDocType(ocrData):
    try:
        docTypType = 0
        docType = 0
        text = []
        maxNum = 0
        strText = ''

        file = open('docSentence.txt','r', encoding="UTF8")
        sentenceList = []

        for line in file:
            sentence,docType,docTopType = line.strip().split("||")
            dic = {}
            dic["sentence"] = sentence
            dic["docType"] = docType
            dic["docTopType"] = docTopType
            sentenceList.append(dic)
        file.close()

        regExp = "[\{\}\[\]\/?.,;:|\)*~`!^\-_+<>@\#$%&\\\=\(\'\"]"

        for i, item in enumerate(ocrData):
            text.append(re.sub(regExp, "", item["text"]))
            strText = ",".join(str(x) for x in text)
            if i == 20:
                break

        strText = strText.lower()

        for rows in sentenceList:
            ratio = similar(strText, rows["sentence"])

            if ratio > maxNum:
                maxNum = ratio
                doctype = rows["docType"]
                docTopType = rows["docTopType"]

        if maxNum > 0.1:
            return int(docTopType), int(docType)
        else:
            return docTopType, docType

    except Exception as ex:
        raise Exception(str({'code': 500, 'message': 'findDocType error',
                             'error': str(ex).replace("'", "").replace('"', '')}))

def splitLabel(ocrData):
    try:
        sepKeywordList = []

        # sep_keyword 파일 추출
        file = open("splitLabel.txt", "r", encoding="UTF8")
        for line in file:
            sepKeyword = line.strip()
            sepKeywordList.append(sepKeyword)

        for keyWord in sepKeywordList:
            for item in ocrData:
                if item["text"].replace(" ", "").find(keyWord) > -1:

                    item["text"] = item["text"].replace(" ", "")
                    textLen = len(item["text"])
                    location = item["location"].split(",")
                    value = math.ceil(int(location[2]) / textLen)

                    textList = splitText(item["text"], keyWord)
                    ocrData.remove(item)

                    findLen = 0

                    for idx, i in enumerate(textList):
                        dic = {}
                        dicLoc = ""

                        find = item["text"].find(i, findLen)
                        findLen += len(i)
                        width = int(value * find)

                        if idx == 0:
                            dicLoc = location[0] + "," + location[1] + "," + str(int(value * len(i))) + "," + location[3]
                        else:
                            dicLoc = str(int(location[0]) + width) + "," + location[1] + "," + str(
                                int(value * len(i))) + "," + location[3]

                        dic["location"] = dicLoc
                        dic["text"] = i
                        ocrData.append(dic)

        ocrData = sortArrLocation(ocrData)
        return ocrData

    except Exception as ex:
        raise Exception(str({'code':500, 'message':'splitLabel error', 'error':str(ex).replace("'","").replace('"','')}))

def splitText(text, split):
    result = []

    while True:
        find = text.find(split)

        if find == 0:
            result.append(text[0:len(split)])
            text = text[len(split):]
        elif find > 0:
            result.append(text[0:find])
            result.append(text[find:find + len(split)])
            text = text[find + len(split):]

        if find == -1:
            if len(text) > 0:
                result.append(text)
            break

    return result

def locationCheck(loc1, loc2, plus, minus):
    if minus < int(loc1) - int(loc2) < plus:
        return True
    else :
        return False

def bottomCheck(loc1, loc2, num):
   if int(loc1) - int(loc2) < num:
       return True
   else:
       return False

def compareLabel(inputArr):

    for item in inputArr:
        yData = []
        xData = []
        itemLoc = item["location"].split(",")

        yData.append(item["text"].replace(" ", ""))
        xData.append(item["text"].replace(" ", ""))

        for data in inputArr:
            dataLoc = data["location"].split(",")

            # 아래로 5개 문장 가져오기
            if item != data and bottomCheck(itemLoc[1], dataLoc[1], 2) and locationCheck(itemLoc[0], dataLoc[0], 10, -10) and len(yData) < 5:
                yData.append(data["text"].replace(" ", ""))

            # 오른쪽으로 5개 문장 가져오기
            if item != data and bottomCheck(itemLoc[0], dataLoc[0], 2) and locationCheck(itemLoc[1], dataLoc[1], 10, -10) and len(xData) < 5:
                xData.append(data["text"].replace(" ", ""))

        xText = ""
        yText = ""

        for x in xData:
            xText += x + " "

        for y in yData:
            yText += y + " "

        item["xData"] = xText[:-1]
        item["yData"] = yText[:-1]

    return inputArr

def findEntry(ocrData):

    return ocrData


def findColByML(ocrData):
    obj = [{'yData': 'aaa1', 'text': 'bbb1', 'xData': 'ccc1', 'location': 44},
           {'yData': 'aaa2', 'text': 'bbb2', 'xData': 'ccc2', 'location': 530},
           {'yData': 'aaa3', 'text': 'bbb3', 'xData': 'ccc3', 'location': 81},
           {'yData': 'aaa4', 'text': 'bbb4', 'xData': 'ccc4', 'location': 1234},
           {'yData': 'aaa5', 'text': 'bbb5', 'xData': 'ccc5', 'location': 1039}]

    resultObj = {}
    colName = ["xData", "yData", "text", "location"]
    dataArr = []
    for qq in obj:
        tmpArr = [qq.get('xData'),
                  qq.get('yData'),
                  qq.get('text'),
                  qq.get('location')
                  ]
        dataArr.append(tmpArr)

    resultObj['ColumnNames'] = colName;
    resultObj['Values'] = dataArr;

    data = {
        "Inputs": {
            "input1": resultObj,
        },
        "GlobalParameters": {
        }
    }

    body = str.encode(json.dumps(data))
    api_key = 'Glka58B/GkaysKmq01K/1S7zIhiuAPo1k9l1wq/8Z6NjrQGTMJs4cbMXiV0a2Lr5eVggch1aIDQjUDKaCLpYEA=='
    headers = {'Content-Type': 'application/json', 'Authorization': ('Bearer ' + api_key)}
    url = 'https://ussouthcentral.services.azureml.net/workspaces/a2de641a3e3a40d7b85125db08cf4a97/services/9ca98ef979444df8b1fcbecc329c46bd/execute?api-version=2.0&details=true'

    req = urllib.request.Request(url, body, headers)

    try:
        response = urllib.request.urlopen(req)

        result = response.read()
        # print(json.dumps(result.decode("utf8", 'ignore')))
        return json.dumps(result.decode("utf8", 'ignore'))
    except urllib.error.HTTPError as error:
        # print("The request failed with status code: " + str(error.code))

        # Print the headers - they include the requert ID and the timestamp, which are useful for debugging the failure
        # print(error.info())
        # print(json.loads(error.read().decode("utf8", 'ignore')))
        return json.loads(error.read().decode("utf8", 'ignore'))

def imgResize(filename):
    try:
        FIX_LONG = 3600
        FIX_SHORT = 2400

        img = cv2.imread(filename)
        height, width = img.shape[:2]
        imagetype = "hori"

        magnify = 1
        if width - height > 0:
            iimagetype = "hori"
            if (width / height) > (FIX_LONG / FIX_SHORT):
                magnify = round((FIX_LONG / width) - 0.005, 2)
            else:
                magnify = round((FIX_SHORT / height) - 0.005, 2)
        else:
            imagetype = "vert"
            if (height / width) > (FIX_LONG / FIX_SHORT):
                magnify = round((FIX_LONG / height) - 0.005, 2)
            else:
                magnify = round((FIX_SHORT / width) - 0.005, 2)

        img = cv2.resize(img, dsize=(0, 0), fx=magnify, fy=magnify, interpolation=cv2.INTER_LINEAR)
        height, width = img.shape[:2]

        if imagetype == "hori":
            img = cv2.copyMakeBorder(img, 0, FIX_SHORT - height, 0, FIX_LONG - width, cv2.BORDER_CONSTANT,
                                     value=[255, 255, 255])
        else:
            img = cv2.copyMakeBorder(img, 0, FIX_LONG - height, 0, FIX_SHORT - width, cv2.BORDER_CONSTANT,
                                     value=[255, 255, 255])

    except Exception as ex:
        raise Exception(
            str({'code': 500, 'message': 'imgResize error', 'error': str(ex).replace("'", "").replace('"', '')}))

if __name__=='__main__':
    app.run(host='0.0.0.0',port=5000,debug=True)
