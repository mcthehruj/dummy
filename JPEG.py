import os
import sys
import shutil
import cv2
from pylibjpeg import decode

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
    def __init__(self, mode='jpg'):
        self.frame_list = []
        self.mode = mode
        for i in range(1,5):
            for j in range(1,5):
                if mode == '.jpg':
                    self.frame_list.append('tmp/Candidates_%d_%d.jpg'%(i,j))
                elif mode == '.j2k':
                    self.frame_list.append('tmp/Candidates_%d_%d.j2k'%(i,j))
                elif mode == '.bmp':
                    self.frame_list.append('tmp/Candidates_%d_%d.bmp'%(i,j))

    def transform(self, frame):
        r_frame = TF.resize(frame, (224, 224))
        t_frame = TF.to_tensor(r_frame)
        n_frame = TF.normalize(t_frame, mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
        return n_frame

    def __getitem__(self, index):
        if self.mode in ['.jpg', '.bmp']:
            frame = Image.open(self.frame_list[index])
        elif self.mode == '.j2k':
            frame = Image.fromarray(decode(self.frame_list[index]))

        t_frame = self.transform(frame)

        return t_frame

    def __len__(self):
        return len(self.frame_list)
        

class Net(nn.Module):
    def __init__(self):
        super(Net, self).__init__()
        # vgg16_features = list(vgg16_bn().children())
        self.features1 = nn.Sequential(nn.Conv2d(3, 64, (3, 3), (1, 1), padding=(1, 1)), nn.BatchNorm2d(64), nn.ReLU(inplace=True),
                                      nn.Conv2d(64, 64, (3, 3), (1, 1), padding=(1, 1)), nn.BatchNorm2d(64), nn.ReLU(inplace=True),
                                      nn.MaxPool2d(2,2),)

        self.features2 = nn.Sequential(nn.Conv2d(64, 128, (3, 3), (1, 1), padding=(1, 1)), nn.BatchNorm2d(128), nn.ReLU(inplace=True),
                                      nn.Conv2d(128,128, (3, 3), (1, 1), padding=(1, 1)), nn.BatchNorm2d(128), nn.ReLU(inplace=True),
                                      nn.MaxPool2d(2, 2),)
        self.features3 = nn.Sequential(nn.Conv2d(128,256, (3, 3), (1, 1), padding=(1, 1)), nn.BatchNorm2d(256), nn.ReLU(inplace=True),
                                      nn.Conv2d(256,256, (3, 3), (1, 1), padding=(1, 1)), nn.BatchNorm2d(256), nn.ReLU(inplace=True),
                                      nn.Conv2d(256,256, (3, 3), (1, 1), padding=(1, 1)), nn.BatchNorm2d(256), nn.ReLU(inplace=True),
                                      nn.MaxPool2d(2, 2),)
        self.features4 = nn.Sequential(nn.Conv2d(256, 512, (3, 3), (1, 1), padding=(1, 1)), nn.BatchNorm2d(512), nn.ReLU(inplace=True),
                                      nn.Conv2d(512, 512, (3, 3), (1, 1), padding=(1, 1)), nn.BatchNorm2d(512), nn.ReLU(inplace=True),
                                      nn.Conv2d(512, 512, (3, 3), (1, 1), padding=(1, 1)), nn.BatchNorm2d(512), nn.ReLU(inplace=True),
                                      nn.MaxPool2d(2, 2),)
        self.features5 = nn.Sequential(nn.Conv2d(512, 512, (3, 3), (1, 1), padding=(1, 1)), nn.BatchNorm2d(512), nn.ReLU(inplace=True),
                                      nn.Conv2d(512, 512, (3, 3), (1, 1), padding=(1, 1)), nn.BatchNorm2d(512), nn.ReLU(inplace=True),
                                      nn.Conv2d(512, 512, (3, 3), (1, 1), padding=(1, 1)), nn.BatchNorm2d(512), nn.ReLU(inplace=True),
                                      nn.MaxPool2d(2, 2))
        self.fc1 = nn.Sequential(nn.Linear(in_features=25088, out_features=4096, bias=True),nn.ReLU(inplace=True),)
        self.fc2 = nn.Sequential(nn.Linear(in_features=4096, out_features=1024, bias=True),nn.ReLU(inplace=True))
        self.fc3 = nn.Sequential(nn.Linear(in_features=1024, out_features=400, bias=True),nn.ReLU(inplace=True))
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
        Return marker location(index)
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
        Randomly transform DQT table in JPEG file header to cause distorted image problem when JPEG file is decoded by a viewer program(codec).
    """
    DQT_MARKER = b'\xff\xdb'

    loc = Find_Marker(Bin_Jpeg, DQT_MARKER)

    Corrupted_val = hex(random.randint(30, 99))[2:] # ex. '0xDC' -> 'DC'

    return Fix_Byte_Stream(Bin_Jpeg, Corrupted_val, loc[0])

def Distortion_J2k(Bin_J2k):
    QCD_MARKER = b'\xff\x5c'

    loc = Find_Marker(Bin_J2k, QCD_MARKER)

    Corrupted_val = hex(random.randint(16*7, 16*8))[2:] # ex. '0xDC' -> 'DC'

    return Fix_Byte_Stream(Bin_J2k, Corrupted_val, loc[0])


def Candidate_JPEG(Bin_Jpeg, mode):
    DQT_MARKER = b'\xff\xdb'

    loc = Find_Marker(Bin_Jpeg, DQT_MARKER)[0]

    if mode == 'Restore':
        row, col = 4,5
    elif mode == 'Check':
        row, col = 4,5
    else:
        raise ValueError('No [%s] mode'%mode)
    
    for i in range(row):
        for j in range(1,col):
            Candidates_DC = hex(int(8*i+ 2*j))[2:]  # ex. '0xDC' -> 'DC'
            if len(Candidates_DC) == 1:
                Candidates_DC = '0' + Candidates_DC
            Candidate = Fix_Byte_Stream(Bin_Jpeg, Candidates_DC, loc)
            Write_bin('tmp/Candidates_%d_%d.jpg'%(i+1,j), Candidate)

def Candidate_J2k(Bin_J2k, mode):
    QCD_MARKER = b'\xff\x5c'

    loc = Find_Marker(Bin_J2k, QCD_MARKER)[0]

    if mode == 'Restore':
        row, col = 4,5
    elif mode == 'Check':
        row, col = 4,5
    else:
        raise ValueError('No [%s] mode'%mode)
    
    for i in range(row):
        for j in range(1,col):
            Candidates_QC = hex(int(16*3+10*i+2*j))[2:]  # ex. '0xDC' -> 'DC'
            if len(Candidates_QC) == 1:
                Candidates_QC = '0' + Candidates_QC
            Candidate = Fix_Byte_Stream(Bin_J2k, Candidates_QC, loc)
            Write_bin('tmp/Candidates_%d_%d.j2k'%(i+1,j), Candidate)

def Candidate_BMP(Bin_BMP):
    candidates = [2, 4, 8, 16]
    BMP_header_chunk_length = 14

    biWidth = Bin_BMP[BMP_header_chunk_length + 4:BMP_header_chunk_length + 8]
    biHeight = Bin_BMP[BMP_header_chunk_length + 8:BMP_header_chunk_length + 12]

    biWidth_int = int.from_bytes(biWidth, 'little')
    biHeight_int = int.from_bytes(biHeight, 'little')

    for i in range(4):
        for idx, candidate in enumerate(candidates):
            biWidth_candidate = int(biWidth_int * candidate).to_bytes(2, byteorder='little')
            biHeight_candidate = int(biHeight_int / candidate).to_bytes(2, byteorder='little')
            fixed, _ = utils.Fix_Byte_Stream_v2(Bin_BMP, biWidth_candidate, BMP_header_chunk_length + 4)
            fixed, _ = utils.Fix_Byte_Stream_v2(fixed, biHeight_candidate, BMP_header_chunk_length + 8)
            with open('tmp/Candidates_{}_{}.bmp'.format(i+1, idx+1), 'wb') as f:
                f.write(fixed)


def Distortion(fn):
    Current_bin = Load_bin(fn)
    # Perform distortion to loaded JPEG binary data
    
    # Save distorted JPEG file
    if os.path.splitext(fn)[1] == '.jpg':
        Current_bin = Distortion_JPEG(Current_bin)
        Write_bin(fn.replace('.jpg','_Distorted.jpg'), Current_bin)
    elif os.path.splitext(fn)[1] == '.j2k':        
        Current_bin = Distortion_J2k(Current_bin)
        Write_bin(fn.replace('.j2k','_Distorted.j2k'), Current_bin)
    
def Restoration(fn):
    if not os.path.exists('tmp'):
            os.mkdir('tmp')

    ext = os.path.splitext(fn)[1]
    current_bin = Load_bin(fn)
    if ext == '.jpg':
        Candidate_JPEG(current_bin, 'Restore') # made in Check
    elif ext == '.j2k':
        Candidate_J2k(current_bin, 'Restore')  # made in Check
    elif ext == '.bmp':
        Candidate_BMP(current_bin)  # made in Check

    Detector = Net().cuda()
    Detector.load_state_dict(torch.load('JPEG_Net.pth'))
    Detector.eval()

    data_loader = data.DataLoader(Candidates_dataset(mode=ext), num_workers=0, batch_size=16, shuffle=False)

    with torch.no_grad():
        for iteration, batch in enumerate(data_loader, 1):
            input = batch.cuda()

            Prob = Detector(input)
            score_list, rank_list = torch.topk(Prob, 10)

            distortion_class = np.array( rank_list[:, :3].detach().cpu())
            distortion_score = np.array(score_list[:, :3].detach().cpu())

            restore_num = None
            No_distortion_level = 7

            while restore_num is None:
                for i in range(3):
                    class_temp = distortion_class[:,i]
                    score_temp = distortion_score[:,i]

                    if score_temp[class_temp == No_distortion_level].size > 0:
                        gt_score = score_temp * [class_temp==No_distortion_level] - 9999 * (class_temp!=No_distortion_level)

                        restore_num = np.argmax(gt_score)
                        break

                if not restore_num:
                    No_distortion_level -=1

            restore_idx = (restore_num//4 +1 , restore_num%4 + 1)
            # print(restore_idx)

    
    shutil.copy('tmp/Candidates_%d_%d%s'%(restore_idx[0], restore_idx[1],ext), fn.replace('_Distorted','_Restored'))


def Check(fn):
    flag = False
    if not os.path.exists('tmp'):
            os.mkdir('tmp')

    brisque = BRISQUE()
    
    ext = os.path.splitext(fn)[1]
    current_bin = Load_bin(fn)
    if ext == '.jpg':
        Candidate_JPEG(current_bin,'Check')
        flag = True
    elif ext == '.j2k':
        Candidate_J2k(current_bin, 'Check')
        flag = True

    score_list = []
    if flag:
        for i in range(1,5):
            for j in range(1,5):
                try:
                    if ext =='.jpg':
                        img = cv2.imread('tmp/Candidates_%d_%d.jpg'%(i,j))

                    elif ext =='.j2k':
                        img = decode('tmp/Candidates_%d_%d.j2k'%(i,j))
                    score_list.append(brisque.get_score(img))
                except:
                    score_list.append(99999)

        if min(score_list) > 150:
            return 0
        else:
            return 1
    else:
        return 0


if __name__ == "__main__":
    '''
        Distortion: python.exe JPEG.py xxx.jpg 0
        Restoration: python.exe JPEG.py xxx_Distorted.jpg 1
        Check: python.exe JPEG.py xxx_Distorted.jpg 2
    '''
    fn, ext = os.path.splitext(sys.argv[1])

    if ext in ['.jpg','.j2k']:
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