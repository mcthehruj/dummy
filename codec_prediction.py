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
        print('running with', 'cuda' if torch.cuda.is_available() else 'cpu', 'environments')
        print('코덱 판별중..')  # 코덱분류
        video = bitstring.ConstBitStream(filename=src)
        video = video.read(video.length).bin
        count = factor(len(video))
        video = bitstring.BitStream('0b' + video)                           #video.tofile(open('decoded' + name[1], 'wb'))
        frequency_image = codec_decide(video, 'image')
        frequency_video = codec_decide(video, 'video')
        if frequency_video.index(max(frequency_video)) in [2, 3, 4, 10]:
            frequency = frequency_video                                     # 면밀한 분류를 하는 것이 중요한 비디오 분류
            # 2: H.264 정확도 보완
            # 3, 10: H.265 정확도 보완
            # 4: IVC 정확도 보완
        elif frequency_image.index(max(frequency_image)) in [1, 6, 8]:
            frequency = frequency_image                                     # 부족한 정보를 채우는 것이 중요한 이미지 분류
            # 1: JPEG 정확도 보완
            # 6: TIFF 정확도 보완
            # 8: BMP 정확도 보완
        else:
            frequency = frequency_video
            # JPEG 2000 보완, video 버전이 image 버전보다 상대적으로 정확하다
        print(codec[frequency.index(max(frequency))])
        print('변형 시나리오 예측중..')
        detected_scenario, video = scenario_detect(frequency, video, count)
        # 'default', 'inverse', 'xor'
        print('변형 시나리오는 %s 입니다.' % scenario_list[detected_scenario])
        # MPEG2 H.263 H.264 H.265 IVC VP8 JPEG JPEG2000 BMP PNG TIFF

    if (len(sys.argv) != 2):
        print('입력 인자 오류')
