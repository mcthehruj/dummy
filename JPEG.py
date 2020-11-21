import os
import sys
import shutil
import cv2
import subprocess
from openjpeg import decode

import torch
import torch.nn as nn
import torchvision.transforms.functional as TF
import torch.utils.data as data
import numpy as np
import PIL.Image as Image
import random

import utils_tiff_png as utils
from brisque.brisque import BRISQUE


class Candidates_dataset(data.Dataset):
    def __init__(self):
        # Detector 신경망 데이터 로더 생성
        self.frame_list = []
        self.mode = mode
        for i in range(1, 5):
            for j in range(1, 5):
                self.frame_list.append('tmp/Candidates_%d_%d.jpg' % (i, j))

    def transform(self, frame):
        r_frame = TF.resize(frame, (224, 224))
        t_frame = TF.to_tensor(r_frame)
        n_frame = TF.normalize(t_frame, mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
        return n_frame

    def __getitem__(self, index):
        frame = Image.open(self.frame_list[index])
        t_frame = self.transform(frame)

        return t_frame

    def __len__(self):
        return len(self.frame_list)


class Net(nn.Module):
    def __init__(self):
        # 왜곡 검출기 신경망
        super(Net, self).__init__()
        self.features1 = nn.Sequential(nn.Conv2d(3, 64, (3, 3), (1, 1), padding=(1, 1)), nn.BatchNorm2d(64),
                                       nn.ReLU(inplace=True),
                                       nn.Conv2d(64, 64, (3, 3), (1, 1), padding=(1, 1)), nn.BatchNorm2d(64),
                                       nn.ReLU(inplace=True),
                                       nn.MaxPool2d(2, 2), )

        self.features2 = nn.Sequential(nn.Conv2d(64, 128, (3, 3), (1, 1), padding=(1, 1)), nn.BatchNorm2d(128),
                                       nn.ReLU(inplace=True),
                                       nn.Conv2d(128, 128, (3, 3), (1, 1), padding=(1, 1)), nn.BatchNorm2d(128),
                                       nn.ReLU(inplace=True),
                                       nn.MaxPool2d(2, 2), )
        self.features3 = nn.Sequential(nn.Conv2d(128, 256, (3, 3), (1, 1), padding=(1, 1)), nn.BatchNorm2d(256),
                                       nn.ReLU(inplace=True),
                                       nn.Conv2d(256, 256, (3, 3), (1, 1), padding=(1, 1)), nn.BatchNorm2d(256),
                                       nn.ReLU(inplace=True),
                                       nn.Conv2d(256, 256, (3, 3), (1, 1), padding=(1, 1)), nn.BatchNorm2d(256),
                                       nn.ReLU(inplace=True),
                                       nn.MaxPool2d(2, 2), )
        self.features4 = nn.Sequential(nn.Conv2d(256, 512, (3, 3), (1, 1), padding=(1, 1)), nn.BatchNorm2d(512),
                                       nn.ReLU(inplace=True),
                                       nn.Conv2d(512, 512, (3, 3), (1, 1), padding=(1, 1)), nn.BatchNorm2d(512),
                                       nn.ReLU(inplace=True),
                                       nn.Conv2d(512, 512, (3, 3), (1, 1), padding=(1, 1)), nn.BatchNorm2d(512),
                                       nn.ReLU(inplace=True),
                                       nn.MaxPool2d(2, 2), )
        self.features5 = nn.Sequential(nn.Conv2d(512, 512, (3, 3), (1, 1), padding=(1, 1)), nn.BatchNorm2d(512),
                                       nn.ReLU(inplace=True),
                                       nn.Conv2d(512, 512, (3, 3), (1, 1), padding=(1, 1)), nn.BatchNorm2d(512),
                                       nn.ReLU(inplace=True),
                                       nn.Conv2d(512, 512, (3, 3), (1, 1), padding=(1, 1)), nn.BatchNorm2d(512),
                                       nn.ReLU(inplace=True),
                                       nn.MaxPool2d(2, 2))
        self.fc1 = nn.Sequential(nn.Linear(in_features=25088, out_features=4096, bias=True), nn.ReLU(inplace=True), )
        self.fc2 = nn.Sequential(nn.Linear(in_features=4096, out_features=1024, bias=True), nn.ReLU(inplace=True))
        self.fc3 = nn.Sequential(nn.Linear(in_features=1024, out_features=400, bias=True), nn.ReLU(inplace=True))
        self.fc4 = nn.Linear(in_features=400, out_features=107, bias=True)

    def forward(self, im):
        x1 = self.features1(im)
        x2 = self.features2(x1)
        x3 = self.features3(x2)
        x4 = self.features4(x3)
        x5 = self.features5(x4)
        x = x5.view(x5.size()[0], -1)
        f1 = self.fc1(x)
        f2 = self.fc2(f1)
        f3 = self.fc3(f2)
        f4 = self.fc4(f3)

        return nn.functional.log_softmax(f4, dim=1)


def Load_bin(fn):
    with open(fn, 'rb') as f:
        return f.read()


def Find_Marker(Content, Marker):
    """
        마커의 위치를 반환한다.
    """
    found = []
    current_index = -1
    while True:
        current_index += 1
        current_index = Content.find(Marker, current_index)

        if current_index != -1:
            found.append(current_index)
        else:
            break
    return found


def Fix_Byte_Stream(Stream, val, location, offset=10):
    """
        입력 Stream의 입력 위치에 입력 값으로 값을 대체한다.
        Stream(Bytes object): JPEG file bytes stream
        val(hexadecimal)    : new value to replace original value in stream
        location(int)       : location(index) of byte stream to replace old value with new value
    """

    # Initial DQT table data appear after passing 5bytes from '0xff' location
    str_stream = Stream.hex()
    return bytes.fromhex(str_stream[:location * 2 + offset] + val + str_stream[location * 2 + offset + 2:])


def Write_bin(output_fn, Stream):
    with open(output_fn, 'wb') as f:
        f.write(Stream)


def Distortion_JPEG(Bin_Jpeg):
    """
        JPEG 파일이 decoding 시 왜곡된 영상이 추출되도록 헤더의 DQT 테이블을 왜곡한다.
    """
    DQT_MARKER = b'\xff\xdb'

    loc = Find_Marker(Bin_Jpeg, DQT_MARKER)

    Corrupted_val = hex(random.randint(30, 99))[2:]  # 왜곡 값을 생성한다.

    return Fix_Byte_Stream(Bin_Jpeg, Corrupted_val, loc[0])  # 왜곡 값을 특정 위치로 대체시킨다.


def Distortion_J2k(Bin_J2k):
    QCD_MARKER = b'\xff\x5c\x00\x13'

    loc = Find_Marker(Bin_J2k, QCD_MARKER)

    Corrupted_val = hex(random.randint(16 * 7, 16 * 8))[2:]  # 왜곡 값을 생성한다.

    return Fix_Byte_Stream(Bin_J2k, Corrupted_val, loc[0])  # 왜곡 값을 특정 위치로 대체시킨다.


def Candidate_JPEG(Bin_Jpeg, mode):
    DQT_MARKER = b'\xff\xdb'

    loc = Find_Marker(Bin_Jpeg, DQT_MARKER)[0] # DQT 마커의 위치를 찾는다.

    if mode == 'Restore':
        row, col = 4, 5
    elif mode == 'Check':
        row, col = 4, 5
    else:
        raise ValueError('No [%s] mode' % mode)

    for i in range(row):
        for j in range(1, col):
            Candidates_DC = hex(int(8 * i + 2 * j))[2:]  # ex. '0xDC' -> 'DC'
            if len(Candidates_DC) == 1:
                Candidates_DC = '0' + Candidates_DC
            Candidate = Fix_Byte_Stream(Bin_Jpeg, Candidates_DC, loc)
            Write_bin('tmp/Candidates_%d_%d.jpg' % (i + 1, j), Candidate) # JPEG후보를 생성한다.


def Candidate_J2k(Bin_J2k, mode):
    QCD_MARKER = b'\xff\x5c\x00\x13'

    loc = Find_Marker(Bin_J2k, QCD_MARKER)[0] # QCD 마커의 위치를 찾는다.

    if mode == 'Restore':
        row, col = 4, 5
    elif mode == 'Check':
        row, col = 4, 5
    else:
        raise ValueError('No [%s] mode' % mode)

    for i in range(row):
        for j in range(1, col):
            Candidates_QC = hex(int(8 * 6 + 5 * i + 1 * j))[2:]  # ex. '0xDC' -> 'DC'
            if len(Candidates_QC) == 1:
                Candidates_QC = '0' + Candidates_QC
            Candidate = Fix_Byte_Stream(Bin_J2k, Candidates_QC, loc)
            Write_bin('tmp/Candidates_%d_%d.j2k' % (i + 1, j), Candidate) # JPEG2000 후보를 생성한다.


def Distortion(fn):
    Current_bin = Load_bin(fn)
    
    # Save distorted file
    if os.path.splitext(fn)[1] == '.jpg':
        Current_bin = Distortion_JPEG(Current_bin) # jPEG 파일에 왜곡을 수행한다.
        Write_bin(fn.replace('.jpg', '_Distorted.jpg'), Current_bin) # 왜곡 영상을 저장한다.
    elif os.path.splitext(fn)[1] == '.j2k':
        Current_bin = Distortion_J2k(Current_bin) # jPEG2000 파일에 왜곡을 수행한다.
        Write_bin(fn.replace('.j2k', '_Distorted.j2k'), Current_bin) # 왜곡 영상을 저장한다.


def Restoration(fn):
    if not os.path.exists('tmp'):
        os.mkdir('tmp')

    ext = os.path.splitext(fn)[1]
    current_bin = Load_bin(fn)
    if ext == '.jpg':
        Candidate_JPEG(current_bin, 'Restore')  # JPEG 후보를 만든다.
    elif ext == '.j2k':
        Candidate_J2k(current_bin, 'Restore')  # JPEG2000 후보를 만든다.
        subprocess.call(['python.exe', 'j2kTojpg.py']) # JPEG2000 후보 영상을 전처리가 간편한 JPEG으로 저장한다.

    Detector = Net().cuda()
    Detector.load_state_dict(torch.load('JPEG_Net.pth'))
    Detector.eval()

    data_loader = data.DataLoader(Candidates_dataset(), num_workers=0, batch_size=16, shuffle=False)

    with torch.no_grad():
        for iteration, batch in enumerate(data_loader, 1):
            input = batch.cuda()

            Prob = Detector(input)
            score_list, rank_list = torch.topk(Prob, 10)

            distortion_class = np.array(rank_list[:, :3].detach().cpu())
            distortion_score = np.array(score_list[:, :3].detach().cpu())

            restore_num = None
            No_distortion_level = 7

            while restore_num is None:
                for i in range(3):
                    class_temp = distortion_class[:, i]
                    score_temp = distortion_score[:, i]

                    if score_temp[class_temp == No_distortion_level].size > 0:
                        gt_score = score_temp * [class_temp == No_distortion_level] - 9999 * (
                                    class_temp != No_distortion_level)

                        restore_num = np.argmax(gt_score)
                        break

                if not restore_num:
                    No_distortion_level -= 1

            restore_idx = (restore_num // 4 + 1, restore_num % 4 + 1)

    # 복원 점수가 가장 높은 후보 영상을 복원 영상으로 추출
    shutil.copy('tmp/Candidates_%d_%d%s' % (restore_idx[0], restore_idx[1], ext), fn.replace('_Distorted', '_Restored'))


def Check(fn):
    flag = False
    if not os.path.exists('tmp'):
        os.mkdir('tmp')

    brisque = BRISQUE()  # 시나리오 검사를 위한 체크 점수

    ext = os.path.splitext(fn)[1]
    current_bin = Load_bin(fn)
    if ext == '.jpg':
        Candidate_JPEG(current_bin, 'Check')  # 후보 생성
        flag = True
    elif ext == '.j2k':
        Candidate_J2k(current_bin, 'Check')  # 후보 생성
        subprocess.call(['python.exe', 'j2kTojpg.py']) # JPEG2000 후보 영상을 전처리가 간편한 JPEG으로 저장한다.
        flag = True

    score_list = []
    if flag:
        for i in range(1, 5):
            for j in range(1, 5):
                try:
                    img = cv2.imread('tmp/Candidates_%d_%d.jpg' % (i, j))

                    score_list.append(brisque.get_score(img))  # 후보들의 체크 점수를 계산

                except:
                    score_list.append(99999)  # 영상이 JPEG 또는 JPEG2000이 아닌경우, JPEG, JPEG2000 이 아님을 나타내는 상수
        if min(score_list) > 150:
            return 0  # Not JPEG, JPEG2000 scenario
        else:
            return 1  # JPEG, JPEG2000 scenario
    else:
        return 0  # Not JPEG, JPEG2000 scenario


if __name__ == "__main__":
    '''
        Distortion: python.exe JPEG.py xxx.jpg 0
        Restoration: python.exe JPEG.py xxx_Distorted.jpg 1
        Check: python.exe JPEG.py xxx_Distorted.jpg 2
    '''

    fn, ext = os.path.splitext(sys.argv[1])

    if ext in ['.jpg', '.j2k']:
        mode = sys.argv[2]
        if mode == '0':
            Distortion(sys.argv[1])
        elif mode == '1':
            Restoration(sys.argv[1])
        elif mode == '2':
            check_flag = Check(sys.argv[1])
            if check_flag == 0:
                # Not JPEG, JPEG2000 scenario
                raise ValueError()
        else:
            raise ValueError('Only [0, 1, 2] for mode argument')

    else:
        # Not JPEG, JPEG2000 scenario
        raise ValueError()
