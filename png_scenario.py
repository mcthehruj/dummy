import numpy as np
import binascii
import utils_tiff_png as utils
import zlib
import struct
import os
import shutil
import cv2
from brisque.brisque import BRISQUE
import sys
import JPEG
import random


def I4(value):
    return struct.pack("!I", value & (2 ** 32 - 1))


def Distortion(filename, new_stream=b'\x9d\xe5', new_stream_2nd=b'\x8c\xd4'):
    f = open(filename, 'rb')
    png_bytes = f.read()

    case_list = [
        [0, 1],
        [1, 0],
        [1, 1]
    ]

    marker_IDAT = b'\x49\x44\x41\x54'
    loc_IDAT = utils.Find_Marker(png_bytes, marker_IDAT)
    IDAT_chunk_length = int.from_bytes(png_bytes[loc_IDAT[0] - 4:loc_IDAT[0]], 'big')

    case = case_list[random.randint(0, 2)]
    check_stream = b'\xaa\xbb\xcc\xdd'
    png_bytes = bytes.fromhex(png_bytes.hex() + check_stream.hex())
    ## modify chunk value : png byte stream / new stream / modifying location
    if case[0] == 0:
        dummy_stream = b'\x4d\x3e'
        fixed, orig_stream = utils.Fix_Byte_Stream_v2(png_bytes, new_stream_2nd, loc_IDAT[0] + 50)

        fixed = bytes.fromhex(fixed.hex() + dummy_stream.hex())
        fixed = bytes.fromhex(fixed.hex() + orig_stream.hex())

    elif case[0] == 1:
        fixed, orig_stream = utils.Fix_Byte_Stream_v2(png_bytes, new_stream, loc_IDAT[0] + 20)
        fixed = bytes.fromhex(fixed.hex() + orig_stream.hex())
        # orig_stream = binascii.hexlify(orig_stream)
        if case[1] == 1:
            fixed, orig_stream = utils.Fix_Byte_Stream_v2(fixed, new_stream_2nd, loc_IDAT[0] + 50)
            fixed = bytes.fromhex(fixed.hex() + orig_stream.hex())
        else:
            dummy_stream_2nd = b'\x2a\x5f'
            fixed = bytes.fromhex(fixed.hex() + dummy_stream_2nd.hex())

    ## modify crc
    modified_IDAT = fixed[loc_IDAT[0]:loc_IDAT[0] + IDAT_chunk_length + 4]
    modified_IDAT_crc = I4(zlib.crc32(modified_IDAT))
    modulated, orig_crc = utils.Fix_Byte_Stream_v2(fixed, modified_IDAT_crc, loc_IDAT[0] + IDAT_chunk_length + 4)

    JPEG.Write_bin(filename.replace('.png', '_Distorted.png'), modulated)
    # return modulated


def Restoration(filename):
    brisque = BRISQUE()
    case_list = [
        [0, 0],
        [0, 1],
        [1, 0],
        [1, 1]
    ]

    fp = open(filename, 'rb')
    png_bytes = fp.read()

    orig_streams = png_bytes[-8:].hex()
    orig_stream_1st = binascii.unhexlify(orig_streams[-8:-4])
    orig_stream_2nd = binascii.unhexlify(orig_streams[-4:])

    marker_IDAT = b'\x49\x44\x41\x54'
    loc_IDAT = utils.Find_Marker(png_bytes, marker_IDAT)
    IDAT_chunk_length = int.from_bytes(png_bytes[loc_IDAT[0] - 4:loc_IDAT[0]], 'big')

    ## modify chunk value
    for case_idx, case in enumerate(case_list):

        if case_idx == 0:
            f = open(filename, 'rb')
            fixed = f.read()
            f.close()

            ## modify crc
            modified_IDAT = fixed[loc_IDAT[0]:loc_IDAT[0] + IDAT_chunk_length + 4]
            modified_IDAT_crc = I4(zlib.crc32(modified_IDAT))
            restored, _ = utils.Fix_Byte_Stream_v2(fixed, modified_IDAT_crc, loc_IDAT[0] + IDAT_chunk_length + 4)

            with open('tmp/Candidates_{}.png'.format(case_idx), 'wb') as f:
                f.write(restored)

        if case_idx == 1:
            f = open(filename, 'rb')
            fixed = f.read()
            f.close()

            fixed, _ = utils.Fix_Byte_Stream_v2(fixed, orig_stream_2nd, loc_IDAT[0] + 50)
            ## modify crc
            modified_IDAT = fixed[loc_IDAT[0]:loc_IDAT[0] + IDAT_chunk_length + 4]
            modified_IDAT_crc = I4(zlib.crc32(modified_IDAT))
            restored, _ = utils.Fix_Byte_Stream_v2(fixed, modified_IDAT_crc, loc_IDAT[0] + IDAT_chunk_length + 4)

            with open('tmp/Candidates_{}.png'.format(case_idx), 'wb') as f:
                f.write(restored)

        if case_idx == 2:
            f = open(filename, 'rb')
            fixed = f.read()
            f.close()

            fixed, _ = utils.Fix_Byte_Stream_v2(fixed, orig_stream_1st, loc_IDAT[0] + 20)
            ## modify crc
            modified_IDAT = fixed[loc_IDAT[0]:loc_IDAT[0] + IDAT_chunk_length + 4]
            modified_IDAT_crc = I4(zlib.crc32(modified_IDAT))
            restored, _ = utils.Fix_Byte_Stream_v2(fixed, modified_IDAT_crc, loc_IDAT[0] + IDAT_chunk_length + 4)

            with open('tmp/Candidates_{}.png'.format(case_idx), 'wb') as f:
                f.write(restored)

        if case_idx == 3:
            f = open(filename, 'rb')
            fixed = f.read()
            f.close()

            fixed, _ = utils.Fix_Byte_Stream_v2(fixed, orig_stream_1st, loc_IDAT[0] + 20)
            fixed, _ = utils.Fix_Byte_Stream_v2(fixed, orig_stream_2nd, loc_IDAT[0] + 50)
            ## modify crc
            modified_IDAT = fixed[loc_IDAT[0]:loc_IDAT[0] + IDAT_chunk_length + 4]
            modified_IDAT_crc = I4(zlib.crc32(modified_IDAT))
            restored, _ = utils.Fix_Byte_Stream_v2(fixed, modified_IDAT_crc, loc_IDAT[0] + IDAT_chunk_length + 4)

            with open('tmp/Candidates_{}.png'.format(case_idx), 'wb') as f:
                f.write(restored)

    # scoring
    score_list = []

    for i in range(1, 5):
        try:
            if ext == '.png':
                img = cv2.imread('tmp/Candidates_{}.png'.format(i), 0)  # read as gray scale
            if img is None:
                score_list.append(99999)
            else:
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
    # shutil.copy('tmp/Candidates_%d%s' % (restore_idx+1, ext), filename.replace('_Distorted', '_Restored'))
    shutil.copy('tmp/Candidates_%d.png' % (restore_idx+1), filename.replace('_Distorted', '_Restored'))

    # for r in range(4):
    #     os.remove('tmp/candidate_{}.png'.format(r))
    # os.remove('tmp/orig_streams.txt'.format())


def Check(filename):
    fp = open(filename, 'rb')
    png_bytes = fp.read()

    check_stream = png_bytes[-8:-4]
    if check_stream == b'\xaa\xbb\xcc\xdd':
        return 1
    else:
        return 0


if __name__ == "__main__":
    fn, ext = os.path.splitext(sys.argv[1])

    if ext in ['.png']:

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