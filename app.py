# -*- coding: utf-8 -*-
import os
import base64
# from datetime import datetime, timedelta
from datetime import datetime
from datetime import timedelta
import cv2
import json
import operator
import re
import math
import http.client, urllib.request, urllib.parse, urllib.error, base64
from flask import Flask, render_template, request, send_file
from werkzeug import secure_filename
from difflib import SequenceMatcher
from pdf2image import convert_from_path, convert_from_bytes
import ftplib

import linedel as lineDel
# mask 생성 후 GRID 제거
# import lineDelTest as lineDel

app = Flask(__name__)
ftpIp = '104.41.171.244' # FTP 서버 IP
ftpPort = 21 # FTP 서버 PORT
ftpId = 'daerimicr' # FTP 서버 접속 ID
ftpPw = 'daerimicr123!@#' # FTP 서버 접속 PASSWORD
receiveFtpPath = "/uploads" # FTP에서 파일을 받을 경로
#pyFilePath = '/home/daerimicr/icrRest/uploads/' # python 서버 파일 경로
pyFilePath = '/Users/Taiho/Desktop/icrRest/uploads/' # python 서버 파일 경로

# encode
def stringToBase64(s):
    return base64.b64encode(s.encode('utf-8'))

# decode
def base64ToString(b):
    return base64.b64decode(b).decode('utf-8')

@app.route("/")
def hello():
    return "Hello World!"

@app.route("/upload")
def render_file():
    return render_template('upload.html')

@app.route('/fileUpload', methods = ['GET', 'POST'])
def upload_file():
    if request.method == 'POST':
        upload_path = pyFilePath
        fileNames = []
        retResult = []
        obj = {}
        convertFilename = ''
        ext = ''

        if len(request.files) != 0 :
            f = request.files['file']
            ext = os.path.splitext(f.filename)[1]
            convertFilename = f.filename

             #f.save(secure_filename(convertFilename))
            f.save(os.path.join(upload_path, convertFilename))
            uploadFtpFile(upload_path, convertFilename)
        else:
            convertFilename = request.form['filename']
            downloadFtpFile(upload_path, convertFilename)
            ext = os.path.splitext(convertFilename)[1]

        if ext == ".pdf":
            fileNames = convertPdfToImage(upload_path, convertFilename)
            for item in fileNames:
                imgResize(upload_path + item)
                # lineDeleteAndNoiseDelete
                lineDel.main(stringToBase64(upload_path + item))
                obj = pyOcr(upload_path + item, convertFilename)
                retResult.append(obj)
        else:
            fileNames = imgResize(upload_path + convertFilename)
            for item in fileNames:
                # lineDeleteAndNoiseDelete
                lineDel.main(stringToBase64(upload_path + item))
                obj = pyOcr(item, convertFilename)
            retResult.append(obj)

        for item in fileNames:
            uploadFtpFile(upload_path, item)
            os.remove(upload_path + item);
        os.remove(upload_path + convertFilename);

        result = re.sub('None', "null", json.dumps(retResult, ensure_ascii=False))
        return str(result)
    else:
        return "upload GET"

#@app.route("/fileDown", methods = ['GET', 'POST'])
#def download_file():
#    upload_path = '/home/daerimicr/icrRest/uploads/'
#    fileName = request.args.get('fileName')
#    
#    with open((upload_path + fileName), 'rb') as single_img:
#        img_b64 = base64.b64encode(single_img.read())
#    return img_b64

@app.route("/insertDocSentence", methods = ['GET','POST'])
def insertDocSentence():
    if request.method == 'POST':
        str = request.form['sentence']
        print(str)
        file = open('docSentence.txt', 'a', -1, encoding='UTF8')
        file.write('\n')
        file.write(str)
        file.close()

        return "success"
    else:
        return render_template('insertDocSentence.html')

@app.route("/insertSplitData", methods = ['GET','POST'])
def insertSplitData():
    if request.method == 'POST':
        data = request.get_json()
        sentence = data['sentence']
        sentence = json.loads(sentence)

        file = open('splitLabel.txt', 'a', -1, encoding='UTF8')
        for item in sentence:
            # file.write(item + "\n")
            file.write("\n" + item)
        file.close()

        return "success"

# imageMagick_lineDelete
# imageMagick 경로 확인!!!
# def lineDelete(path):
#     try:
#         cmd = 'C:\\Users\\user\\source\\repos\\ICR-DAERIM\\module\\imageMagick\\convert.exe ' + path + ' -type Grayscale -negate -define morphology:compose=darken -morphology Thinning ''Rectangle:1x60+0+0<'' -negate ' + path
#         cmd = 'convert ' + path + ' -type Grayscale -negate -define morphology:compose=darken -morphology Thinning ''Rectangle:1x40+0+0<'' -negate ' + path
#         cmd_args = cmd.split()
#         call(cmd_args)
#         return True
        
#     except Exception as ex:
#         raise Exception(str({'code': 500, 'message': 'lineDelete error',
#                              'error': str(ex).replace("'", "").replace('"', '')}))

def pyOcr(item, convertFilename):
    # MS ocr api 호출
    ocrData = get_Ocr_Info(item)

    # Y축정렬
    ocrData = sortArrLocation(ocrData)

    # 레이블 분리 모듈 - 임교진
    ocrData = splitLabel(ocrData)

    # doctype 추출 similarity - 임교진
    docTopType, docType, maxNum = findDocType(ocrData)

    # Y축 데이터 X축 데이터 추출
    ocrData = compareLabel(ocrData)

    # label 추출 MS ML 호출
    labelData = findColByML(ocrData)
    # entry 추출
    entryData = findColByML(ocrData)

    # entry 추출
    ocrData = findEntry(ocrData)

    obj = {}
    obj["convertFileName"] = item[item.rfind("/")+1:]
    obj["originFileName"] = convertFilename
    obj["docCategory"] = {"DOCTYPE": docType, "DOCTOPTYPE": docTopType, "DOCSCORE": maxNum}
    obj["data"] = ocrData

    return obj

# pdf 에서 png 변환 함수
def convertPdfToImage(upload_path, pdf_file):

    try:
        pages = convert_from_path(upload_path + pdf_file, dpi=300, output_folder=None, first_page=None,
                                  last_page=None,
                                  fmt='ppm', thread_count=1, userpw=None, use_cropbox=False, strict=False,
                                  transparent=False)
        pdf_file = pdf_file[:-4]  # 업로드 파일명
        filenames = []
        for page in pages:
            filename = "%s-%d.jpg" % (pdf_file, pages.index(page))
            print('filename===>' + filename)
            page.save(upload_path + filename, "JPEG")
            filenames.append(filename)
        return filenames
    except Exception as e:
        print(e)

def imgResize(filename):
    try:
        # FIX_LONG = 3600
        # FIX_SHORT = 2400

        FIX_LONG = 2970
        FIX_SHORT = 2100
        filenames = []

        imgs = cv2.imreadmulti(filename)[1]
        index = 0

        for i in range(0,len(imgs)):

            img = imgs[i]
            height, width = img.shape[:2]
            imagetype = "hori"
            # 배율
            magnify = 1
            if width - height > 0:
                imagetype = "hori"
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

            # 확대, 축소
            img = cv2.resize(img, dsize=(0, 0), fx=magnify, fy=magnify, interpolation=cv2.INTER_LINEAR)
            height, width = img.shape[:2]
            # 여백 생성
            if imagetype == "hori":
                img = cv2.copyMakeBorder(img, 0, FIX_SHORT - height, 0, FIX_LONG - width, cv2.BORDER_CONSTANT,
                                         value=[255, 255, 255])
            else:
                img = cv2.copyMakeBorder(img, 0, FIX_LONG - height, 0, FIX_SHORT - width, cv2.BORDER_CONSTANT,
                                         value=[255, 255, 255])

            ext = findExt(filename)

            if ext.lower() == '.tif':
                name = filename[:filename.rfind(".")]
                name = "%s-%d.jpg" % (name, index)
                cv2.imwrite(name, img)
                filenames.append(name)
                index = index + 1
            else:
                cv2.imwrite(filename, img)
                filenames.append(filename)

        return filenames

    except Exception as ex:
        raise Exception(
            str({'code': 500, 'message': 'imgResize error', 'error': str(ex).replace("'", "").replace('"', '')}))

def findExt(fileName):
    ext = fileName[fileName.rfind("."):]
    return ext

def get_Ocr_Info(filePath):
    headers = {
        # Request headers
        'Content-Type': 'application/octet-stream',
        'Ocp-Apim-Subscription-Key': '8dbe688c24a04c3992825e1a68644b82',
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
            data.append({"location":j["boundingBox"], "text":item[:-1],"originText":item[:-1]})
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
        docTopType = 0
        docType = 0
        text = []
        maxNum = 0
        strText = ''

        file = open('docSentence.txt','r', encoding="UTF8")
        sentenceList = []

        for line in file:
            sentence,type,topType = line.strip().split("||")
            dic = {}
            dic["sentence"] = sentence
            dic["docType"] = type
            dic["docTopType"] = topType
            sentenceList.append(dic)
        file.close()

        regExp = "[\{\}\[\]\/?.,;:|\)*~`!^\-_+<>@\#$%&\\\=\(\'\"]"

        for i, item in enumerate(ocrData):
            text.append(re.sub(regExp, "", item["text"]))
            strText = ",".join(str(x) for x in text)
            if i == 19:
                break

        strText = strText.lower()

        for rows in sentenceList:
            ratio = similar(strText, rows["sentence"])

            if ratio > maxNum:
                maxNum = ratio
                docType = rows["docType"]
                docTopType = rows["docTopType"]

        if maxNum > 0.1:
            return int(docTopType), int(docType), maxNum
        else:
            return docTopType, docType, maxNum

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
                        dic["originText"] = i
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


def downloadFtpFile(upload_path, filename):
    ftp = ftplib.FTP()
    ftp.connect(ftpIp, ftpPort)
    ftp.login(ftpId, ftpPw)
    ftp.cwd(receiveFtpPath)   #파일 전송할 Ftp 주소 (받을 주소)
    os.chdir(upload_path) #파일 전송 대상의 주소(보내는 주소)
    ftp.retrbinary("RETR " + filename ,open(filename, 'wb').write)
    
    ftp.close() 
    os.chdir("/Users/Taiho/Desktop/icrRest/")

def uploadFtpFile(upload_path, filename):
    ftp = ftplib.FTP()
    ftp.connect(ftpIp, ftpPort)
    ftp.login(ftpId, ftpPw)
    ftp.cwd(receiveFtpPath)
    os.chdir(upload_path)
    myfile = open(filename, 'rb')
    ftp.storbinary('STOR ' + filename, myfile)
    
    myfile.close()
    ftp.close() 
    os.chdir("/Users/Taiho/Desktop/icrRest/")
if __name__=='__main__':
    app.run(host='0.0.0.0',port=5000,debug=True)
