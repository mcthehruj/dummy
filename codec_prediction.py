import os
import tkinter.messagebox
from tkinter.filedialog import askopenfilename
from tkinter import *
from tkinter.ttk import *
import subprocess

import PIL.Image
import PIL.ImageTk
import cv2
from utils import *

# 딥러닝 네트워크 불러오는 과정 코드들 codec_prediction.py로 정리함

# 메인 함수
if __name__ == "__main__":          #def sangmin_deep_predict(mode, src):
    if (len(sys.argv) == 2):
        src = sys.argv[1]
        print('딥네트워크 코덱 식별중..', 'cuda' if torch.cuda.is_available() else 'cpu', '환경')
        #print('코덱 판별중..')  # 코덱분류
        video = bitstring.ConstBitStream(filename=src)
        video = video.read(video.length).bin
        video = bitstring.BitStream('0b' + video)                           #video.tofile(open('decoded' + name[1], 'wb'))
        frequency = codec_decide(video)
        print('top-1 codec is ', codec[frequency.index(max(frequency))])
        print('{MPG2 H263 H264 H265  IVC  VP8 JPEG JP2K  BMP  PNG TIFF}')
        print('{', end='')
        for i, a in enumerate(frequency): print('%4d' % a, end=''); print(',', end='') if i != len(frequency)-1 else None
        print('}')

        # print('변형 시나리오 예측중..')
        # detected_scenario, video = scenario_detect(frequency, video, count)    # 'default', 'inverse', 'xor'
        # print('변형 시나리오는 %s 입니다.' % scenario_list[detected_scenario])


        sys.exit(0)

    if (len(sys.argv) != 2):
        print('입력 인자 오류')