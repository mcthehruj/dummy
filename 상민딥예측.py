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

#상민딥 네트워크 불러오는 과정 코드들 상민딥예측.py로 정리함
"""
def detect(text, scenario, index, name):  # 1이 반전, 2가 xor
    text = 0  # 안쓰는 변수

    print_dual(text, '1. preparing trained model for codec classification...')
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model = BiLSTM_Attention()
    model.to(device)
    print_dual(text, '   scenario = ' + str(scenario) + ' index = ' + str(index))
    a = torch.load(glob('Bi-LSTM_96.73.pth')[0])
    model.load_state_dict(a)

    print_dual(text, '2. preparing randomly encoded bitstream...')
    ext = codec_list[index]
    video = bitstring.ConstBitStream(filename=name + ext)
    video.tofile(open('original' + ext, 'wb'))
    video = video.read(video.length).bin
    # original = bitstring.BitStream('0b' + video)
    count = factor(len(video))
    # print(len(video), count)
    if scenario == 1:
        video = encode(video, 'inv')
    elif scenario == 2:
        video = xor_fast(video, count)  # 시나리오에 의한 변조
    elif scenario == 3:
        pass
        # dummy 시나리오 변조 넣기
    video = bitstring.BitStream('0b' + video)
    video.tofile(open("encoded" + ext, 'wb'))

    print_dual(text, '3. testing what the codec of encoded bitstream is...')  # 코덱분류
    video.pos = 0
    frequency = [0] * num_classes  # MPEG-2, H.263, H.264,... 의 예측값의 빈도수를 각각 저장
    limit = (dataset - 1) * shift_bytes_in_a_sentence + all_bytes_in_a_sentence  # 학습시킨 데이터 길이만큼만 검증
    for i in range(limit):
        tt = video.read(all_bytes_in_a_sentence * int(math.log2(16))).hex
        video.pos -= all_bytes_in_a_sentence * int(math.log2(16))
        video.pos += shift_bytes_in_a_sentence * int(math.log2(16))
        predict = test(tt, test_scenario, num_chars_in_a_word, model)
        frequency[predict] += 1

    print_dual(text, '')
    print_dual_nocl(text, frequency)

    print_dual(text, '4. testing what the scenario of encoded bitstream is...')  # 시나리오분류
    detected_scenario, video = scenario_detect(frequency, video, count)
    print_dual(text, '   The scenario for encoding is...')
    print_dual(text, '   %s' % scenario_list[detected_scenario])

    # self.changedvideo(text_1_3, ext ,'e')
    return ext

def detect_inv(text, name):
    text = 0  # 안쓰는 변수

    print_dual(text, 'Decoding process start..')

    print_dual(text, '1. preparing trained model for codec classification...')
    print_dual(text, '   ' + name[0] + name[1])

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model = BiLSTM_Attention()
    model.to(device)
    a = torch.load(glob('Bi-LSTM_96.73.pth')[0])
    model.load_state_dict(a)

    print_dual(text, '2. preparing randomly encoded bitstream...')
    video = bitstring.ConstBitStream(filename=name[0] + name[1])
    video = video.read(video.length).bin
    # original = bitstring.BitStream('0b' + video)
    count = factor(len(video))
    # print(len(video), count)
    video = bitstring.BitStream('0b' + video)
    video.tofile(open('decoded' + name[1], 'wb'))

    print_dual(text, '3. testing what the codec of encoded bitstream is...')  # 코덱분류
    video.pos = 0
    frequency = [0] * num_classes  # MPEG-2, H.263, H.264,... 의 예측값의 빈도수를 각각 저장
    limit = (dataset - 1) * shift_bytes_in_a_sentence + all_bytes_in_a_sentence  # 학습시킨 데이터 길이만큼만 검증
    for i in range(limit):
        tt = video.read(all_bytes_in_a_sentence * int(math.log2(16))).hex
        video.pos -= all_bytes_in_a_sentence * int(math.log2(16))
        video.pos += shift_bytes_in_a_sentence * int(math.log2(16))
        predict = test(tt, test_scenario, num_chars_in_a_word, model)
        frequency[predict] += 1

    print_dual(text, '')
    print_dual_nocl(text, frequency)

    print_dual(text, '4. testing what the scenario of encoded bitstream is...')  # 시나리오분류
    detected_scenario, video = scenario_detect(frequency, video, count)
    print_dual(text, '   The scenario for encoding is...')
    print_dual(scenario_list[detected_scenario])

    return scenario_list[detected_scenario]

    # print_dual(text, '5. reconstructing the encoded bitstream...')
    # ext = self.find_ext2(scenario_list[detected_scenario], True)
    # video = bitstring.BitStream('0b' + video)
    # self.video_source = bin2hex(video)
    # video.tofile(open("reconstructed" + ext, 'wb'))
    # self.changedvideo(text_2_3, ext, 'd')
    # print_dual(text, '   Please compare the reconstructed file with the encoded file!')

def print_dual(text, aa):
    now = datetime.now()
    print('[%d.%02d.%02d %d:%02d:%02d] ' % (now.year, now.month, now.day, now.hour, now.minute, now.second), end='')
    # text.insert(END, '[%d.%02d.%02d %d:%02d:%02d] ' % (now.year, now.month, now.day, now.hour, now.minute, now.second))
    print(aa)
    if aa == '': return;
    # if type(aa) == str: text.insert(END, aa + '\n')
    if type(aa) == list:
        print_dual_nocl(text, '   frequency is [')
        for a in aa:
            print_dual_nocl(text, '%d, ' % (a))
        print_dual_nocl(text, ']\n')
    # text.update()

def print_dual_nocl(text, aa):
    print(aa, end='')
    # if type(aa) == str: text.insert(END, aa)
    if type(aa) == list:
        print_dual_nocl(text, '   frequency is [')
        for a in aa:
            print_dual_nocl(text, '%d, ' % (a))
        print_dual_nocl(text, ']\n')
    # text.update()
"""

################ 메인함수
if __name__ == "__main__":          #def sangmin_deep_predict(mode, src):
    if (len(sys.argv) == 2):
        src = sys.argv[1]
        print('running with','cuda' if torch.cuda.is_available() else 'cpu', 'environments')
        print('testing what the codec of encoded bitstream is...')  # 코덱분류
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
        print('testing what the scenario of encoded bitstream is...')
        detected_scenario, video = scenario_detect(frequency, video, count)
        # 'default', 'inverse', 'xor'
        print('The scenario for encoding is... %s' % scenario_list[detected_scenario])
        # MPEG2 H.263 H.264 H.265 IVC VP8 JPEG JPEG2000 BMP PNG TIFF

    if (len(sys.argv) != 2):
        print('입력 인자 오류')
