import utils_tiff_png as utils
import numpy as np
import cv2
from brisque.brisque import BRISQUE
import os
import random
import JPEG
import sys
import shutil


def Distortion(filename):
    with open(filename, 'rb') as b:
        bmp_bytes = b.read()

    BMP_header_chunk_length = 14

    biWidth = bmp_bytes[BMP_header_chunk_length + 4:BMP_header_chunk_length + 8]
    biHeight = bmp_bytes[BMP_header_chunk_length + 8:BMP_header_chunk_length + 12]

    biWidth_int = int.from_bytes(biWidth, 'little')
    biHeight_int = int.from_bytes(biHeight, 'little')

    candidates = [200, 300, 400, 500]

    candidate_res = candidates[random.randint(0, 3)]
    modified_biWidth = int(biWidth_int + candidate_res).to_bytes(2, byteorder='little')
    modified_biHeight = int(biHeight_int + candidate_res).to_bytes(2, byteorder='little')

    modulated, _ = utils.Fix_Byte_Stream_v2(bmp_bytes, modified_biWidth, BMP_header_chunk_length + 4)
    modulated, _ = utils.Fix_Byte_Stream_v2(modulated, modified_biHeight, BMP_header_chunk_length + 8)

    JPEG.Write_bin(filename.replace('.bmp', '_Distorted.bmp'), modulated)

    # return modulated

def Candidate_BMP(Bin_BMP):
    candidates = [200, 300, 400, 500]

    BMP_header_chunk_length = 14

    biWidth = Bin_BMP[BMP_header_chunk_length + 4:BMP_header_chunk_length + 8]
    biHeight = Bin_BMP[BMP_header_chunk_length + 8:BMP_header_chunk_length + 12]

    biWidth_int = int.from_bytes(biWidth, 'little')
    biHeight_int = int.from_bytes(biHeight, 'little')

    for idx, candidate in enumerate(candidates):
        if (biWidth_int - candidate <= 0) or (biHeight_int - candidate <= 0):
            with open('tmp/Candidates_{}.bmp'.format(idx+1), 'wb') as f:
                f.write(Bin_BMP)
        else:
            biWidth_candidate = int(biWidth_int - candidate).to_bytes(2, byteorder='little')
            biHeight_candidate = int(biHeight_int - candidate).to_bytes(2, byteorder='little')
            fixed, _ = utils.Fix_Byte_Stream_v2(Bin_BMP, biWidth_candidate, BMP_header_chunk_length + 4)
            fixed, _ = utils.Fix_Byte_Stream_v2(fixed, biHeight_candidate, BMP_header_chunk_length + 8)
            with open('tmp/Candidates_{}.bmp'.format(idx+1), 'wb') as f:
                f.write(fixed)


def Restoration(fn):
    if not os.path.exists('tmp'):
        os.mkdir('tmp')

    brisque = BRISQUE()

    ext = os.path.splitext(fn)[1]
    current_bin = JPEG.Load_bin(fn)
    if ext == '.bmp':
        Candidate_BMP(current_bin)

    score_list = []

    for i in range(1, 5):
        if ext == '.bmp':
            img = cv2.imread('tmp/Candidates_%d.bmp' % (i), 0)
        if img is None:
            score_list.append(99999)
        else:
            img = cv2.equalizeHist(img)
            score_list.append(np.nan_to_num(brisque.get_score(img)))

    # print(score_list)
    restore_idx = np.argmin(score_list)

    shutil.copy('tmp/Candidates_%d%s' % (restore_idx+1, ext), fn.replace('_Distorted', '_Restored'))


def Check(fn):
    if not os.path.exists('tmp'):
        os.mkdir('tmp')

    brisque = BRISQUE()

    ext = os.path.splitext(fn)[1]
    current_bin = JPEG.Load_bin(fn)
    if ext == '.bmp':
        Candidate_BMP(current_bin)

    score_list = []

    for i in range(1, 5):
        try:
            if ext == '.bmp':
                img = cv2.imread('tmp/Candidates_%d.bmp' % (i))
            score_list.append(brisque.get_score(img))
        except:
            score_list.append(99999)

    if min(score_list) > 150:
        return 0
    else:
        return 1


if __name__ == "__main__":
    fn, ext = os.path.splitext(sys.argv[1])
    if ext in ['.bmp']:

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