# -*- coding: utf-8 -*-
import os
import base64
# from datetime import datetime, timedelta
from datetime import datetime
from datetime import timedelta
import cv2
import cv2 as cv
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
import hgtk
from google.cloud import vision
import numpy

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

regex = r'[가-힣]+'

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
                # lineDect.main(stringToBase64(upload_path + item))
                # imgResize(upload_path + item)
                # obj = pyOcr_google(upload_path + item, convertFilename)

                msOcr = get_Ocr_Info(upload_path + item)
                rotatedImg, retOcr = getRotateImage(upload_path + item)
                cv.imwrite(upload_path + "org_" + item, rotatedImg)
                retOcr = plusMsOcr(retOcr, msOcr)
                retOcr = sortLocX(sortLocY(retOcr))
                docTopType, docType, maxNum = findDocType(retOcr)

                if maxNum < 0.3:
                    if docTopType == 58:
                        docTopType = 51
                        docType = 339

                if docTopType == 51:
                    retOcr = textPreprocessGeneral(retOcr, rotatedImg)
                elif docTopType == 61:
                    retOcr = textPreprocessRebar(retOcr, rotatedImg)

                findColByML(retOcr)

                retOcr, retImg = updLocation(retOcr, rotatedImg, docTopType)
                retOcr = companyInfoInsert(retOcr, docTopType, docType)

                obj = {}
                obj["convertFileName"] = item[item.rfind("/") + 1:]
                obj["originFileName"] = convertFilename
                obj["docCategory"] = {"DOCTYPE": docType, "DOCTOPTYPE": docTopType, "DOCSCORE": maxNum}
                obj["data"] = retOcr

                cv.imwrite(upload_path + item, retImg)

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
            uploadFtpFile(upload_path, "org_" + item)
            os.remove(upload_path + item)
            os.remove(upload_path + "org_" + item)
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

def plusMsOcr(ocrData, msOcr):

    ocrRange = 30
    insertOcr = []

    for item in msOcr:
        mloc = [int(i) for i in item['location'].split(",")]
        mx1 = mloc[0]
        mx2 = mloc[0] + mloc[2]
        my1 = mloc[1]
        my2 = mloc[1] + mloc[3]

        insBool = True

        for gitem in ocrData:
            gloc = [int(i) for i in gitem['location'].split(",")]
            gx1 = gloc[0]
            gx2 = gloc[0] + gloc[2]
            gy1 = gloc[1]
            gy2 = gloc[1] + gloc[3]

            if gx1 < mx1 < gx2 and gy1 < my1 < gy2:
                insBool = False
                break

            if gx1 < mx2 < gx2 and gy1 < my2 < gy2:
                insBool = False
                break

            if mx1 - ocrRange < gx1 < mx2 + ocrRange and my1 - ocrRange < gy1 < my2 + ocrRange:
                insBool = False
                break

            if mx1 - ocrRange < gx2 < mx2 + ocrRange and my1 - ocrRange < gy2 < my2 + ocrRange:
                insBool = False
                break


        if insBool == True:
            print(insBool, item)
            insertOcr.append(item)

    for item in insertOcr:
        ocrData.append(item)

    return ocrData

def textPreprocessGeneral(retocr, img):
    idx = 0
    labeldics = {}
    regexp = "[-=+,#/\?:^$.@*\"※~&%ㆍ!』\\‘|\(\)\[\]\<\>`\'…》]"
    file = open("generalLabel.txt", "r", encoding="UTF-8-sig")
    for line in file:
        if line is None:
            print("generalLabel line is Null")
        else:
            labelNo, labelWord, fieldDirection = line.strip().split("||")
            labeldics[labelWord] = [labelNo, fieldDirection]
    file.close()

    #'I' 문장 제거
    while idx < len(retocr):
        if retocr[idx]["text"] == '' or retocr[idx]["text"] == '|' or retocr[idx]["text"] == ':':
            del retocr[idx]
            idx -= 1
        if retocr[idx]["text"].find(':') > -1:
            words = retocr[idx]["text"].split(":")
            if len(words[0]) > 0 and len(words[1]) > 0:
                tempdictLoc = list(map(int, retocr[idx]["location"].split(',')))
                firstLoc = tempdictLoc
                firstLoc[2] = tempdictLoc[2] - tempdictLoc[3] * (len(words[0]) / len(words[1]))
                firstLoc[2] = int(firstLoc[2])
                secondLoc = tempdictLoc
                secondLoc[0] = secondLoc[0] + firstLoc[2] + tempdictLoc[3]
                secondLoc[0] = int(secondLoc[0])
                secondLoc[2] = tempdictLoc[2] - firstLoc[2] - tempdictLoc[3]
                secondLoc[2] = int(secondLoc[2])

                tempdict = {}
                tempdict["text"] = words[0]
                tempdict["location"] = ",".join(map(str, firstLoc))
                retocr[idx] = tempdict
                tempdict["text"] = words[1]
                tempdict["location"] = ",".join(map(str, secondLoc))
                retocr.insert(idx + 1, tempdict)
        idx += 1

    idx = 0

    #같은라인 문장 합치기 레이블 문장 합치기
    while idx < len(retocr):
        isCombiend, combineData = distanceParams(retocr[idx], mostCloseWordSameLine(retocr[idx],extractSameLine(retocr[idx],retocr, 13)))
        if combineData:
            # 같은 라인에 거리가 문장높이의 절반 이하일 경우 text는 합친다
            if isCombiend < int(retocr[idx]["location"].split(",")[3]) / 2:
                retocr[idx] = combiendText(retocr[idx], combineData)
                retocr.remove(combineData)
                idx -= 1
            elif combiendLabelText(retocr[idx]["text"], combineData["text"], list(labeldics.keys())):
                # 같은 줄에 다음 text와 합쳐서 레이블의 부분일 경우 합친다
                retocr[idx] = combiendText(retocr[idx], combineData)
                retocr.remove(combineData)
                idx -= 1
        idx += 1

    labellist = {}
    for item in retocr:
        for tempdict in labeldics.keys():
            ratio = similar(re.sub(regexp, '', item["text"].lower()), tempdict.lower())
            if ratio > 0.8:
                if item['location'] in labellist:
                    if  labellist[item['location']][0] < ratio:
                        labellist[item['location']] = [ratio, labeldics[tempdict]]
                else:
                    labellist[item['location']] = [ratio, labeldics[tempdict]]
    retocr = findSingleField('General', retocr, labellist)
    retocr = findMultiField('General', retocr, labellist, img)

    return retocr

def textPreprocessRebar(retocr, img):
    idx = 0
    labeldics = {}
    regexp = "[-=+,#/\?:^$.@*\"※~&%ㆍ!』\\‘|\(\)\[\]\<\>`\'…》]"
    file = open("rebarLabel.txt", "r", encoding="UTF-8-sig")
    for line in file:
        if line is None:
            print("rebarLabel line is Null")
        else:
            labelNo, labelWord, fieldDirection = line.strip().split("||")
            labeldics[labelWord] = [labelNo, fieldDirection]
    file.close()

    #'I' 문장 제거
    while idx < len(retocr):
        if retocr[idx]["text"] == '' or retocr[idx]["text"] == '|' or retocr[idx]["text"] == ':':
            del retocr[idx]
            idx -= 1
        if retocr[idx]["text"].find(':') > -1:
            words = retocr[idx]["text"].split(":")
            if len(words[0]) > 0 and len(words[1]) > 0:
                tempdictLoc = list(map(int, retocr[idx]["location"].split(',')))
                firstLoc = tempdictLoc
                firstLoc[2] = tempdictLoc[2] - tempdictLoc[3] * (len(words[0]) / len(words[1]))
                secondLoc = tempdictLoc
                secondLoc[0] = secondLoc[0] + firstLoc[2] + tempdictLoc[3]
                secondLoc[2] = tempdictLoc[2] - firstLoc[2] - tempdictLoc[3]

                tempdict = {}
                tempdict["text"] = words[0]
                tempdict["location"] = ",".join(map(str, firstLoc))
                retocr[idx] = tempdict
                tempdict["text"] = words[1]
                tempdict["location"] = ",".join(map(str, secondLoc))
                retocr.insert(idx + 1, tempdict)
        idx += 1

    idx = 0
    # 같은라인 문장 합치기 레이블 문장 합치기
    while idx < len(retocr):
        isCombiend, combineData = distanceParams(retocr[idx], mostCloseWordSameLine(retocr[idx],extractSameLine(retocr[idx],retocr, 22)))
        if combineData:
            # 같은 라인에 거리가 문장높이의 절반 이하일 경우 text는 합친다
            if isCombiend < int(retocr[idx]["location"].split(",")[3]) / 1.5 and not retocr[idx]["text"] in labeldics.keys():
                retocr[idx] = combiendText(retocr[idx], combineData)
                retocr.remove(combineData)
                idx -= 1
            elif combiendLabelText(retocr[idx]["text"], combineData["text"], list(labeldics.keys())):
                # 같은 줄에 다음 text와 합쳐서 레이블의 부분일 경우 합친다
                retocr[idx] = combiendText(retocr[idx], combineData)
                retocr.remove(combineData)
                idx -= 1
        idx += 1

    labellist = {}
    for item in retocr:
        for tempdict in labeldics.keys():
            ratio = similar(re.sub(regexp, '', item["text"].lower()), tempdict.lower())
            if ratio > 0.8:
                if item['location'] in labellist:
                    if  labellist[item['location']][0] < ratio:
                        labellist[item['location']] = [ratio, labeldics[tempdict]]
                else:
                    labellist[item['location']] = [ratio, labeldics[tempdict]]
    retocr = findSingleField('Rebar', retocr, labellist)
    retocr = findMultiField('Rebar', retocr, labellist, img)

    return retocr

def findMultiField(toptype, retocr, labellist, img):
    #같은 라인에 있는 레이블끼리 집합생성
    sameLineLabel = []
    for key, value in labellist.items():
        if value[1][1] == 'M':
            location = list(map(int, key.split(",")))
            if len(sameLineLabel) == 0:
                sameLineLabel.append([[location, value[1][0]]])
            else:
                #기존 레이블과 동일 라인일 경우
                addFlag = False
                for lines in range(len(sameLineLabel)):
                    for line in range(len(sameLineLabel[lines])):
                        if not addFlag and abs(sameLineLabel[lines][line][0][1] - location[1]) < 50:
                            sameLineLabel[lines].append([location, value[1][0]])
                            addFlag = True
                if not addFlag:
                    sameLineLabel.append([[location, value[1][0]]])

    #일반 송장에서 레이블이 복수 추출되었으나 품목이 추출 안된경우 품목 레이블 생성
    if toptype == 'General':
        for x in range(len(sameLineLabel)):
            if len(sameLineLabel[x]) > 1:
                minx = [5000]
                existFlag = False
                for y in range(len(sameLineLabel[x])):
                    coords = sameLineLabel[x][y][0]
                    if minx[0] > coords[0]:
                        minx = coords
                    if sameLineLabel[x][y][1] == '504':
                        existFlag = True
                if not existFlag:
                    sameLineLabel[x].append([[round(minx[0]/2),minx[1],minx[2],minx[3]],'504'])
    allResultArr = []
    for x in range(len(sameLineLabel)):
        if len(sameLineLabel[x]) > 1:
            for y in range(len(sameLineLabel[x])):
                coords = sameLineLabel[x][y][0]
                labelno = sameLineLabel[x][y][1]
                startx, endx = getSideLine(img, coords)
                # startx, endx 사이에 있으면서 coords[1] + coords[3] 아래에 있는 문장을 labelno로 매핑
                retocr, resultArr = rangedFiled(retocr, startx, endx, coords[1] + coords[3], labelno)
                allResultArr = allResultArr + resultArr

    stopwords = []
    deletewords = []
    file = open("bannedWord.txt", "r", encoding="UTF-8-sig")
    for line in file:
        if line is None:
            print("bannedWord line is Null")
        else:
            keyword, type, usage = line.strip().split("||")
            if toptype == type:
                if usage == 'stop':
                    stopwords.append(keyword)
                if usage == 'delete':
                    deletewords.append(keyword)
    file.close()

    sameLineField = []
    stopLine = []
    deletelines = []
    for result in allResultArr:
        location = list(map(int, result[0].split(",")))
        if len(sameLineField) == 0:
            sameLineField.append([[location, result[1], result[2]]])
            if result[2] in stopwords:
                stopLine.append(location[1])
            if result[2] in deletewords:
                deletelines.append(location[1])
        else:
            # 기존 필드와 동일 라인일 경우
            addFlag = False
            for lines in range(len(sameLineField)):
                for line in range(len(sameLineField[lines])):
                    if not addFlag and abs(sameLineField[lines][line][0][1] - location[1]) < 30:
                        sameLineField[lines].append([location, result[1], result[2]])
                        if result[2] in stopwords:
                            stopLine.append(location[1])
                        if result[2] in deletewords:
                            deletelines.append(location[1])
                        addFlag = True
            if not addFlag:
                sameLineField.append([[location, result[1], result[2]]])
                if result[2] in stopwords:
                    stopLine.append(location[1])

                if result[2] in deletewords:
                    deletelines.append(location[1])

    stopMinLine = 100000
    if len(stopLine) != 0:
        stopMinLine = min(stopLine)

    print('stopLine ====== ', stopMinLine)
    #stop delete words 처리
    for item in retocr:
        for result in allResultArr:
            if item['location'] == result[0] and list(map(int, result[0].split(",")))[1] < stopMinLine - 30:
                deleteFlag = False
                for deleteline in deletelines:
                    if abs(deleteline - list(map(int, result[0].split(",")))[1]) < 30:
                        deleteFlag = True
                if not deleteFlag:
                    item['entryLbl'] = result[1]
                    print(result[0], '\t', result[1], '\t', result[2])

    secondStopLine = 0
    if stopMinLine != 100000:

        allResultArr = []
        for x in range(len(sameLineLabel)):
            if len(sameLineLabel[x]) > 1 and int(sameLineLabel[x][0][0][1]) > stopMinLine:
                for y in range(len(sameLineLabel[x])):
                    coords = sameLineLabel[x][y][0]
                    labelno = sameLineLabel[x][y][1]
                    startx, endx = getSideLine(img, coords)
                    # startx, endx 사이에 있으면서 coords[1] + coords[3] 아래에 있는 문장을 labelno로 매핑
                    retocr, resultArr = rangedFiled(retocr, startx, endx, coords[1] + coords[3], labelno)
                    allResultArr = allResultArr + resultArr
            secondStopLine = sameLineLabel[x][0][0][1] + sameLineLabel[x][0][0][3]

        delStopLine = []
        for x in stopLine:
            if x < secondStopLine:
                delStopLine.append(x)

        for x in delStopLine:
            stopLine.remove(x)

        stopMinLine = 100000
        if len(stopLine) != 0:
            stopMinLine = min(stopLine)

        print('stopLine ====== ', stopMinLine)
        for item in retocr:
            for result in allResultArr:
                if item['location'] == result[0] and list(map(int, result[0].split(",")))[1] < stopMinLine - 30:
                    deleteFlag = False
                    for deleteline in deletelines:
                        if abs(deleteline - list(map(int, result[0].split(",")))[1]) < 30:
                            deleteFlag = True
                    if not deleteFlag:
                        item['entryLbl'] = result[1]
                        print(result[0], '\t', result[1], '\t', result[2])

    return retocr

#싱글필드 추출
def findSingleField(toptype, retocr, labellist):
    fixfilename = ''
    if toptype == 'Rebar':
        fixfilename = 'rebarFixLabel.txt'
    elif toptype == 'General':
        fixfilename = 'generalFixLabel.txt'
    fixList = {}

    file = open(fixfilename, "r", encoding="UTF-8-sig")
    for line in file:
        if line is None:
            print("FixLabel line is Null")
        else:
            labelno, text = line.strip().split("||")
            if labelno in fixList:
                fixList[labelno].append(text)
            else:
                fixList[labelno] = [text]
    file.close()

    #similarity 검색
    resultDic = {}
    for serialno in fixList:
        maxRatio = 0
        for textlist in fixList[serialno]:
            for item in retocr:
                ratio = similar(makeParts(textlist), makeParts(item["text"]))
                if ratio > 0.5 and ratio > maxRatio:
                    maxRatio = ratio
                    resultDic[serialno] = item["text"]

    #방향이 있는 싱글 검색  R L D
    for key, value in labellist.items():
        direction = value[1][1]
        if direction == 'R' or direction == 'L' or direction == 'D' or direction == 'RD':
            resultDic = findSingleFieldFromDirection(resultDic, retocr, direction, key, value[1][0])
    resultLists = []
    for key, value in resultDic.items():
        list = []
        list.append(key)
        list.append(value)
        resultLists.append(list)

    for item in retocr:
        for resultList in resultLists:
            if item['text'] == resultList[1]:
                item['entryLbl'] = resultList[0]
                print(resultList[0], '\t', resultList[1])
                if toptype == 'Rebar':
                    resultLists.remove(resultList)
    return retocr

def findSingleFieldFromDirection(resultDic, retocr, direction, coords, label):
    try:
        retDict = {}
        baseLoc = list(map(int, coords.split(',')))
        min = 700
        if direction == 'R' or direction == 'RD':
            findFlag = False
            for item in retocr:
                location = list(map(int, item['location'].split(",")))
                if abs(baseLoc[1] - location[1]) < 13 and location[0] - baseLoc[0] > 0 and location[0] - baseLoc[0] < min:
                    if label == "892":
                        if hasNumbers(item["text"]):
                            min = location[0] - baseLoc[0]
                            resultDic[label] = item["text"]
                            findFlag = True
                    else:
                        min = location[0] - baseLoc[0]
                        resultDic[label] = item["text"]
                        findFlag = True
            if  direction == 'RD' and not findFlag:
                for item in retocr:
                    location = list(map(int, item['location'].split(",")))
                    startx = baseLoc[0] - 50
                    endx = baseLoc[0] + baseLoc[2] + 50
                    locationcenter = location[0] + (location[2] / 2)
                    if locationcenter > startx and endx > locationcenter and location[1] - baseLoc[1] > 0 and location[1] - baseLoc[1] < min:
                        min = location[1] - baseLoc[1]
                        resultDic[label] = item["text"]

        return resultDic

    except Exception as e:
        raise Exception(str(
            {'code': 500, 'message': 'mostCloseWordSameLine fail', 'error': str(e).replace("'", "").replace('"', '')}))

def hasNumbers(inputString):
    return any(char.isdigit() for char in inputString)

#영역내 멀티 필드 추출
def rangedFiled(retocr, startx, endx, endy, labelno):
    print(labelno, 'start label ', startx, 'end label ', endx)
    blanklimit = 300
    cursor = endy + 30
    extractFields = []
    idx = 0
    while idx < len(retocr):
        splitLoc = list(map(int, retocr[idx]["location"].split(',')))
        targetCenter = (splitLoc[0] * 2 + splitLoc[2]) / 2
        if startx < targetCenter and endx > targetCenter:
            if endy < splitLoc[1] + splitLoc[3]:
                extractFields.append(retocr[idx])
        idx += 1
    # 추출된 엔트리들중 같은 라인에 있는 문장 합치기
    idx = 0
    resultArr = []
    for idx in range(len(extractFields)):
        nowy = list(map(int, extractFields[idx]["location"].split(",")))[1]
        #리미트 안에 있는지
        if cursor + blanklimit > nowy:
            # 다음게 있는지
            if idx + 1 < len(extractFields):
                nexty = list(map(int, extractFields[idx + 1]["location"].split(",")))[1]
                # 다음게 같은 라인인지
                if abs(nowy - nexty) < 13:
                    retocr[retocr.index(extractFields[idx])] = combiendText(extractFields[idx], extractFields[idx + 1])
                    retocr.remove(extractFields[idx + 1])
                    extractFields[idx+1] = combiendText(extractFields[idx], extractFields[idx + 1])
                # 다음게 다른 라인
                else:
                    cursor = nowy
                    resultArr.append([extractFields[idx]["location"], labelno, extractFields[idx]["text"]])
                    print(labelno, '===', extractFields[idx])
            # 다음게 없을때
            else:
                cursor = nowy
                resultArr.append([extractFields[idx]["location"], labelno, extractFields[idx]["text"]])
                print(labelno, '===', extractFields[idx])
        #리미트 밖
        else:
            break
    return retocr, resultArr

def matchEntry(ocrData, extractFields, labelno):
    for item in ocrData:
        if item['location'] == extractFields['location']:
            item['entryLbl'] = labelno
    return ocrData

def makeParts(word):
    retStr = ''
    for char in word:
        if hgtk.checker.is_hangul(char):
            retStr += ''.join(hgtk.letter.decompose(char))
        else:
            retStr += char
    return retStr

def getSideLine(img, coords):
    item = cv.bitwise_not(img)
    #ret, item = cv.threshold(item, 87, 255, cv.THRESH_BINARY)
    verticalsize = 40
    deleteVerticalLineWeight = 9
    verticalStructure = cv.getStructuringElement(cv.MORPH_RECT, (1, int(verticalsize)))
    verticalDilateStructure = cv.getStructuringElement(cv.MORPH_RECT, (deleteVerticalLineWeight, int(verticalsize)))

    item = cv.erode(item, verticalStructure)
    item = cv.dilate(item, verticalDilateStructure)

    edges = cv.Canny(item, 50, 200, apertureSize=3)
    minLineLength = 3500
    maxLineGap = 80
    findLimit = 1000

    height, width = img.shape[:2]
    # 레이블의 y좌표
    label_coord_y = coords[1] + coords[3] / 2
    # 레이블의 X좌표
    label_coord_x = coords[0] + coords[2] / 2
    # 문서 X축 시작시점
    label_start_x = 0
    # 문서 X축 종료시점
    label_end_x = width
    lines = cv.HoughLinesP(edges, 1, numpy.pi / 360, 100, minLineLength, maxLineGap)
    for i in range(len(lines)):
        for x1, y1, x2, y2 in lines[i]:
            #cv.line(img, (x1, y1), (x2, y2), (0, 0, 255), 3)
            if y1 > label_coord_y and y1 < label_coord_y + findLimit:

                myradians = math.atan2(y1 - y2, x1 - x2)
                mydegrees = math.degrees(myradians)
                mydegrees = mydegrees + 180
                if mydegrees > 260.0 and mydegrees < 280.0:
                    # cv.line(img, (x1, y1), (x2, y2), (0, 0, 255), 3)
                    if label_coord_x > x1 and label_start_x < x1:
                        label_start_x = x1
                    if label_coord_x < x1 and label_end_x > x1:
                        label_end_x = x1

    # cv.imshow('img1', cv.resize(img, None, fx=0.15, fy=0.15))
    # cv.waitKey(0)
    # cv.destroyAllWindows()
    return label_start_x, label_end_x

def getOcrLabels(inputimg):
    try:
        ocrData = []
        client = vision.ImageAnnotatorClient()
        # item1 = cv.imread(item)
        success, encoded_image = cv.imencode('.jpg', inputimg)
        content = encoded_image.tobytes()
        image = vision.types.Image(content=content)

        response = client.document_text_detection(image=image)

        for page in response.full_text_annotation.pages:
            for block in page.blocks:
                # print('\nBlock confidence: {}\n'.format(block.confidence))

                for paragraph in block.paragraphs:
                    # print('Paragraph confidence: {}'.format(paragraph.confidence))

                    for word in paragraph.words:
                        word_text = ''
                        for symbol in word.symbols:
                            if symbol.confidence > 0.25:
                                word_text += symbol.text
                        word_text = word_text.replace('"','')
                        x = word.bounding_box.vertices[0].x
                        y = word.bounding_box.vertices[0].y

                        width = int(word.bounding_box.vertices[1].x) - int(word.bounding_box.vertices[0].x)
                        height = int(word.bounding_box.vertices[3].y) - int(word.bounding_box.vertices[0].y)

                        location = str(x) + ',' + str(y) + ',' + str(width) + ',' + str(height)
                        if x > 0 and y > 0 and word_text != "":
                            ocrData.append({"location": location, "text":word_text})

        ocrData = sortLocX(sortLocY(ocrData))
        return ocrData
    except Exception as e:
        print(e)

def updLocation(ocrData, img, docTopType):
    try:
        regX = r'[가-힣]+'

        minX = 100000
        maxX = 0
        minXText = ''
        maxXText = ''
        minY = 100000
        maxY = 0
        minYText = ''
        maxYText = ''

        height, width = img.shape[:2]

        garbage = ['공미', '엘씨엘폼']

        for data in ocrData:
            location = data['location']
            location = location.split(",")

            if re.findall(regX, data['text']) and data['text'] not in garbage:
                if docTopType == 58:
                    if minX > int(location[0]) and int(location[0]) > 160:
                        minX = int(location[0])
                        minXText = data['text']
                    if maxX < int(location[0]) + int(location[2]) and int(location[0]) + int(location[2]) < width - 160:
                        maxX = int(location[0]) + int(location[2])
                        maxXText = data['text']
                    if minY > int(location[1]):
                        minY = int(location[1])
                        minYText = data['text']
                    if maxY < int(location[1]) + int(location[3]):
                        maxY = int(location[1]) + int(location[3])
                        maxYText = data['text']
                else:
                    if minX > int(location[0]):
                        minX = int(location[0])
                        minXText = data['text']
                    if maxX < int(location[0]) + int(location[2]):
                        maxX = int(location[0]) + int(location[2])
                        maxXText = data['text']
                    if minY > int(location[1]):
                        minY = int(location[1])
                        minYText = data['text']
                    if maxY < int(location[1]) + int(location[3]):
                        maxY = int(location[1]) + int(location[3])
                        maxYText = data['text']

        print("minX : ", minX, ", minXText : ", minXText, ", maxX : ", maxX, ", maxXText : ", maxXText)
        print("minY : ", minY, ", minYText : ", minYText, ", maxY : ", maxY, ", maxYText : ", maxYText)
        margin = 100

        #doctype 58일 경우 minX maxX 를 이미지선에서 추출

        # if docTopType == 58:
        #     img = getCropedImg(img, minY, maxY)
        # else:
        y = minY - margin
        if y < 0:
            y = 0
        x = minX - margin
        if x < 0:
            x = 0

        img = img[y:maxY+margin, x:maxX+margin]

        img = imgResize(img)

        for data in ocrData:
            updLocation = data['location']
            updLocation = relocate(updLocation, minX, minY, maxX, maxY)
            data['location'] = updLocation

        #     cv.line(img, (int(updLocation.split(',')[0]), int(updLocation.split(',')[1])), (int(updLocation.split(',')[0]) + int(updLocation.split(',')[2]), int(updLocation.split(',')[1])+int(updLocation.split(',')[3])), (0, 0, 255), 3)
        #
        # cv.imshow('img1', cv.resize(img, None, fx=0.25, fy=0.25))
        # cv.waitKey(0)
        # cv.destroyAllWindows()
        return ocrData, img
    except Exception as e:
        print(e)

def relocate(location, minX, minY, maxX, maxY):
    margin = 100
    targetwidth = 2100 - (margin * 2)
    targetheight = 2970 - (margin * 2)

    location = list(map(int, location.split(",")))
    location[0] = round((location[0] - minX) / (maxX - minX) * targetwidth + margin)
    location[2] = round((location[2]) / (maxX - minX) * targetwidth)
    location[1] = round((location[1] - minY) / (maxY - minY) * targetheight + margin)
    location[3] = round((location[3]) / (maxY - minY) * targetheight)

    location = ','.join(map(str, location))
    return location


def getAngleFromGoogle(response):
    try:
        first = []
        last = []
        maxlen = 0
        ocrData = []

        # 상위 5개 angle search start
        list = []
        temp = ''
        for page in response.full_text_annotation.pages:
            pagewidth = page.width
            pageheight = page.height
            for block in page.blocks:
                for paragraph in block.paragraphs:
                    for word in paragraph.words:
                        word_text = ''
                        for symbol in word.symbols:
                            if symbol.confidence > 0.25:
                                word_text += symbol.text
                        word_text = word_text.replace('"', '')
                        x1 = word.bounding_box.vertices[0].x
                        y1 = word.bounding_box.vertices[0].y
                        x2 = word.bounding_box.vertices[1].x
                        y2 = word.bounding_box.vertices[1].y
                        x3 = word.bounding_box.vertices[2].x
                        y3 = word.bounding_box.vertices[2].y
                        x4 = word.bounding_box.vertices[3].x
                        y4 = word.bounding_box.vertices[3].y
                        location = [x1, y1, x2, y2, x3, y3, x4, y4]
                        if x1 > 0 and y1 > 0 and word_text != "":
                            ocrData.append({"location": location, "text": word_text})
                            print({"location": location, "text": word_text})

                        list.append({"length": len(word_text), "word": word})
        data = sorted(list, key=lambda l: (l['length']), reverse=True)
        retDegrees = []

        i = 0
        while i < 10:
            # print(data[i]['word'])
            first = []
            last = []
            if data[i]['word'].bounding_box.vertices[0].x > 100 and data[i]['word'].bounding_box.vertices[0].y > 100:
                for symbol in data[i]['word'].symbols:
                    if len(first) == 0:
                        first.append(symbol.bounding_box.vertices[0].x)
                        first.append(symbol.bounding_box.vertices[0].y)
                    last = [symbol.bounding_box.vertices[0].x, symbol.bounding_box.vertices[0].y]

                radians = math.atan2(first[1] - last[1], first[0] - last[0])
                retDegrees.append(radians)
                i += 1
            else:
                del data[i]
        # 상위 5개 angle search end
        myradians = avgDegrees(retDegrees) + numpy.pi
        mydegrees = math.degrees(myradians)
        ocrData = newCoordFromRadian(ocrData, myradians, pagewidth, pageheight)
        ocrData = sortLocX(sortLocY(ocrData))
        return mydegrees, ocrData
    except Exception as e:
        print(e)

def newCoordFromRadian(ocrData, myradians, pagewidth, pageheight):
    #newOutline
    minx, miny = getNewOutLine(myradians, pagewidth, pageheight)
    for item in ocrData:
        item['location'] = getNewCoords(item['location'], myradians, minx, miny)
    return ocrData

def getNewCoords(locaitonlist, myradians, minx, miny):
    retCoord = []
    for i in range(0, 8, 2):
        retCoord.append(getNewCoord(locaitonlist[i], locaitonlist[i+1], myradians))
    startx = round((retCoord[0][0] + retCoord[3][0]) / 2 - minx)
    starty = round((retCoord[0][1] + retCoord[1][1]) / 2 - miny)
    width =  round((retCoord[1][0] + retCoord[2][0]) / 2 - minx - startx)
    height = round((retCoord[2][1] + retCoord[3][1]) / 2 - miny - starty)
    location = str(startx) + ',' + str(starty) + ',' + str(width) + ',' + str(height)

    return location

def getNewOutLine(myradians, pagewidth, pageheight):
    listx, listy = [], []
    x, y = getNewCoord(pagewidth, 0, myradians)
    listx.append(x)
    listy.append(y)
    x, y = getNewCoord(0, pageheight, myradians)
    listx.append(x)
    listy.append(y)
    x, y = getNewCoord(pagewidth, pageheight, myradians)
    listx.append(x)
    listy.append(y)
    minx = min(listx)
    miny = min(listy)
    if minx > 0:
        minx = 0
    if miny > 0:
        miny = 0
    return minx, miny


def getNewCoord(oldx, oldy, radian):
    new_x = round(math.cos(-radian) * oldx - math.sin(-radian) * oldy)
    new_y = round(math.sin(-radian) * oldx + math.cos(-radian) * oldy)
    return [new_x, new_y]

def avgDegrees(arr):
    for i in range(7):
        ave = numpy.mean(arr)
        arr2 = abs(arr - ave)
        index, value = max(enumerate(arr2), key=operator.itemgetter(1))
        del arr[index]
    return arr[0]

def getRotateImage(imgPre):
    try:
        item = cv.imread(imgPre)

        client = vision.ImageAnnotatorClient()
        success, encoded_image = cv.imencode('.jpg', item)
        content = encoded_image.tobytes()

        image = vision.types.Image(content=content)

        response = client.document_text_detection(image=image)
        # content = encoded_image.tobytes()

        mydegrees, ocrData = getAngleFromGoogle(response)
        print(mydegrees)
        # image = cv.imread(item)

        (h, w) = item.shape[:2]
        center = (w // 2, h // 2)

        M = cv.getRotationMatrix2D(center, mydegrees, 0.5)

        newX, newY = w * 0.5, h * 0.5
        r = numpy.deg2rad(mydegrees)
        newX, newY = (
            abs(numpy.sin(r) * newY) + abs(numpy.cos(r) * newX), abs(numpy.sin(r) * newX) + abs(numpy.cos(r) * newY))

        (tx, ty) = ((newX - w) / 2, (newY - h) / 2)
        M[0, 2] += tx  # third column of matrix holds translation, which takes effect after rotation.
        M[1, 2] += ty
        thresh1 = cv.warpAffine(item, M, (int(newX), int(newY)),
                                flags=cv.INTER_CUBIC, borderMode=cv.BORDER_REPLICATE)
        thresh1 = cv.bitwise_not(thresh1)
        verticalsize = 20
        deleteVerticalLineWeight = 2
        verticalStructure = cv.getStructuringElement(cv.MORPH_RECT, (1, int(verticalsize)))
        verticalDilateStructure = cv.getStructuringElement(cv.MORPH_RECT, (deleteVerticalLineWeight, int(verticalsize)))

        thresh1 = cv.erode(thresh1, verticalStructure)
        thresh1 = cv.dilate(thresh1, verticalDilateStructure)

        edges = cv.Canny(thresh1, 50, 200, apertureSize=3)
        minLineLength = 3500
        maxLineGap = 50

        longestlength = 0
        longlineDegree = -90
        lines = cv.HoughLinesP(edges, 1, numpy.pi / 360, 100, minLineLength, maxLineGap)
        for i in range(len(lines)):
            for x1, y1, x2, y2 in lines[i]:
                myradians = math.atan2(y1 - y2, x1 - x2)
                tempmydegrees = math.degrees(myradians)
                print(tempmydegrees)
                print('x1: ' + repr(x1) + 'y1: ' + repr(y1) + 'x2: ' + repr(x2) + 'y2: ' + repr(y2))
                if tempmydegrees < -85.0 and tempmydegrees > -95.0:
                    cv.line(thresh1, (x1, y1), (x2, y2), (0, 0, 255), 4)
                    dx = x2 - x1
                    dy = y2 - y1
                    if math.sqrt((dx * dx) + (dy * dy)) > longestlength:
                        longestlength = math.sqrt((dx * dx) + (dy * dy))
                        longlineDegree = tempmydegrees

        M = cv.getRotationMatrix2D(center, mydegrees + longlineDegree + 90, 1)

        newX, newY = w, h
        r = numpy.deg2rad(mydegrees + longlineDegree + 90)
        newX, newY = (
            abs(numpy.sin(r) * newY) + abs(numpy.cos(r) * newX), abs(numpy.sin(r) * newX) + abs(numpy.cos(r) * newY))

        (tx, ty) = ((newX - w) / 2, (newY - h) / 2)
        M[0, 2] += tx  # third column of matrix holds translation, which takes effect after rotation.
        M[1, 2] += ty
        rotated = cv.warpAffine(item, M, (int(newX), int(newY)),
                                flags=cv.INTER_CUBIC, borderMode=cv.BORDER_REPLICATE)

        # for item in ocrData:
        #     coords = [int(i) for i in item['location'].split(",")]
        #     cv.line(rotated, (coords[0], coords[1]), (coords[0] + coords[2], coords[1] + coords[3]), (0, 0, 255), 3)

        # cv.imshow('img1', cv.resize(rotated, None, fx=0.15, fy=0.15))
        # cv.waitKey(0)
        # cv.destroyAllWindows()

        return rotated, ocrData
    except Exception as e:
        print(e)


def getGoogleOutline(item):
    ocrData = []
    client = vision.ImageAnnotatorClient()
    # item1 = cv.imread(item)
    success, encoded_image = cv.imencode('.jpg', item)
    content = encoded_image.tobytes()

    image = vision.types.Image(content=content)

    response = client.document_text_detection(image=image)
    # print(response.text_annotations[0])
    # x = response.text_annotations[0].bounding_poly.vertices[0].x
    # y = response.text_annotations[0].bounding_poly.vertices[0].y
    # w = response.text_annotations[0].bounding_poly.vertices[1].x
    # h = response.text_annotations[0].bounding_poly.vertices[2].y

    minY = 10000
    maxY = 0
    minText = ""
    maxText = ""
    minBool = False
    maxBool = False

    for page in response.full_text_annotation.pages:
        for block in page.blocks:
            for paragraph in block.paragraphs:
                for word in paragraph.words:
                    text = ""
                    for symbol in word.symbols:
                        text += symbol.text
                        for vertice in symbol.bounding_box.vertices:
                            if re.findall(regex, text) and minY > vertice.y:
                                minY = vertice.y
                                minBool = True

                            if re.findall(regex, text) and maxY < vertice.y:
                                maxY = vertice.y
                                maxBool = True

                    if minBool == True:
                        minText = text
                        minBool = False

                    if maxBool == True:
                        maxText = text
                        maxBool = False

    print("res MinY : ", minY, "minText :", minText, "res MaxY :", maxY, "maxText : ", maxText)

    if minY < 0:
        minY = 0

    return minY, maxY

def getCropedImg(rotatedimg):
    try:
        ret, thresh1 = cv.threshold(rotatedimg, 140, 255, cv.THRESH_BINARY)
        thresh1 = cv.bitwise_not(thresh1)
        # thresh1 = cv.adaptiveThreshold(thresh1, 255, cv.ADAPTIVE_THRESH_MEAN_C, cv.THRESH_BINARY, 15, -2)
        verticalsize = 20
        deleteVerticalLineWeight = 2
        verticalStructure = cv.getStructuringElement(cv.MORPH_RECT, (1, int(verticalsize)))
        verticalDilateStructure = cv.getStructuringElement(cv.MORPH_RECT, (deleteVerticalLineWeight, int(verticalsize)))

        thresh1 = cv.erode(thresh1, verticalStructure)
        thresh1 = cv.dilate(thresh1, verticalDilateStructure)

        # cv.imshow('img1', cv.resize(thresh1, None, fx=0.15, fy=0.15))
        # cv.waitKey(0)
        # cv.destroyAllWindows()
        edges = cv.Canny(thresh1, 50, 200, apertureSize=3)
        minLineLength = 3500
        maxLineGap = 50
        height, width = rotatedimg.shape[:2]
        limitLine = 100
        minX = width
        maxX = 0
        margin = 70

        lines = cv.HoughLinesP(edges, 1, numpy.pi / 360, 100, minLineLength, maxLineGap)
        for i in range(len(lines)):
            for x1, y1, x2, y2 in lines[i]:
                # myradians = math.atan2(y1 - y2, x1 - x2)
                # mydegrees = math.degrees(myradians)
                # mydegrees = mydegrees + 180
                #
                # if mydegrees > 260.0 and mydegrees < 280.0:
                #     cv.line(thresh1, (x1, y1), (x2, y2), (0, 255, 255), 3)
                #     print('x1: ' + repr(x1) + 'y1: ' + repr(y1) + 'x2: ' + repr(x2) + 'y2: ' + repr(y2))
                #     for j in range(len(lines)):
                #         for xx1, yy1, xx2, yy2 in lines[j]:
                #             if x1 == xx1 and y1 + 500 > yy2 and y1 < yy2:
                #                 cv.line(thresh1, (x1, y1), (x2, y2), (0, 0, 255), 3)
                #                 if margin < x1 and minX > x1:
                #                     minX = x1
                #                 if margin < x2 and minX > x2:
                #                     minX = x2
                #                 if width - margin > x1 and maxX < x1:
                #                     maxX = x1
                #                 if width - margin > x2 and maxX < x2:
                #                     maxX = x2
                # if mydegrees > 80.0 and mydegrees < 100.0:
                #     cv.line(thresh1, (x1, y1), (x2, y2), (0, 255, 255), 3)
                #     print('x1: ' + repr(x1) + 'y1: ' + repr(y1) + 'x2: ' + repr(x2) + 'y2: ' + repr(y2))
                #     for j in range(len(lines)):
                #         for xx1, yy1, xx2, yy2 in lines[j]:
                #             if x1 == xx1 and y2 + 500 > yy1 and y2 < yy1:
                #                 cv.line(thresh1, (x1, y1), (x2, y2), (0, 0, 255), 3)
                #                 if margin < x1 and minX > x1:
                #                     minX = x1
                #                 if margin < x2 and minX > x2:
                #                     minX = x2
                #                 if width - margin > x1 and maxX < x1:
                #                     maxX = x1
                #                 if width - margin > x2 and maxX < x2:
                #                     maxX = x2
                dx = x2 - x1
                dy = y2 - y1
                if math.sqrt((dx * dx) + (dy * dy)) > limitLine:
                    cv.line(thresh1, (x1, y1), (x2, y2), (0, 0, 255), 3)
                    if margin < x1 and minX > x1:
                        minX = x1
                    if margin < x2 and minX > x2:
                        minX = x2
                    if width - margin > x1 and maxX < x1:
                        maxX = x1
                    if width - margin > x2 and maxX < x2:
                        maxX = x2
        # print('min line %d -- max line %d' % (minX, maxX))

        y, h = getGoogleOutline(rotatedimg)
        minY = y - 50
        if minY < 0:
            minY = 0

        if abs(maxX - minX) < 1000:
            minX = 0
        else:
            width = minX + (maxX - minX)

        crop = rotatedimg[minY:y + h, minX:width]

        return crop
    except Exception as e:
        print(e)

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


    # print(docTopType, docType)

    # Y축 데이터 X축 데이터 추출
    # ocrData = compareLabel(ocrData)
    # ocrData = extractCNNData(ocrData)
    
    # label 추출 MS ML 호출
    # labelData = findColByML(ocrData)
    # entry 추출
    # entryData = findColByML(ocrData)

    # 업체명,사업자번호,주소,전화 입력
    ocrData = companyInfoInsert(ocrData, docTopType, docType)

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
                    word_text = ''
                    for symbol in word.symbols:
                        if symbol.confidence > 0.25:
                            word_text += symbol.text
                        # else:
                        #     print(symbol.text , "confidence : ", symbol.confidence)
                    word_text = word_text.replace('"','')
                    x = word.bounding_box.vertices[0].x
                    y = word.bounding_box.vertices[0].y

                    width = int(word.bounding_box.vertices[1].x) - int(word.bounding_box.vertices[0].x)
                    height = int(word.bounding_box.vertices[3].y) - int(word.bounding_box.vertices[0].y)

                    location = str(x) + ',' + str(y) + ',' + str(width) + ',' + str(height)
                    if x > 0 and y > 0 and word_text != "":
                        ocrData.append({"location": location, "text":word_text})

                    # print('Word text: {}, location:{},{},{},{}'.format(word_text, x, y, width, height))
                    # print('Word text: {}, location:{}'.format(word_text, word.bounding_box.vertices))

    # print('--------------------origin---------------------')
    # for data in ocrData:
    #     print(data)

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
                if isCombiend < 12:
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
def extractSameLine(sourceItem, targetarr, yInterval):
    try:
        dictArr = []
        sourceItemLoc = list(map(int, sourceItem["location"].split(',')) )
        starty = sourceItemLoc[1] - yInterval
        endy = sourceItemLoc[1] + yInterval
        for targetitem in targetarr:
            if targetitem["text"] != "" and sourceItem["location"] != targetitem["location"]:
                targetItemLoc = list(map(int, targetitem["location"].split(',')))
                if starty < targetItemLoc[1] and endy > targetItemLoc[1]:
                    dictArr.append(targetitem)
        return dictArr

    except Exception as e:
        raise Exception(str(
            {'code': 500, 'message': 'extractSameLine fail', 'error': str(e).replace("'", "").replace('"', '')}))

def mostCloseWordSameLine(base, cadidates):
    try:
        retDict = {}
        baseLoc = list(map(int, base["location"].split(',')))
        min = 10000
        if len(cadidates) != 0:
            for cadidate in cadidates:
                cadidateLoc = list(map(int, cadidate["location"].split(',')))
                dx =  cadidateLoc[0] + 14 - (baseLoc[0] + baseLoc[2])
                if dx > 0:
                    dy = abs(baseLoc[1] - cadidateLoc[1])
                    dist = math.sqrt( math.pow(dx, 2) + math.pow(dy, 2))
                    if dist < min:
                        min = dist;
                        retDict = cadidate

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
def combiendText(ocrItem, combiendData):
    try:
        result = {}
        ocrItemLoc = list(map(int, ocrItem["location"].split(',')))
        combiendDataLoc = list(map(int, combiendData["location"].split(',')))
        location = []
        text = ""

        if ocrItemLoc[0] < combiendDataLoc[0]:
            location.append(ocrItemLoc[0])
            text = ocrItem["text"] + combiendData["text"]
        else:
            location.append(combiendDataLoc[0])
            text = combiendData["text"] + ocrItem["text"]
        if ocrItemLoc[1] < combiendDataLoc[1]:
            location.append(ocrItemLoc[1])
        else:
            location.append(combiendDataLoc[1])

        if ocrItemLoc[0] + ocrItemLoc[2] < combiendDataLoc[0] + combiendDataLoc[2]:
            location.append(combiendDataLoc[0] + combiendDataLoc[2] - location[0])
        else:
            location.append(ocrItemLoc[0] + ocrItemLoc[2] - location[0])
        if ocrItemLoc[1] + ocrItemLoc[3] < combiendDataLoc[1] + combiendDataLoc[3]:
            location.append(combiendDataLoc[1] + combiendDataLoc[3] - location[1])
        else:
            location.append(ocrItemLoc[1] + ocrItemLoc[3] - location[1])


        result["location"] = ",".join(map(str, location))
        result["text"] = text

        return result

    except Exception as e:
        raise Exception(str(
            {'code': 500, 'message': 'combiendText fail', 'error': str(e).replace("'", "").replace('"', '')}))

# 같은 줄에 현재 text와 다음 텍스트가 레이블 문자에 포함하면 합친다.
def combiendLabelText(ocrText, combineText, labelTexts):
    try:
        resultFlag = False
        for i in range(len(labelTexts)):
            if ocrText + combineText in labelTexts[i]:
                resultFlag = True
                break
        return resultFlag

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
        colNum = [765,766]
        labelDatas = []
        ocrDataX = sortArrLocationX(ocrData)
        entryDiffHeight = 130

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
                        regexCheck = labelData[3]

                p = re.compile(regexCheck)

                if entryCheck == 'single':
                    singleExit = False

                    # entryCheck
                    for entryData in ocrDataX:
                        entryLoc = entryData['location'].split(',')

                        # 수평 check and colLbl 보다 오른쪽 check
                        if locationCheck(colLoc[1], entryLoc[1], 35, -50) and locationCheck(colLoc[0], entryLoc[0], 10, -1500) and p.match(entryData['text']):
                            if 'entryLbl' not in entryData and 'colLbl' not in entryData:
                                entryData['mlEntryLbl'] = colData['colLbl']
                                entryData['amount'] = 'single'
                                singleExit = True
                                break

                    if singleExit == True:
                        continue

                    for entryData in ocrData:
                        entryLoc = entryData['location'].split(',')

                        # 수직 check and colLbl 보다 아래 check
                        if verticalCheck(colLoc, entryLoc, 50, -100) and locationCheck(colLoc[1], entryLoc[1], 15, -250) and int(colData['colLbl']) not in colNum and p.match(entryData['text']):
                            if 'entryLbl' not in entryData and 'colLbl' not in entryData:
                                entryData['mlEntryLbl'] = colData['colLbl']
                                entryData['amount'] = 'single'
                                break

                elif entryCheck == 'multi':
                    firstEntry = colData;
                    preEntry = colData

                    # vertical area check
                    plus, minus = verticalAreaSearch(colData, ocrData)

                    for entryData in ocrData:
                        entryLoc = entryData['location'].split(',')

                        if entryVerticalCheck(colLoc, entryLoc, plus, minus) and locationCheck(colLoc[1], entryLoc[1], 15, -2000) and entryHeightCheck(preEntry, entryData, entryDiffHeight) and p.match(entryData['text']):
                            if 'entryLbl' not in entryData and 'colLbl' not in entryData:
                                entryData['mlEntryLbl'] = colData['colLbl']
                                entryData['amount'] = 'multi'
                                preEntry = entryData


        return ocrData
    except Exception as e:
        print(e)

def entryVerticalCheck(lblLoc, entLoc, plus, minus):
    try:
        lblwidthLoc = (int(lblLoc[0]) + (int(lblLoc[0]) + int(lblLoc[2]))) / 2
        entwidthLoc = (int(entLoc[0]) + (int(entLoc[0]) + int(entLoc[2]))) / 2

        if int(lblLoc[0]) + minus < entwidthLoc < int(lblLoc[0]) + int(lblLoc[2]) + plus:
            return True
        else:
            return False

    except Exception as e:
        raise Exception(str({'code': 500, 'message': 'checkVerticalEntry fail',
                             'error': str(e).replace("'", "").replace('"', '')}))

def entryHeightCheck(data1, data2, diffHeight):
    check = False
    data1 = data1['location'].split(',')
    data2 = data2['location'].split(',')
    res = int(data2[1]) - int(data1[1])

    if (res < diffHeight):
        check = True

    return check

def verticalAreaSearch(labelData, ocrData):
    try:
        labelLoc = labelData['location'].split(',')
        colList = []
        for data in ocrData:
            dataLoc = data['location'].split(',')
            if locationCheck(labelLoc[1], dataLoc[1], 18, -18):
                colList.append(data)

        minusTemp = -5000
        plusTemp = 5000
        for col in colList:
            colLoc = col['location'].split(',')
            res1 = (int(colLoc[0]) + int(colLoc[2])) - int(labelLoc[0])
            res2 = int(colLoc[0]) - (int(labelLoc[0]) + int(labelLoc[2]))

            if int(colLoc[0]) + int(colLoc[2]) < int(labelLoc[0]) and res1 > minusTemp:
                minusTemp = res1

            if int(labelLoc[0]) + int(labelLoc[2]) < int(colLoc[0]) and res2 < plusTemp:
                plusTemp = res2

        plus = plusTemp - (plusTemp / 2)
        if minusTemp == -5000:
            minus = -100
        else:
            minus = minusTemp - (minusTemp / 3)

        print(minus, ",", plus)
        return plus, minus
    except Exception as e:
        print(e)

def evaluateLabelMulti(ocrData):
    try:
        labelDatas = []
        delDatas = []
        # ocrData = json.loads('[{"location": "1289,1409,195,38", "text": "슬럼프또는"},{"location": "382,1410,336,54", "text": "콘크리트의종류에"},{"location": "718,1410,168,54", "text": "굵은골재"},{"location": "886,1410,126,54", "text": "의최대"},{"location": "1075,1410,148,39", "text": "호칭강도"},{"location": "1617,1426,231,39", "text": "시멘트 종류에"},{"location": "1289,1455,194,38", "text": "슬럼프 플로"},{"location": "740,1457,280,38", "text": "치수에따른구분"},{"location": "1649,1489,170,38", "text": "따른 구분"},{"location": "440,1493,191,38", "text": "따른 구분"}]')
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
                for i in range(10):
                    if labelData[0].lower().find(tempStr.lower()) == 0:
                        # 완전일치 확인
                        if labelData[0].lower() == tempStr.lower() and 'colLbl' not in data:
                            data['colLbl'] = labelData[1]
                            textWidth = 0
                            maxWidth = 0
                            minWidth = 10000
                            for insertData in insertDatas:
                                data['text'] += ' ' + insertData['text']
                                insertDataLoc = insertData['location'].split(',')

                                if int(insertDataLoc[0]) > maxWidth:
                                    maxWidth = int(insertDataLoc[0])

                            print(data['text'])
                            print(maxWidth)
                            if maxWidth != 0:
                                data['location'] = dataLoc[0] + "," + dataLoc[1] + "," + repr(maxWidth - int(dataLoc[0])) + "," + dataLoc[3]

                            for delete in deletes:
                                delDatas.append(delete)

                            break
                        else:
                            # 옆 문장 합쳐서 tempStr에 저장
                            for horiData in ocrDataX:
                                bottomLoc = horiData['location'].split(',')

                                # 수평 check
                                if locationCheck(dataLoc[1], bottomLoc[1], 20, -20) and locationCheck(dataLoc[0],
                                                                                                      bottomLoc[0], 10,
                                                                                                      -1000) and data[
                                    'text'] != horiData['text'] and horiData not in insertDatas:
                                    tempStr += horiData['text'].replace(' ', '')
                                    deletes.append(horiData)
                                    insertDatas.append(horiData)
                                    break
                    else:
                        break

        for data in ocrData:
            text = data['text'].replace(' ', '')
            dataLoc = data['location'].split(',')
            check = False
            # print('00000000', data, '0000000')
            for labelData in labelDatas:
                insertDatas = []
                if labelData[0].lower().find(text.lower()) == 0:
                    for bottomData in ocrData:
                        bottomLoc = bottomData['location'].split(',')

                        if locationCheck(dataLoc[1], bottomLoc[1], 20, -20) and locationCheck(dataLoc[0], bottomLoc[0],
                                                                                              10, -300) and data[
                            'text'] != bottomData['text']:
                            insertDatas.append(bottomData)

                        if verticalCheck(dataLoc, bottomLoc, 90, -200) and locationCheck(dataLoc[1], bottomLoc[1], 0,
                                                                                         -150):
                            insertDatas.append(bottomData)

                tempStr = text

                for i in range(10):
                    # print(i, ',', labelData[0])
                    textWidth = 0
                    maxWidth = 0

                    for insertData in insertDatas:
                        str = tempStr + insertData['text'].replace(' ', '')
                        if labelData[0].lower().find(str.lower()) == 0:
                            tempStr = tempStr + insertData['text'].replace(' ', '')
                            # textWidth 추가
                            insertLoc = insertData['location'].split(',')
                            if int(dataLoc[1]) - int(insertLoc[1]) > -40 and int(insertLoc[2]) > maxWidth:
                                maxWidth = int(insertLoc[2])

                            delDatas.append(insertData)

                        # print(insertData['text'], ',', str)

                        if labelData[0].lower() == tempStr.lower() and 'colLbl' not in data:
                            data['colLbl'] = labelData[1]
                            data['text'] = tempStr
                            if maxWidth != 0:
                                data['location'] = dataLoc[0] + "," + dataLoc[1] + "," + repr(maxWidth - int(dataLoc[0])) + "," + dataLoc[3]
                            check = True
                            break

                    if check == True:
                        break

                if check == True:
                    check = False
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
        pages = convert_from_path(upload_path + pdf_file, dpi=500, output_folder=None, first_page=None,
                                  last_page=None,
                                  fmt='ppm', thread_count=1, userpw=None, use_cropbox=False, strict=False,
                                  transparent=False)
        pdf_file = pdf_file[:-4]  # 업로드 파일명
        filenames = []
        for page in pages:
            filename = "%s-%d.jpg" % (pdf_file, pages.index(page))
            print('filename===>' + filename)
            page.save(upload_path + filename, "JPEG", dpi=(500,500))
            page.save(upload_path + "org_" + filename, "JPEG", dpi=(300,300))
            img = imgResize4200(cv.imread(upload_path + filename))
            cv.imwrite(upload_path + filename, img)
            filenames.append(filename)
        return filenames
    except Exception as e:
        print(e)

def imgResize(img):
    try:
        FIX_LONG = 2970
        FIX_SHORT = 2100
        img = cv.resize(img, dsize=(FIX_SHORT, FIX_LONG), interpolation=cv.INTER_LINEAR)

        return img
    except Exception as ex:
        raise Exception(
            str({'code': 500, 'message': 'imgResize error', 'error': str(ex).replace("'", "").replace('"', '')}))


def imgResize4200(img):
    try:
        FIX_LONG = 4200
        FIX_SHORT = 4200
        img = cv.resize(img, dsize=(FIX_SHORT, FIX_LONG), interpolation=cv.INTER_LINEAR)

        return img
    except Exception as ex:
        raise Exception(
            str({'code': 500, 'message': 'imgResize error', 'error': str(ex).replace("'", "").replace('"', '')}))

def imgResize_old(filename):
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
        data = ocrParsingOne(data)
        conn.close()

        return data
    except Exception as e:
        print("[Errno {0}] {1}".format(e.errno, e.strerror))

def ocrParsingOne(body):
    data = []
    for i in body["regions"]:
        for j in i["lines"]:
            for k in j["words"]:
                data.append({"location":k["boundingBox"], "text":k['text']})
    return data

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

def findDocTopType(ocrData):
    try:
        file = open('docTopType.txt', 'r', encoding="UTF8")
        docList = []
        res = 0

        for line in file:
            label, docTopType = line.strip().split("||")
            dic = {}
            dic['label'] = label
            dic['docTopType'] = docTopType
            dic['count'] = 0
            docList.append(dic)
        file.close()

        temp = 0

        for doc in docList:
            labelLists = doc['label'].split(',')

            for data in ocrData:
                for labelList in labelLists:
                    if 'colLbl' in data and labelList == data['colLbl']:
                        doc['count'] = 1 + doc['count']


            rate = doc['count'] / len(doc['label'])

            if temp < rate:
                temp = rate
                res = doc['docTopType']

        return res

    except Exception as ex:
        raise Exception(str({'code': 500, 'message': 'findDocTopType error', 'error': str(ex).replace("'", "").replace('"', '')}))

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

        cnt = 0
        
        #for i, item in enumerate(ocrData):
        #   if (re.sub(regExp, "", item["text"]) != ""):
        #        text.append(re.sub(regExp, "", item["text"]))
        #        strText = ",".join(str(x) for x in text)
        #        if (cnt == 20):
        #            break        
	
        for i, item in enumerate(ocrData):
            text.append(re.sub(regExp, "", item["text"]))
            strText = ",".join(str(x) for x in text)
            if i == 99:
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
    data = {

        "Inputs": {

            "input1":
                {
                    "ColumnNames": ["age", "workclass", "fnlwgt", "education", "education-num", "marital-status", "occupation", "relationship", "race", "sex", "capital-gain", "capital-loss", "hours-per-week", "native-country"],
                    "Values": [["0", "value", "0", "value", "0", "value", "value", "value", "value", "value", "0", "0", "0", "value"], ["0", "value", "0", "value", "0", "value", "value", "value", "value", "value", "0", "0", "0", "value"], ]
                }, },
        "GlobalParameters": {
        }
    }

    body = str.encode(json.dumps(data))

    url = 'https://ussouthcentral.services.azureml.net/workspaces/f0f7964960e14b1d9120fba8a7b6b792/services/eeabaa5bf2aa4339a7975744a0c800fd/execute?api-version=2.0&details=true'
    api_key = 'ZnGeAKywPE9J5aonBkBtrHU8qyuGypRMGq3G+8xVNeP1N47uM1VgHS495g8EKl4inLRxy8EX5PBBD8coyYiqqw=='  # Replace this with the API key for the web service
    headers = {'Content-Type': 'application/json', 'Authorization': ('Bearer ' + api_key)}

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
                        if companyName.find(search) == -1:
                            dic["companyName"] = companyName
                        # print(companyRegistNo.find(search))
                        if companyRegistNo.find(search) == -1:
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

            if int(docTopType) == 61:
                if "companyName" in rows:
                    obj = {}
                    obj["entryLbl"] = "853"
                    obj["location"] = rows["companyName"].split("@@")[1]
                    obj["text"] = rows["companyName"].split("@@")[0]
                    ocrData.append(obj)
        # print(ocrData)
        return ocrData

    except Exception as ex:
        raise Exception(str(
            {'code': 500, 'message': 'companyInfoInsert error', 'error': str(ex).replace("'", "").replace('"', '')}))

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)