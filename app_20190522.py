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
from PIL import Image
import io
from google.cloud import vision

import linedel as lineDel
# mask 생성 후 GRID 제거
# import lineDelTest as lineDel
# line 확인 후 crop 하기
import lineDetection as lineDect

app = Flask(__name__)
ftpIp = '104.41.171.244' # FTP 서버 IP
ftpPort = 21 # FTP 서버 PORT
ftpId = 'daerimicr' # FTP 서버 접속 ID
ftpPw = 'daerimicr123!@#' # FTP 서버 접속 PASSWORD
receiveFtpPath = "/uploads" # FTP에서 파일을 받을 경로
pyFilePath = '/home/daerimicr/icrRest/uploads/' # python 서버 파일 경로
osChdir = '/home/daerimicr/icrRest/'
#pyFilePath = '/Users/Taiho/Desktop/icrRest/uploads/' # python 서버 파일 경로
#osChdir = '/Users/Taiho/Desktop/icrRest/'
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
            print(upload_path)
            print(convertFilename)
            downloadFtpFile(upload_path, convertFilename)
            ext = os.path.splitext(convertFilename)[1]

        if ext == ".pdf":
            fileNames = convertPdfToImage(upload_path, convertFilename)
            print(fileNames)
            for item in fileNames:
                # imgResize(upload_path + item)
                # lineDetectionAndCrop
                # x, y, w, h = lineDect.main(stringToBase64(upload_path + "chg_" + item))
                # lineDeleteAndNoiseDelete
                # lineDel.main(stringToBase64(upload_path + "chg_" + item))
                lineDect.main(stringToBase64(upload_path + item))
                imgResize(upload_path + item)
                obj = pyOcr(upload_path + item, convertFilename)
                retResult.append(obj)
        else:
            fileNames = imgResize(upload_path + convertFilename)
            for item in fileNames:
                # lineDetectionAndCrop
                x, y, w, h= lineDect.main(stringToBase64(upload_path + "chg_" + item))
                # lineDeleteAndNoiseDelete
                lineDel.main(stringToBase64(upload_path + "chg_" + item))
                obj = pyOcr(upload_path + "chg_" + item, convertFilename, x, y, w, h)
            retResult.append(obj)

        for item in fileNames:
            uploadFtpFile(upload_path, item)
            # uploadFtpFile(upload_path, "chg_" + item)
            os.remove(upload_path + item)
            # os.remove(upload_path + "chg_" + item)
        os.remove(upload_path + convertFilename)

        result = re.sub('None', "null", json.dumps(retResult, ensure_ascii=False))
        return str(result)
    else:
        return "upload GET"

@app.route('/fileUploadGoogle', methods = ['GET', 'POST'])
def upload_file_google():
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
            print(upload_path)
            print(convertFilename)
            downloadFtpFile(upload_path, convertFilename)
            ext = os.path.splitext(convertFilename)[1]

        if ext == ".pdf":
            fileNames = convertPdfToImage(upload_path, convertFilename)
            print(fileNames)
            for item in fileNames:
                # imgResize(upload_path + item)
                # lineDetectionAndCrop
                # x, y, w, h = lineDect.main(stringToBase64(upload_path + "chg_" + item))
                # lineDeleteAndNoiseDelete
                # lineDel.main(stringToBase64(upload_path + "chg_" + item))
                lineDect.main(stringToBase64(upload_path + item))
                imgResize(upload_path + item)
                obj = pyOcr_google(upload_path + item, convertFilename)
                retResult.append(obj)
        else:
            fileNames = imgResize(upload_path + convertFilename)
            for item in fileNames:
                # lineDetectionAndCrop
                x, y, w, h= lineDect.main(stringToBase64(upload_path + "chg_" + item))
                # lineDeleteAndNoiseDelete
                lineDel.main(stringToBase64(upload_path + "chg_" + item))
                obj = pyOcr_google(upload_path + "chg_" + item, convertFilename, x, y, w, h)
            retResult.append(obj)

        for item in fileNames:
            uploadFtpFile(upload_path, item)
            # uploadFtpFile(upload_path, "chg_" + item)
            os.remove(upload_path + item)
            # os.remove(upload_path + "chg_" + item)
        os.remove(upload_path + convertFilename)

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
        file.write('\n'+str)
        #file.write(str)
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
            #file.write('\n')
            #file.write(item)
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
    # print(ocrData)

    # doctype 추출 similarity - 임교진
    docTopType, docType, maxNum = findDocType(ocrData)

    # 업체명,사업자번호,주소,전화 입력 
    ocrData = companyInfoInsert(ocrData, docTopType, docType)

    # Y축 데이터 X축 데이터 추출
    ocrData = compareLabel(ocrData)

    # label 추출 MS ML 호출
    labelData = findColByML(ocrData)
    # entry 추출
    entryData = findColByML(ocrData)

    # entry 추출
    ocrData = findEntry(ocrData)

    # label mapping
    #ocrData = evaluateLabelMulti(ocrData)

    # entry mapping
    #ocrData = evaluateEntry(ocrData)

    obj = {}
    # obj["convertFileName"] = item[item.rfind("/")+1:].replace("chg_", "")
    obj["convertFileName"] = item[item.rfind("/") + 1:]
    obj["originFileName"] = convertFilename
    obj["docCategory"] = {"DOCTYPE": docType, "DOCTOPTYPE": docTopType, "DOCSCORE": maxNum}
    # obj["x-axis"] = x
    # obj["y-axis"] = y
    # obj["width"] = w
    # obj["height"] = h
    obj["data"] = ocrData

    return obj

def pyOcr_google(item, convertFilename):
    ocrData = getOcrInfo(item)

    # Y축정렬
    ocrData = sortArrLocation(ocrData)
    # 오타 수정
    ocrData = updateTypo(ocrData)
    
    # 레이블 분리 모듈 - 임교진
    ocrData = splitLabel(ocrData)
    
    # doctype 추출 similarity - 임교진
    docTopType, docType, maxNum = findDocType(ocrData)
    # docTopType, docType, maxNum = 50, 70, 0.40236686390532544


    print(docTopType, docType)

    # 업체명,사업자번호,주소,전화 입력 
    ocrData = companyInfoInsert(ocrData, docTopType, docType)


    # Y축 데이터 X축 데이터 추출
    # ocrData = compareLabel(ocrData)
    # ocrData = extractCNNData(ocrData)
    
    # label 추출 MS ML 호출
    # labelData = findColByML(ocrData)
    # entry 추출
    # entryData = findColByML(ocrData)

    # label mapping
    #ocrData = evaluateLabelMulti(ocrData)

    # entry mapping
    #ocrData = evaluateEntry(ocrData)

    # findLabel CNN
    # ocrData = labelEval.startEval(ocrData)

    # findEntry CNN
    # ocrData = entryEval.startEval(ocrData)

    obj = {}
    obj["convertFileName"] = item[item.rfind("/") + 1:]
    obj["originFileName"] = convertFilename
    obj["docCategory"] = {"DOCTYPE": docType, "DOCTOPTYPE": docTopType, "DOCSCORE": maxNum}
    obj["data"] = ocrData

    #print("-------------result---------------")
    #for item in obj["data"]:
    #    print(item)

    return obj

def updateTypo(ocrData):
    try:
        typoDatas = []
        f = open('typoData.txt', 'r', encoding='utf-8')
        lines = f.readlines()

        for line in lines:
            data = line.split('||')
            data[1] = data[1][:-1]
            typoDatas.append(data)

        for data in ocrData:
            text = data['text'].replace(' ','')

            for typoData in typoDatas:
                if text.replace(' ','').find(typoData[0]) > -1:
                    data['text'] = data['text'].replace(typoData[0], typoData[1])

        return ocrData
    except Exception as e:
        print(e)

def getOcrInfo(item):
    ocrData = []
    client = vision.ImageAnnotatorClient()

    with io.open(item, 'rb') as image_file:
        content = image_file.read()

    image = vision.types.Image(content=content)

    response = client.document_text_detection(image=image)

    for page in response.full_text_annotation.pages:
        for block in page.blocks:
            # print('\nBlock confidence: {}\n'.format(block.confidence))

            for paragraph in block.paragraphs:
                # print('Paragraph confidence: {}'.format(paragraph.confidence))

                for word in paragraph.words:
                    word_text = ''.join([
                        symbol.text for symbol in word.symbols
                    ])

                    x = word.bounding_box.vertices[0].x
                    y = word.bounding_box.vertices[0].y

                    width = int(word.bounding_box.vertices[1].x) - int(word.bounding_box.vertices[0].x)
                    height = int(word.bounding_box.vertices[3].y) - int(word.bounding_box.vertices[0].y)

                    location = str(x) + ',' + str(y) + ',' + str(width) + ',' + str(height)
                    if x > 0 and y > 0:
                        ocrData.append({"location": location, "text":word_text})

                    # print('Word text: {}, location:{},{},{},{}'.format(word_text, x, y, width, height))
                    # print('Word text: {}, location:{}'.format(word_text, word.bounding_box.vertices))

    #print('--------------------origin---------------------')
    #for data in ocrData:
    #    print(data)

    # y축 다음 x축 기준으로 소팅
    ocrData = sortLocX(sortLocY(ocrData))

    # text에 관한 전처리
    ocrPreProcessData = []
    idx = 0
    # 임시
    labelTexts = ["사업자번호", "납품장소", "운반차번호", "출발", "납품용적", "누계", "콘크리트의종류에", "따른구분", "굵은골재의최대"
        , "치수에따른구분", "호칭강도", "슬럼프또는", "슬럼프플로", "시멘트종류에"]
    originX, originY = 0, 0

    while idx < len(ocrData):
        # text가 "|" 일 경우 text를 삭제한다
        if ocrData[idx]["text"] == '|':
            del ocrData[idx]
            idx -= 1
        else:
            # 같은 라인에 거리가 가까운 text는 합친다
            isCombiend, combineData = distanceParams(ocrData[idx], mostCloseWordSameLine(ocrData[idx], extractSameLine(ocrData[idx], ocrData, 3)))         
            if combineData:
                if isCombiend < 21:
                    ocrData, idx = combiendText(ocrData, combineData, idx, originX, originY)

                # 같은 줄에 다음 text와 합쳐서 레이블의 부분일 경우 합친다
                ocrData, idx = combiendLabelText(ocrData, combineData, labelTexts, idx, originX, originY)

                # 같은 줄에 다음 text가 숫자 다음 '시' 숫자 '분'  경우 합친다.
                ocrData, idx = combiendTimeText(ocrData, combineData, idx,  originX, originY)
        idx += 1

    ocrPreProcessData = ocrData

    #print('--------------------ocrPreProcessData---------------------')
    #for data in ocrPreProcessData:
    #    print(data)
    return ocrPreProcessData

# ocr 데이터 위치 정렬 (y축 and x축)
def sortLocY(data):
    try:
        if len(data) > 1:
            target = int(data[len(data) - 1]["location"].split(',')[1])
            left, mid, right = [], [], []

            for i in range(len(data)-1):
                loc = int(data[i]["location"].split(',')[1])
                if loc < target:
                    left.append(data[i])
                elif loc > target:
                    right.append(data[i])
                else:
                    mid.append(data[i])
            mid.append(data[len(data) - 1])

            return sortLocY(left) + mid + sortLocY(right)
        else:
            return data

    except Exception as e:
        raise Exception(str(
            {'code': 500, 'message': 'sortLocY fail', 'error': str(e).replace("'", "").replace('"', '')}))

def sortLocX(data):
    try:
        for i in range(len(data)):
           for j in range(len(data)):
               iLoc = data[i]["location"].split(',')
               jLoc = data[j]["location"].split(',')
               if int(iLoc[1]) == int(jLoc[1]) and int(iLoc[0]) < int(jLoc[0]):
                   temp = data[i]
                   data[i] = data[j]
                   data[j] = temp

        return data

    except Exception as e:
        raise Exception(str(
            {'code': 500, 'message': 'sortLocX fail', 'error': str(e).replace("'", "").replace('"', '')}))

#temparr에서 tempdict와 같은 라인에 있는 원소를 찾는다
def extractSameLine(tempdict, temparr, yInterval):
    try:
        dictArr = []
        tempdictLoc = tempdict["location"].split(',')

        for temp in temparr:
            if temp["text"] != "" and tempdict["location"] != temp["location"] and int(tempdictLoc[1]) >= int(temp["location"].split(',')[1]) - yInterval and int(tempdictLoc[1]) <= int(temp["location"].split(',')[1]) + yInterval:
                dictArr.append(temp)

        return dictArr

    except Exception as e:
        raise Exception(str(
            {'code': 500, 'message': 'extractSameLine fail', 'error': str(e).replace("'", "").replace('"', '')}))

#temparr에서 tempdict와 가장 가까운 원소를 찾는다
def mostCloseWordSameLine(tempdict, temparr):
    try:
        retDict = {}
        tempdictLoc = tempdict["location"].split(',')
        min = 3000
        if len(temparr) != 0:
            for temp in temparr:
                tempLoc = temp["location"].split(',')
                dx = abs(int(tempdictLoc[0]) + int(tempdictLoc[2]) - int(tempLoc[0]))
                dy = abs(int(tempdictLoc[1]) - int(tempLoc[1]))
                dist = math.sqrt( math.pow(dx, 2) + math.pow(dy, 2) )
                if dist < min:
                    min = dist;
                    retDict = temp

        return retDict

    except Exception as e:
        raise Exception(str(
            {'code': 500, 'message': 'mostCloseWordSameLine fail', 'error': str(e).replace("'", "").replace('"', '')}))

#tempdict와 comparedict의 거리를 구한다
def distanceParams(tempdict, comparedict):
    try:
        tempdictLoc = tempdict["location"].split(',')
        comparedictLoc = []
        if comparedict != {} :
            comparedictLoc =  comparedict["location"].split(',')
            dx = abs(int(tempdictLoc[0]) + int(tempdictLoc[2]) - int(comparedictLoc[0]))
            dy = abs(int(tempdictLoc[1]) - int(comparedictLoc[1]))
            retInt = math.sqrt( math.pow(dx, 2) + math.pow(dy, 2) )
        else:
            retInt = 5000

        return retInt, comparedict

    except Exception as e:
        raise Exception(str(
            {'code': 500, 'message': 'distanceParams fail', 'error': str(e).replace("'", "").replace('"', '')}))

# 좌표 및 텍스트 합친다
def combiendText(ocrData, combiendData, idx, originX, originY):
    try:
        result = {}
        ocrItem = ocrData[idx]
        ocrItemLoc = ocrItem["location"].split(',')
        combiendDataLoc = combiendData["location"].split(',')
        location = ""
        text = ""

        if int(ocrItemLoc[0]) < int(combiendDataLoc[0]):
            location = str(int(ocrItemLoc[0]) - int(originX)) + "," + str(int(ocrItemLoc[1]) - int(originY)) + ","
            location += str(int(combiendDataLoc[0]) - int(ocrItemLoc[0]) + int(combiendDataLoc[2])) + ","
            text = ocrItem["text"] + combiendData["text"]
        else:
            location = str(int(combiendDataLoc[0]) - int(originX)) + "," + str(int(combiendDataLoc[1]) - int(originY)) + ","
            location += str(int(ocrItemLoc[0]) - int(combiendDataLoc[0]) + int(ocrItemLoc[2])) + ","
            text = combiendData["text"] + ocrItem["text"]
        if int(ocrItemLoc[3]) < int(combiendDataLoc[3]):
            location += combiendDataLoc[3]
        else:
            location += ocrItemLoc[3]

        ocrData[idx]["location"] = location
        ocrData[idx]["text"] = text

        # 합쳐진 row 제거
        for i in range(len(ocrData)):
            if combiendData["location"] == ocrData[i]["location"] and combiendData["text"] == ocrData[i]["text"]:
                del ocrData[i]
                idx -= 1
                break

        return ocrData, idx

    except Exception as e:
        raise Exception(str(
            {'code': 500, 'message': 'combiendText fail', 'error': str(e).replace("'", "").replace('"', '')}))

# 같은 줄에 현재 text와 다음 텍스트가 레이블 문자에 포함하면 합친다.
def combiendLabelText(ocrData, combineData, labelTexts, idx, originX, originY):
    try:
        targetLabelTexts = []

        compareText = (ocrData[idx]["text"] + combineData["text"]).replace(" ", "")
        for i in range(len(labelTexts)):
            if labelTexts[i].find(compareText) != -1:
                targetLabelTexts.append(labelTexts[i])

            if len(targetLabelTexts) != 0:
                compareText = (ocrData[idx]["text"] + combineData["text"]).replace(" ", "")
                j = 0
                while j < len(targetLabelTexts):
                    if targetLabelTexts[j].find(compareText) != -1:
                        ocrData, idx = combiendText(ocrData, combineData, idx, originX, originY)
                    else:
                        del targetLabelTexts[j]
                        j -= 1
                    j += 1

        return ocrData, idx

    except Exception as e:
        raise Exception(str(
            {'code': 500, 'message': 'combiendLabelText fail', 'error': str(e).replace("'", "").replace('"', '')}))

# 같은 줄에 현재 text가 숫자 다음 '시' 숫자 '분' 경우 합친다.
def combiendTimeText(ocrData, combineData, idx, originX, originY):
    try:
        caseOne = regMatch('\d{1,2}시{1}', ocrData[idx]["text"].replace(" ", "")) and regMatch('\d{1,2}분{1}', combineData["text"].replace(" ", ""))
        caseTwo = regMatch('\d{1,2}', ocrData[idx]["text"].replace(" ", "")) and regMatch('시', combineData["text"].replace(" ", ""))
        caseThree = regMatch('\d{1,2}시', ocrData[idx]["text"].replace(" ", "")) and regMatch('\d{1,2}', combineData["text"].replace(" ", ""))
        casFour = regMatch('\d{1,2}시\d{1,2}', ocrData[idx]["text"].replace(" ", "")) and regMatch('분', combineData["text"].replace(" ", ""))

        if caseOne or caseTwo or caseThree or casFour:
            ocrData, idx = combiendText(ocrData, combineData, idx, originX, originY)

        return ocrData, idx

    except Exception as e:
        raise Exception(str(
            {'code': 500, 'message': 'combiendTimeText fail', 'error': str(e).replace("'", "").replace('"', '')}))

def regMatch(reg, text):
    try:
        return re.compile(reg).match(text)

    except Exception as e:
        raise Exception(str(
            {'code': 500, 'message': 'regMatch fail', 'error': str(e).replace("'", "").replace('"', '')}))


def evaluateEntry(ocrData):
    try:

        labelDatas = []
        ocrDataX = sortArrLocationX(ocrData)
        trainData = '/home/daerimicr/icrRest/labelTrain/data/invoice.train'
        f = open(trainData, 'r', encoding='utf-8')
        lines = f.readlines()

        for line in lines:
            data = line.split('||')
            data[3] = data[3][:-1]
            labelDatas.append(data)

        for colData in ocrData:
            if 'colLbl' in colData and int(colData['colLbl']) > 0:
                colLoc = colData['location'].split(',')

                # single multi check
                entryCheck = 'single'
                for labelData in labelDatas:
                    if colData['colLbl'] == labelData[1]:
                        entryCheck = labelData[2]

                if entryCheck == 'single':
                    singleExit = False

                    # entryCheck
                    for entryData in ocrDataX:
                        entryLoc = entryData['location'].split(',')

                        # 수평 check and colLbl 보다 오른쪽 check
                        if locationCheck(colLoc[1], entryLoc[1], 20, -20) and locationCheck(colLoc[0], entryLoc[0], 10, -1000):
                            if 'entryLbl' not in entryData and 'colLbl' not in entryData:
                                entryData['entryLbl'] = colData['colLbl']
                                singleExit = True
                                break

                    if singleExit == True:
                        continue

                    for entryData in ocrDataX:
                        entryLoc = entryData['location'].split(',')

                        # 수직 check and colLbl 보다 아래 check
                        if verticalCheck(colLoc, entryLoc, 50, -50) and locationCheck(colLoc[1], entryLoc[1], 15, -400):
                            if 'entryLbl' not in entryData and 'colLbl' not in entryData:
                                entryData['entryLbl'] = colData['colLbl']
                                break

                elif entryCheck == 'multi':
                    for entryData in ocrData:
                        entryLoc = entryData['location'].split(',')

                        if verticalCheck(colLoc, entryLoc, 20, -20) and locationCheck(colLoc[1], entryLoc[1], 15, -2000):
                            if 'entryLbl' not in entryData and 'colLbl' not in entryData:
                                entryData['entryLbl'] = colData['colLbl']


        return ocrData
    except Exception as e:
        print(e)


def evaluateLabelMulti(ocrData):
    try:
        labelDatas = []
        delDatas = []
        ocrDataX = sortArrLocationX(ocrData)
        trainData = '/home/daerimicr/icrRest/labelTrain/data/invoice.train'
        f = open(trainData, 'r', encoding='utf-8')
        lines = f.readlines()

        # for item in ocrData:
        #     print(item)

        for line in lines:
            data = line.split('||')
            data[3] = data[3][:-1]
            labelDatas.append(data)

        for data in ocrData:
            text = data['text'].replace(' ', '')
            dataLoc = data['location'].split(',')

            for labelData in labelDatas:
                insertDatas = []
                deletes = []
                tempStr = text

                # data에 colLbl이 없으면 오른쪽 일치 확인
                for i in range(5):
                    if labelData[0].lower().find(tempStr.lower()) == 0:
                        # 완전일치 확인
                        if labelData[0].lower() == tempStr.lower():
                            data['colLbl'] = labelData[1]

                            for insertData in insertDatas:
                                data['text'] += ' ' + insertData['text']

                            for delete in deletes:
                                delDatas.append(delete)

                            break
                        else:
                            # 옆 문장 합쳐서 tempStr에 저장
                            for horiData in ocrDataX:
                                bottomLoc = horiData['location'].split(',')

                                # 수평 check
                                if locationCheck(dataLoc[1], bottomLoc[1], 20, -20) and locationCheck(dataLoc[0], bottomLoc[0], 10, -1000) and data['text'] != horiData['text'] and horiData not in insertDatas:
                                    tempStr += horiData['text'].replace(' ', '')
                                    deletes.append(horiData)
                                    insertDatas.append(horiData)
                                    break
                    else:
                        break

        for data in ocrData:
            text = data['text'].replace(' ', '')
            dataLoc = data['location'].split(',')

            for labelData in labelDatas:
                insertDatas = []
                deletes = []
                tempStr = text
                # 아래쪽 일치 확인
                for i in range(4):
                    if labelData[0].lower().find(tempStr.lower()) == 0:
                        # 완전일치 확인
                        if labelData[0].lower() == tempStr.lower():
                            data['colLbl'] = labelData[1]

                            for insertData in insertDatas:
                                data['text'] += ' ' + insertData['text']

                            for delete in deletes:
                                delDatas.append(delete)

                            break
                        else:
                            # 아래 문장 합쳐서 tempStr에 저장
                            for bottomData in ocrData:
                                bottomLoc = bottomData['location'].split(',')

                                # 수직 check and 아래 문장 check
                                if verticalCheck(dataLoc, bottomLoc, 30, -50) and locationCheck(dataLoc[1], bottomLoc[1], 0, -120):
                                    tempStr += bottomData['text'].replace(' ', '')
                                    deletes.append(bottomData)
                                    insertDatas.append(bottomData)
                    else:
                        break



        delDatas = uniq(delDatas)
        for delData in delDatas:
            ocrData.remove(delData)

        return ocrData
    except Exception as e:
        print(e)

def uniq(ocrData):
    result = []
    for a in ocrData:
        if result.count(a) < 1:
            result.append(a)
    return result

def sortArrLocationX(inputArr):
    tempArr = []
    retArr = []
    for item in inputArr:
        tempArr.append((makeindexX(item['location']), item))
    tempArr.sort(key=operator.itemgetter(0))
    for tempItem in tempArr:
        retArr.append(tempItem[1])
    return retArr

def makeindexX(location):
    if len(location) > 0:
        temparr = location.split(",")
        for i in range(0, 5):
            if (len(temparr[1]) < 5):
                temparr[1] = '0' + temparr[1]
        return int(temparr[0] + temparr[1])
    else:
        return 999999999999
    
def verticalCheck(lblLoc, entLoc, plus, minus):
    try:
        lblwidthLoc = (int(lblLoc[0]) + (int(lblLoc[0]) + int(lblLoc[2]))) / 2
        entwidthLoc = (int(entLoc[0]) + (int(entLoc[0]) + int(entLoc[2]))) / 2

        if minus < lblwidthLoc - entwidthLoc < plus:
            return True
        else:
            return False

    except Exception as e:
        raise Exception(str({'code': 500, 'message': 'checkVerticalEntry fail',
                         'error': str(e).replace("'", "").replace('"', '')}))




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
            page.save(upload_path + filename, "JPEG", dpi=(300,300))
            # page.save(upload_path + "chg_" + filename, "JPEG", dpi=(300,300))
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
                # 원본 img
                cv2.imwrite(filename, img)
                # ocr용 img
                # cv2.imwrite("chg_"+filename, img)
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
        # 'language': 'unk',
        'language': 'ko',
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
            #print(len(line))
            if (len(line)>1):
                #print("docSentence Line is Full")
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
    os.chdir(osChdir)

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
    #os.chdir("/Users/Taiho/Desktop/icrRest/")
    os.chdir(osChdir)


def companyInfoInsert(ocrData, docTopType, docType):
    try:
        # print(ocrData)
        search = "XX"
        compnayInfoList = []
        file = open("companyInfo.txt", "r", encoding="UTF-8-sig")
        for line in file:
            if line is None:
                print("companyInfo line is Null")
            else:
                companyDocTopType, companyDocType, companyName, companyRegistNo = line.strip().split("||")
                if int(docTopType) == int(companyDocTopType):
                    if int(docType) == int(companyDocType):
                        dic = {}
                        # print(companyName.find(search))
                        if companyName.find(search)  == -1:
                            dic["companyName"] = companyName
                        # print(companyRegistNo.find(search))
                        if companyRegistNo.find(search)  == -1:
                            dic["companyRegistNo"] = companyRegistNo
                        compnayInfoList.append(dic)
                        # print(compnayInfoList)
        file.close()

        for rows in compnayInfoList:
            if int(docTopType) == 58:
                if "companyName" in rows:
                    obj = {}
                    obj["entryLbl"] = "760"
                    obj["location"] = rows["companyName"].split("@@")[1]
                    obj["text"] = rows["companyName"].split("@@")[0]
                    ocrData.append(obj)

                if "companyRegistNo" in rows:
                    obj = {}
                    obj["entryLbl"] = "761"
                    obj["location"] = rows["companyRegistNo"].split("@@")[1]
                    obj["text"] = rows["companyRegistNo"].split("@@")[0]
                    ocrData.append(obj)

            if int(docTopType) == 51:
                if "companyName" in rows:
                    obj = {}
                    obj["entryLbl"] = "502"
                    obj["location"] = rows["companyName"].split("@@")[1]
                    obj["text"] = rows["companyName"].split("@@")[0]
                    ocrData.append(obj)

        return ocrData

    except Exception as ex:
        raise Exception(str(
            {'code': 500, 'message': 'companyInfoInsert error', 'error': str(ex).replace("'", "").replace('"', '')}))

if __name__=='__main__':
    app.run(host='0.0.0.0',port=5000,debug=True)
