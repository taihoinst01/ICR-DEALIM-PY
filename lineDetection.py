import cv2 as cv
import numpy as np
# from math import atan2, pi
import base64
import sys
import os
import math
from scipy import ndimage
import matplotlib.pyplot as plt
from PIL import Image as im
from scipy.ndimage import interpolation as inter
from google.cloud import vision

def imread(filename, flags=cv.IMREAD_COLOR, dtype=np.uint8):
    try:
        n = np.fromfile(filename, dtype)
        img = cv.imdecode(n, flags)
        return img
    except Exception as e:
        print(e)
        return None

def imwrite(filename, img, params=None):
    try:
        ext = os.path.splitext(filename)[1]
        result, n = cv.imencode(ext, img, params)

        if result:
            with open(filename, mode='w+b') as f:
                n.tofile(f)
            return True
        else:
            return False
    except Exception as e:
        print(e)
        return False

def find_score(arr, angle):
    data = inter.rotate(arr, angle, reshape=False, order=0)
    hist = np.sum(data, axis=1)
    score = np.sum((hist[1:] - hist[:-1]) ** 2)
    return hist, score

def angle_rotation(filename):
    # 기울기 보정
    image = cv.imread(filename)

    img = im.open(filename)
    # img2 = img
    wd, ht = img.size
    pix = np.array(img.convert('1').getdata(), np.uint8)
    bin_img = 1 - (pix.reshape((ht, wd)) / 255.0)
    #plt.imshow(bin_img, cmap='gray')
    # plt.savefig(filename)

    delta = 0.5
    limit = 5
    angles = np.arange(-limit, limit + delta, delta)
    scores = []
    for angle in angles:
        hist, score = find_score(bin_img, angle)
        scores.append(score)

    best_score = max(scores)
    best_angle = angles[scores.index(best_score)]
    print('Best angle: {}'.format(best_angle))

    (h, w) = image.shape[:2]
    center = (w // 2, h // 2)
    if(best_angle == 1):
        best_angle = best_angle * 0.6
    elif(best_angle == 2):
        best_angle = 2.9

    M = cv.getRotationMatrix2D(center, best_angle, 1.0)
    rotated = cv.warpAffine(image, M, (w, h),
                             flags=cv.INTER_CUBIC, borderMode=cv.BORDER_REPLICATE)
    return rotated

def get_croped(rotated):
    #이미지 여백 크롭
    #rsz_img = cv.resize(rotated, None, fx=0.25, fy=0.25)  # resize since image is huge

    gray = cv.cvtColor(rotated, cv.COLOR_BGR2GRAY)  # convert to grayscale

    # gray = cv.GaussianBlur(gray, (5, 5), 0)
    # cv.imshow("Cropped and thresholded image", gray)
    # cv.waitKey(0)
    ret, gray = cv.threshold(gray, 0, 255, cv.THRESH_BINARY + cv.THRESH_OTSU)
    #cv.imshow("Cropped and thresholded image", cv.resize(gray, None, fx=0.15, fy=0.15))
    #cv.waitKey(0)


    #retval, thresh_crop = cv.threshold(horizontal, thresh=200, maxval=255, type=cv.THRESH_BINARY)
    #cv.imshow("Cropped and thresholded image", thresh_crop)
    #cv.waitKey(0)

    # 원본 이미지 사이즈 추출
    x, y, w, h = cv.boundingRect(gray)  # create a rectangle around those points
    x, y, w, h = x + 30, y + 30, w - 30, h - 40  # make the box a little bigger
    # x, y, w, h = x + 30, y + 30, w - 30, h - 40  # make the box a little bigger
    # 상하좌우 일정 부분 크롭
    gray = gray[y:y + h, x:x + w]  # create a cropped region of the gray image
    #x, y, w, h = x + 120, y + 120, w - 120, h - 160 # make the a little bigger
    rotated = rotated[y:y + h, x:x + w]  # create a cropped region of the gray image

    #cv.imshow("Cropped and thresholded image", gray)
    #cv.waitKey(0)
    # threshold to get just the signature
    # 70 진한 검은색 60 더 검은색
    retval, thresh_gray = cv.threshold(gray, thresh=110, maxval=255, type=cv.THRESH_BINARY)
    thresh_gray = cv.GaussianBlur(thresh_gray, (5, 5), 0)
    cv.imwrite("/home/daerimicr/icrRest/uploads/test.jpg", thresh_gray)
    #cv.imshow("Cropped and thresholded image", cv.resize(thresh_gray, None, fx=0.15, fy=0.15))
    #cv.waitKey(0)
    # find where the signature is and make a cropped region
    points = np.argwhere(thresh_gray == 0)  # find where the black pixels are
    points = np.fliplr(points)  # store them in x,y coordinates instead of row,col indices
    x, y, w, h = cv.boundingRect(points)  # create a rectangle around those points
    print(x, y, w, h)
    #x, y, w, h = x-10, y-10, w+20, h+20 # make the box a little bigger
    # 상하좌우 여백 크롭
    crop = rotated[y:y + h, x:x + w]  # create a cropped region of the gray image
    #cv.imshow("Cropped and thresholded image", cv.resize(crop, None, fx=0.15, fy=0.15))
    #cv.waitKey(0)
    #cv.imshow("Cropped and thresholded image", crop)
    #cv.waitKey(0)
    #retval, thresh_crop = cv.threshold(crop, thresh=200, maxval=255, type=cv.THRESH_BINARY)

    #thresh_crop = lineDel.main(thresh_crop)
    return crop


def getRotateImage(item):

    client = vision.ImageAnnotatorClient()
    success, encoded_image = cv.imencode('.jpg', item)
    content = encoded_image.tobytes()

    image = vision.types.Image(content=content)

    response = client.document_text_detection(image=image)
    # content = encoded_image.tobytes()

    mydegrees = getAngleFromGoogle(response)
    print(mydegrees)
    # image = cv.imread(item)

    (h, w) = item.shape[:2]
    center = (w // 2, h // 2)

    M = cv.getRotationMatrix2D(center, mydegrees, 1.0)
    rotated = cv.warpAffine(item, M, (w, h),
                             flags=cv.INTER_CUBIC, borderMode=cv.BORDER_REPLICATE)

    return rotated

def getAngleFromGoogle(response):
    first = []
    last =[]
    maxlen = 0
    for page in response.full_text_annotation.pages:
        for block in page.blocks:
            for paragraph in block.paragraphs:
                for word in paragraph.words:
                    if len(word.symbols) > maxlen:
                        maxlen = len(word.symbols)
                        first = []
                        last = []
                        for symbol in word.symbols:
                            if len(first) == 0:
                                first.append(symbol.bounding_box.vertices[0].x)
                                first.append(symbol.bounding_box.vertices[0].y)
                            last = [symbol.bounding_box.vertices[0].x, symbol.bounding_box.vertices[0].y]

    myradians = math.atan2(first[1] - last[1], first[0] - last[0])
    mydegrees = math.degrees(myradians)
    mydegrees = mydegrees + 180
    return mydegrees

def getOcrInfo(item):
    client = vision.ImageAnnotatorClient()
    # item1 = cv.imread(item)
    success, encoded_image = cv.imencode('.jpg', item)
    content = encoded_image.tobytes()

    image = vision.types.Image(content=content)

    response = client.document_text_detection(image=image)

    # print(response.text_annotations[0])
    x = response.text_annotations[0].bounding_poly.vertices[0].x
    y = response.text_annotations[0].bounding_poly.vertices[0].y
    w = response.text_annotations[0].bounding_poly.vertices[1].x
    h = response.text_annotations[0].bounding_poly.vertices[2].y

    if(x < 0):
        x = 0

    print(x, y, w, h)


    return x, y, w, h

def main(argv):
    argv = base64.b64decode(argv).decode("utf-8")

    imgPre = cv.imread(argv)

    # 기울기 보정
    imgPre = getRotateImage(imgPre)

    (h, w) = imgPre.shape[:2]

    # x, y, w, h = cv.boundingRect(gray)  # create a rectangle around those points
    x, y, w, h = 100,  100, w, h  # make the box a little bigger
    # print(x, y, w, h)
    # 상하좌우 일정 부분 크롭

    rtnImg = imgPre[y:y + h, x:x + w]  # create a cropped region of the gray image

    # 좌표추출
    x, y, w, h = getOcrInfo(rtnImg)
    # getImg = cv.imread(rtnImg)

    # crop
    crop = rtnImg[y:y + h, x:x + w]  # create a cropped region of the gray image
    cv.imwrite(argv, crop)

    # 리사이즈
    # imgResize(crop)

if __name__ == "__main__":
    main(sys.argv[1:])
