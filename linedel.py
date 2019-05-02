"""
@file morph_lines_detection.py
@brief Use morphology transformations for extracting horizontal and vertical lines sample code
"""
import numpy as np
import sys
import cv2 as cv
import base64
import os

#지워야할 수평 선의 두께
deleteHorizontalLineWeight = 3
#지워야할 수직 선의 두께
deleteVerticalLineWeight = 3

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

def show_wait_destroy(winname, img):
    cv.imshow(winname, cv.resize(img, None, fx=0.25, fy=0.25, interpolation=cv.INTER_AREA))
    cv.moveWindow(winname, 500, 0)
    cv.resizeWindow(winname, 1200, 1200)
    cv.waitKey(0)
    cv.destroyWindow(winname)


def main(argv):
    # [load_image]
    if len(argv) < 1:
        print ('Not enough parameters')
        print ('Usage:\nmorph_lines_detection.py < path_to_image >')
        return -1
    # print(argv[0])
    argv = base64.b64decode(argv).decode("utf-8")
    # Load the image
    src = imread(argv)
    # Check if image is loaded fine
    if src is None:
        print ('Error opening image: ' + argv)
        return -1

    #컬러 이미지 흑백 처리
    if len(src.shape) != 2:
        gray = cv.cvtColor(src, cv.COLOR_BGR2GRAY)
    else:
        gray = src

    # otsu 알고리즘 노이즈 제거 처리
    img_blur = cv.GaussianBlur(gray, (5, 5), 0)
    ret, horizontal = cv.threshold(img_blur, 0, 255, cv.THRESH_BINARY + cv.THRESH_OTSU)
    # show_wait_destroy("horizontal1", horizontal)

    #흑백 이미지 이진화 처리
    horizontal = cv.bitwise_not(horizontal)
    horizontal = cv.adaptiveThreshold(horizontal, 255, cv.ADAPTIVE_THRESH_MEAN_C, cv.THRESH_BINARY, 9, -2)

    # show_wait_destroy("horizontal1", horizontal)

    horizontal = np.copy(horizontal)
    vertical = np.copy(horizontal)

    cols = horizontal.shape[1]
    horizontal_size = cols / 20

    horizontalStructure = cv.getStructuringElement(cv.MORPH_RECT, (int(horizontal_size), 1))
    horizontalDilateStructure = cv.getStructuringElement(cv.MORPH_RECT, (int(horizontal_size), deleteHorizontalLineWeight))

    horizontal2 = cv.erode(horizontal, horizontalStructure)
    horizontal2 = cv.dilate(horizontal2, horizontalDilateStructure)
    # show_wait_destroy("horizontal1", horizontal2)
    horizontal = cv.bitwise_not(horizontal)
    horizontal = cv.add(gray, horizontal2)
    # show_wait_destroy("horizontal1", horizontal)
    rows = vertical.shape[0]
    verticalsize = rows / 20

    verticalStructure = cv.getStructuringElement(cv.MORPH_RECT, (1, int(verticalsize)))
    verticalDilateStructure = cv.getStructuringElement(cv.MORPH_RECT, (deleteVerticalLineWeight, int(horizontal_size)))

    vertical = cv.erode(vertical, verticalStructure)
    vertical = cv.dilate(vertical, verticalDilateStructure)
    horizontal = cv.add(horizontal, vertical)

    imwrite(argv, horizontal)
    # print("fileConvert Success")
    return 0
if __name__ == "__main__":
    main(sys.argv[1:])