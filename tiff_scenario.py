import cv2
import utils_tiff_png as utils
import numpy as np
import os
import random
from brisque.brisque import BRISQUE
import sys
import JPEG
import shutil

byte_comp_type={
    b'\x05\x80': 1,  # packbits
    b'\x01\x00': 2,  # none
    b'\x05\x00': 3,  # lzw
    b'\x08\x00': 4   # deflate
    }

def Distortion(filename):
    with open(filename, 'rb') as b:
        bdata = b.read()

    marker = b'\x03\x01\x03\x00\x01\x00\x00\x00'
    loc = utils.Find_Marker(bdata, marker)
    compression_byte = bdata[loc[0] + 8:loc[0] + 10]

    input_compression = byte_comp_type[compression_byte]

    distortion_val = [hex(0)[2:] + hex(1408)[2:],  # packbits
                      hex(0)[2:] + hex(1)[2:] + hex(0)[2:] + hex(0)[2:],  # none
                      hex(0)[2:] + hex(5)[2:] + hex(0)[2:] + hex(0)[2:],  # lzw
                      hex(0)[2:] + hex(8)[2:] + hex(0)[2:] + hex(0)[2:]]  # deflate

    distortion_index = input_compression - 1
    while distortion_index == input_compression - 1:
        distortion_index = random.randint(0, 3)

    modulated = utils.Fix_Byte_Stream(bdata, distortion_val[distortion_index], loc[0])
    JPEG.Write_bin(filename.replace('.tiff', '_Distorted.tiff'), modulated)

    # return modulated


def Restoration(fn):
    if not os.path.exists('tmp'):
        os.mkdir('tmp')

    brisque = BRISQUE()

    ext = os.path.splitext(fn)[1]
    current_bin = JPEG.Load_bin(fn)
    if ext == '.tiff':
        Candidate_TIFF(current_bin)

    score_list = []

    for i in range(1, 5):
        try:
            if ext == '.tiff':
                img = cv2.imread('tmp/Candidates_%d.tiff' % (i), 0)
            if img is None:
                score_list.append(99999)
            else:
                img = cv2.equalizeHist(img)
                score_list.append(np.nan_to_num(brisque.get_score(img)))
        except:
            score_list.append(99999)

    score_threshold = 0
    for i in score_list:
        if i == 0:
            score_threshold += 1

    score_min = np.argmin(score_list)
    while score_threshold != 0:
        score_list[score_min] = 9999
        score_min = np.argmin(score_list)
        score_threshold -= 1

    restore_idx = np.argmin(score_list)
    shutil.copy('tmp/Candidates_%d%s' % (restore_idx+1, ext), fn.replace('_Distorted', '_Restored'))


def Candidate_TIFF(Bin_TIFF):
    marker = b'\x03\x01\x03\x00\x01\x00\x00\x00'
    loc = utils.Find_Marker(Bin_TIFF, marker)

    distortion_val = [hex(0)[2:] + hex(1408)[2:],  # packbits
                      hex(0)[2:] + hex(1)[2:] + hex(0)[2:] + hex(0)[2:],  # none
                      hex(0)[2:] + hex(5)[2:] + hex(0)[2:] + hex(0)[2:],  # lzw
                      hex(0)[2:] + hex(8)[2:] + hex(0)[2:] + hex(0)[2:]]  # deflate
    for dist in range(4):
        fixed = utils.Fix_Byte_Stream(Bin_TIFF, distortion_val[dist], loc[0])
        with open('tmp/Candidates_{}.tiff'.format(dist+1), 'wb') as f:
            f.write(fixed)

def Check(fn):
    if not os.path.exists('tmp'):
        os.mkdir('tmp')

    brisque = BRISQUE()

    ext = os.path.splitext(fn)[1]
    current_bin = JPEG.Load_bin(fn)
    if ext == '.tiff':
        Candidate_TIFF(current_bin)

    score_list = []

    for i in range(1, 5):
        try:
            if ext == '.tiff':
                img = cv2.imread('tmp/Candidates_%d.tiff' % (i))
                score_list.append(brisque.get_score(img))
        except:
            score_list.append(99999)

    if min(score_list) > 150:
        return 0
    else:
        return 1


if __name__ == "__main__":
    fn, ext = os.path.splitext(sys.argv[1])
    if ext in ['.tiff']:

        mode = sys.argv[2]
        if mode == '0':
            Distortion(sys.argv[1])
        elif mode == '1':
            Restoration(sys.argv[1])
        elif mode == '2':
            check_flag = Check(sys.argv[1])
            if check_flag == 0:
                raise ValueError()
        else:
            raise ValueError('Only [0, 1, 2] for mode argument')
    else:
        raise ValueError()