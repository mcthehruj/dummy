import sys
from random import shuffle
from glob import glob
import bitstring
import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F
from torch.autograd import Variable
import math
from datetime import datetime
import timeit
import time


def list2int(list):
    return int(len(list) != 0)


codec_list = ['.m2v', '.h263', '.264', '.hevc', '.bit', '.webm', '.jpg', '.j2k', '.bmp', '.png', '.tiff']
codec = ['MPEG-2', 'H.263', 'H.264', 'H.265', 'IVC', 'VP8', 'JPEG', 'JPEG2000', 'BITMAP', 'PNG', 'TIFF']
alphabet = ['a', 'b', 'c', 'd', 'e', 'f']
scenario_list = ['default', 'inverse', 'xor']
# Bi-LSTM(Attention) Parameters
embedding_dim = 128
n_hidden = 64
num_classes = len(codec_list)
all_bytes_in_a_sentence = 64
shift_bytes_in_a_sentence = 1
num_chars_in_a_word = 1
number_of_sentences = 16

# Word List for Att-BLSTM
word_dict = {}
hexList = []
for i in range(10):
    hexList.append(str(i))
for i in alphabet:
    hexList.append(i)
for i in range(16):
    word_dict[hexList[i]] = i
    for j in range(16):
        word_dict[hexList[i]+hexList[j]] = 16 * i + j
        for k in range(16):
            word_dict[hexList[i]+hexList[j]+hexList[k]] = (16 ** 2) * i + 16 * j + k
            for l in range(16):
                word_dict[hexList[i]+hexList[j]+hexList[k]+hexList[l]] = (16 ** 3) * i + (16 ** 2) * j + 16 * k + l

vocab_size = len(word_dict)


# Network architecture
class BiLSTM_Attention(nn.Module):
    def __init__(self, n_hidden):
        super(BiLSTM_Attention, self).__init__()

        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.embedding = nn.Embedding(vocab_size, embedding_dim).to(device)
        self.lstm = nn.LSTM(embedding_dim, n_hidden, bidirectional=True).to(device)
        self.out = nn.Linear(n_hidden * 2, num_classes).to(device)
        self.n_hidden = n_hidden

    def attention_net(self, lstm_output, final_state):
        hidden = final_state.view(-1, self.n_hidden * 2, 1)
        attn_weights = torch.bmm(lstm_output, hidden).squeeze(2)
        soft_attn_weights = F.softmax(attn_weights, 1)
        context = torch.bmm(lstm_output.transpose(1, 2), soft_attn_weights.unsqueeze(2)).squeeze(2)
        return context, soft_attn_weights.data

    def forward(self, X):
        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        input = self.embedding(X).to(device)
        input = input.permute(1, 0, 2)
        hidden_state = Variable(torch.zeros(1*2, len(X), self.n_hidden)).to(device)
        cell_state = Variable(torch.zeros(1*2, len(X), self.n_hidden)).to(device)
        output, (final_hidden_state, final_cell_state) = self.lstm(input, (hidden_state, cell_state))
        output = output.permute(1, 0, 2)
        attn_output, attention = self.attention_net(output, final_hidden_state)
        return self.out(attn_output), attention


def codec_decide(video_):
    video_.pos = 0
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model = BiLSTM_Attention(n_hidden)
    model.to(device)
    a = torch.load(glob('Bi-LSTM_96.63.pth')[0], map_location=device)
    model.load_state_dict(a)
    model.to(device)
    predicted_codec = [0] * num_classes       # MPEG-2, H.263, H.264,... 의 예측값의 빈도수를 각각 저장
    limit = (number_of_sentences - 1) * shift_bytes_in_a_sentence + all_bytes_in_a_sentence     # 학습시킨 데이터 길이만큼만 검증
    for i in range(limit):
        tt = video_.read(all_bytes_in_a_sentence * int(math.log2(16))).hex
        video_.pos -= all_bytes_in_a_sentence * int(math.log2(16))
        video_.pos += shift_bytes_in_a_sentence * int(math.log2(16))
        predict = test(tt, num_chars_in_a_word, model)
        predicted_codec[predict] += 1
    return predicted_codec


def xor_header(header_list, xor_flag=1):                                # 원래 코덱의 스타트 코드 검색 리스트
    a = len(header_list)
    b = []
    header_list_ = []                                                   # 시나리오로 변형된 코드 검색 리스트
    for i in range(a):
        header_list_.append([])
        b.append(len(header_list[i]))
        for j in range(b[i]):
            if xor_flag == 0:
                header_list_[i].append(encode(header_list[i][j], 'inv'))
            elif xor_flag == 1:
                header_list_[i].append(xor_fast(header_list[i][j]))
                # 스타트 코드 다음 한 비트가 0이냐 1이냐에 따라서 두 가지 결과가 나오기에 모두 저장
                if header_list_[i][j*2][len(header_list_[i][j*2]) - 1] == '0':
                    new = header_list_[i][j*2][:len(header_list_[i][j*2]) - 1]
                    new += '1'
                    header_list_[i].append(new)
                elif header_list_[i][j*2][len(header_list_[i][j*2]) - 1] == '1':
                    new = header_list_[i][j*2][:len(header_list_[i][j*2]) - 1]
                    new += '0'
                    header_list_[i].append(new)
    return header_list_


def scenario_search(video_, header_list, start_=False):
    predicted_codec_header = [0] * len(header_list)
    time_scale = 30  # 1일때 모든 비트스트림을 다 본다. 시간이 너무 길게 걸리므로 이 값을 늘리면서 실험하는 것을 추천.

    video_ = video_.bin       # binstring read로 읽어오게되면 bit 개수만큼 파일리드를 그제서야 돌려서 엄청오래걸리는듯,, bin str으로 처리하는게 빠름

    limit = len(video_) // time_scale
    if limit < 5000:   limit = 5000           # 하한
    if limit > 60000: limit = 60000           # 상한   120000 정도가 적당한거 같은데 느리니까 60000
    bin_header_list = header_list

    if start_:
        for kk in range(len(bin_header_list[0])):
            if video_[0:len(header_list[0][0])] == header_list[0][kk]:
                predicted_codec_header[0] += 1
        for ii in range(0, limit, 8):                   # video.pos = ii : 비트위치 ii
            for k in range(len(bin_header_list)):       # header list에 대한 for
                if k == 0:
                    continue
                if bin_header_list[k] == []:
                    continue
                for kk in range(len(bin_header_list[k])):               # nalu 쌍들 여러개에 대한 for
                    if video_[ii:ii + len(bin_header_list[k][kk])] == bin_header_list[k][kk]:
                        predicted_codec_header[k] += 1

    else:
        for ii in range(0, limit, 8):               # video.pos = ii : 비트위치 ii
            for k in range(len(bin_header_list)):   # header list에 대한 for
                if bin_header_list[k] == []:
                    continue
                for kk in range(len(bin_header_list[k])):               # nalu 쌍들 여러개에 대한 for
                    if video_[ii:ii + len(bin_header_list[k][kk])] == bin_header_list[k][kk]:
                        predicted_codec_header[k] += 1
    return predicted_codec_header


def encode_all(string, operator, part):
    results = []
    keys = []
    if operator == 'xor':
        k = len(string)//part
        for j in range(part):
            # print(j + 1)
            m = string[j * k:(j + 1) * k]
            result = ''
            for i in range(len(m) - 1):
                partition = str(int(m[i]) ^ int(m[i + 1]))
                result += partition
            results.append(result)
            keys.append(m[1])
        keys.reverse()
    return ''.join(results) + ''.join(keys)


def encode(string, operator):
    result = ''
    if operator == 'inv':
        for i in range(len(string)):
            if string[i] == '1':
                result += '0'
            if string[i] == '0':
                result += '1'
    return result


def decode_all(string, operator, part):
    results = []
    k = len(string)//part - 1
    for j in range(part):
        m = string[j * k:(j + 1) * k]
        key = string[len(string) - 1 - j]
        result = decode(m + key, operator)
        results.append(result)
        # print(j/part*100, '%')
    return ''.join(results)


def decode(string, operator):
    result = []
    if operator == 'xor':
        for i in range(len(string) - 1):
            if i == 0:
                if string[i] == '0' and string[len(string) - 1] == '0':
                    result.append('00')
                if string[i] == '0' and string[len(string) - 1] == '1':
                    result.append('11')
                if string[i] == '1' and string[len(string) - 1] == '0':
                    result.append('10')
                if string[i] == '1' and string[len(string) - 1] == '1':
                    result.append('01')
            else:
                limit = len(result)
                for j in range(limit):
                    if string[i] == '0' and result[j][i] == '0':
                        result.append(result[j] + '0')
                    elif string[i] == '0' and result[j][i] == '1':
                        result.append(result[j] + '1')
                    elif string[i] == '1' and result[j][i] == '1':
                        result.append(result[j] + '0')
                    elif string[i] == '1' and result[j][i] == '0':
                        result.append(result[j] + '1')
                result.reverse()
                for k in range(limit):
                    result.pop()
    return result[0]


def xor_fast(string, part=1):
    return encode_all(string, 'xor', part)


def dxor_fast(string, part=1):
    return decode_all(string, 'xor', part)


### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ###
# 2메가 영상 xor 복조하는데 5분이 걸려서 비트스트림버전으로 변경

def xor_fast_bitstream(stream, none=0, flag=0):
    if type(stream) is str: stream = bitstring.BitStream(bin=stream); flag=1    #bitstring, binarystream 둘다 입력 가능
    result = bytearray(); i = 0
    part = len(stream)
    stream1 = stream.bin
    stream2 = stream.bin[1:]
    for ii in range(0, part-32, 32):            # 32배수로 돈다
        a = int(stream1[ii:ii+32], base=2)
        b = int(stream2[ii:ii+32], base=2)
        c = (a^b).to_bytes(4, byteorder='big')
        result += c; i = ii+32
    remain = part - i                          # 32미만으로 남았을때
    remain_b = remain // 8
    remain_b += bool(remain % 8)                # 올림처리 위해
    a = int(stream1[i:i+remain], base=2)
    if remain == 1: b = 0                       # 1bit 남은 경우 읽을 bit이 0이라 오류
    else:
        b = int(stream2[i:i+remain-1], base=2) << 1    # 마지막 1개는 0 채운다
    c = ((a^b)<<(-remain)%8).to_bytes(remain_b, byteorder='big')
    result += c
    return bitstring.BitStream(result).bin if flag == 1 else result

def dxor_fast_bitstream(stream, none=0, flag=0):
    result = []
    result.append(0)
    lastc = 0
    a = stream.bin
    for ii in range(len(stream)-1):
        t = lastc ^ int(a[ii])
        result.append(t)
        lastc = t
    t = lastc ^ int(a[-1])

    result = bitstring.BitStream(result)
    if t == 1: result = ~result

    return bitstring.BitStream(result).bin if flag == 1 else result.bytes


def dec2bin(number, length):
    result = ''
    if number == 0:
        return '0000'
    while number != 1:
        result += str(number%2)
        number = number//2
    result += '1'
    result = result[::-1]
    final = ''
    for i in range(length):
        if len(result) == length - i:
            for j in range(i):
                final += '0'
            final += result
    return final


def bin2dec(string):
    dec = 0
    for n in range(len(string)):
        dec += int(string[n]) * pow(2, len(string) - n - 1)
    return dec


def hex2bin(string):
    global alphabet
    result = ''
    hex2dec = list(range(10, 16))
    for i in range(len(string)):
        for j in range(10):
            if string[i] == str(j):
                result += dec2bin(j, 4)
        for j in range(6):
            if string[i] == alphabet[j]:
                result += dec2bin(hex2dec[j], 4)
    return result


def bin2hex(string):
    global alphabet
    result = ''
    for i in list(range(0, len(string), 4)):
        s = string[i:i+4]
        t = bin2dec(s)
        for j in range(10):
            if t == j:
                result += str(j)
        for j in range(6):
            if t == j + 10:
                result += alphabet[j]
    return result


def asMinutes(s):
    m = math.floor(s / 60)
    s -= m * 60
    return '%dm %ds' % (m, s)


def timeSince(since, percent):
    now = time.time()
    s = now - since
    es = s / (percent)
    rs = es - s
    return '%s (- %s)' % (asMinutes(s), asMinutes(rs))


def Hex2Zero(string):
    global alphabet
    result = ''
    # Scenario : Reversed 0 & 1 -> Call This Function before calling SplitOne2Ten
    for i in range(len(string)):
        for j in range(len(alphabet)):
            if string[i] == alphabet[j]:
                inputnumber = 10 + j
        if string[i] not in alphabet:
            inputnumber = int(string[i])
        outputnumber = 15 - inputnumber
        for j in range(len(alphabet)):
            if outputnumber == 10 + j:
                part = alphabet[j]
        if outputnumber < 10:
            part = str(outputnumber)
        result += part
    return result


def split1to10(string, word_length):        # 1-byte N words
    original = string
    index = word_length
    sentence_length = len(string) // word_length
    string = original[ : index]
    for i in range(sentence_length - 1):
        string = string + ' '
        string = string + original[index : (index + word_length)]
        index += word_length
    string += original[index : ]
    return string


def shufflemylist(random_codec, random_label):
    order = list(range(len(random_codec)))
    shuffle(order)
    final_codec = []
    final_label = []
    for i in range(len(order)):
        final_codec.append(random_codec[order[i]])
        final_label.append(random_label[order[i]])
    result = []
    result.append(final_codec)
    result.append(final_label)
    return result


def test(test_text, num_chars_in_a_word, model):
    # Test
    test_text = test_text.replace(" ", "")
    test_text = split1to10(test_text, num_chars_in_a_word)
    tests = [np.asarray([word_dict[n] for n in test_text.split()])]
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    test_batch = Variable(torch.LongTensor(tests)).to(device)
    # Predict
    predict, _ = model(test_batch)
    predict = predict.data.max(1, keepdim=True)[1]
    return predict[0][0]


if __name__ == "__main__":
    if (len(sys.argv) != 3):
        print('입력 인자 오류')
    if (len(sys.argv) == 3):
        src = sys.argv[1]
        video = bitstring.ConstBitStream(filename=src)
        predicted_codec_ = [0,0,0,0,0,0,0,0,0,0,0]              # MPEG2 H.263 H.264 H.265 IVC VP8 JPEG JPEG2000 BMP PNG TIFF
        # sys.argv[2].split('.')
        for i, aa in enumerate(codec):
            if aa == sys.argv[2]: predicted_codec_[i] = 1

        print('변형 시나리오 inv, x_or 판단 중..')                # INV, XOR 두가지만

        if predicted_codec_.index(max(predicted_codec_)) == 0:                                                # MPEG2
            ssc = [hex2bin('000001b3')]                                                         # 스타트 코드들 저장
            sec = [hex2bin('000001b5')]
            gop = [hex2bin('000001b8')]
            psc = [hex2bin('00000100')]
            start = False

        elif predicted_codec_.index(max(predicted_codec_)) == 1:                                              # H.263
            ssc = [hex2bin('000080'), hex2bin('000081'), hex2bin('000082'), hex2bin('000083')]  # psc
            sec = []                                                                            # gbsc
            # """
            for i in range(8, 16):
                if i >= 11:
                    j = alphabet[i - 11]
                else:
                    j = str(i)
                sec.append(hex2bin('0000' + j))
            # """
            gop = []
            psc = []
            start = True

        elif predicted_codec_.index(max(predicted_codec_)) == 2:                                              # H.264
            ssc = [hex2bin('0000000167')]                                                       # sps
            sec = [hex2bin('0000000168')]                                                       # pps
            gop = [hex2bin('0000000165'), hex2bin('0000010605')]                                # idr
            psc = [hex2bin('0000000141')]                                                       # nidr
            start = False

        elif predicted_codec_.index(max(predicted_codec_)) == 3:                                              # H.265
            ssc = [hex2bin('00000001')]                                                         # sps
            sec = [hex2bin('000003')]                                                           # pps
            gop = []                                                                            # idr
            psc = []                                                                            # nidr
            start = False

        elif predicted_codec_.index(max(predicted_codec_)) == 4:                                              # IVC
            ssc = [hex2bin('000001b0')]                                                         # vsc
            sec = [hex2bin('00000100')]                                                         # vec
            gop = [hex2bin('000001b2')]                                                         # usc
            psc = [hex2bin('000001b3')]                                                         # udc
            start = True

        elif predicted_codec_.index(max(predicted_codec_)) == 5:                                              # VP8
            ssc = [hex2bin('1a45dfa3010000000000001f')]                                         # sc
            sec = [hex2bin('7765626d')]                                                         # webm
            gop = [hex2bin('1549a96601')]                                                       # ed1
            psc = [hex2bin('00000000000032')]                                                   # ed2
            start = True

        elif predicted_codec_.index(max(predicted_codec_)) == 6:                                              # JPEG
            ssc = [hex2bin('ffd8')]                                                             # sc
            sec = [hex2bin('ffc0'), hex2bin('ffc2')]                                            # sof
            gop = []                                                                            # None
            psc = []                                                                            # None
            start = True

        elif predicted_codec_.index(max(predicted_codec_)) == 7:                                              # JPEG2000
            ssc = [hex2bin('ff4f')]                                                             # sc
            sec = [hex2bin('ff90')]                                                             # sot
            gop = [hex2bin('ff93')]                                                             # sod
            psc = []                                                                            # siz
            start = True

        elif predicted_codec_.index(max(predicted_codec_)) == 8:                                              # BMP
            ssc = [hex2bin('424d')]                                                             # hd1
            sec = [hex2bin('28000000'), hex2bin('0c000000'), hex2bin('40000000'), hex2bin('6c000000'), hex2bin('7c000000')]
            gop = []                                                                            # V3
            psc = []                                                                            # None
            start = True

        elif predicted_codec_.index(max(predicted_codec_)) == 9:                                              # PNG
            ssc = [hex2bin('89504e47')]                                                         # hd1
            sec = [hex2bin('49484452')]                                                         # ihdr
            gop = [hex2bin('49444154')]                                                         # idat
            psc = []                                                                            # None
            start = True

        elif predicted_codec_.index(max(predicted_codec_)) == 10:                                             # TIFF
            ssc = [hex2bin('4949'), hex2bin('4d4d')]                                            # hd1
            sec = [hex2bin('002a'), hex2bin('2a00')]                                            # hd2
            gop = []                                                                            # None
            psc = []                                                                            # None
            start = True

        all = list2int(ssc) + list2int(sec) + list2int(gop) + list2int(psc)
        num_reversed_header = scenario_search(video, xor_header([ssc, sec, gop, psc], xor_flag=0), start_=start)
        num_xor_header = scenario_search(video, xor_header([ssc, sec, gop, psc], xor_flag=1), start_=start)

        video.pos = 0
        video = video.read(video.length).bin
        header_count = [num_inv_header, num_xor_header]
        inv_vs_xor = [True, True]

        for h in range(len(header_count)):                   # h =[num_inv_header, num_xor_header]
            if sum(header_count[h]) == 0 or header_count[h][0] == 0:                                 # 모두 0 이어야 제외하도록 바꿔봄
                inv_vs_xor[h] = False

            if codec[predicted_codec_.index(max(predicted_codec_))] == 'BITMAP':
                if header_count[h][0] != 1:       # 헤더의 수가 너무 많으면 믿지 않는다
                    print('too many header > 1', f'(inv{header_count[0]} vs x_or{header_count[1]})')
                    inv_vs_xor[h] = False

            if codec[predicted_codec_.index(max(predicted_codec_))] == 'H.263':
                if header_count[h][1] >= 10:      # 헤더의 수가 너무 많으면 믿지 않는다
                    print('so many break >= 10', f'(inv{header_count[0]} vs x_or{header_count[1]})')
                    inv_vs_xor[h] = False

            if codec[predicted_codec_.index(max(predicted_codec_))] == 'TIFF' or codec[predicted_codec_.index(max(predicted_codec_))] == 'JPEG' or codec[predicted_codec_.index(max(predicted_codec_))] == 'PNG':        #'JPEG2000', 'PNG', 'TIFF'
                if h == 0:
                    if header_count[h][0] != 1:       # 헤더의 수가 너무 많으면 믿지 않는다
                        print('too many header > 1', f'(inv{header_count[0]} vs x_or{header_count[1]})')
                        inv_vs_xor[h] = False
                else:
                    if header_count[h][0] > 2:        # 헤더의 수가 너무 많으면 믿지 않는다
                        print('too many header > 1', f'(inv{header_count[0]} vs x_or{header_count[1]})')
                        inv_vs_xor[h] = False


        if sum(inv_vs_xor) == 2:    # 출현 헤더수 대소비교를 통해 결정
            if num_inv_header < num_xor_header:
                inv_vs_xor[0] = False
            else:
                inv_vs_xor[1] = False

        elif sum(inv_vs_xor) == 1:  # 하나 남는다면 확정처리
            if inv_vs_xor[0] == 1:
                detected_scenario = 1 # inv
            if inv_vs_xor[1] == 1:
                detected_scenario = 2 # xor
            # print('# of %s headers ->' % scenario_list[detected_scenario], header_count[h])
            print(scenario_list[detected_scenario], f'found (inv{header_count[0]} vs x_or{header_count[1]})')
            if detected_scenario == 1:
                None        # video = encode(video, 'inv')
            elif detected_scenario == 2:
                None        # video = dxor_fast(video, count)             # ui에서 복호화 하자
            print('변형 시나리오는 %s 입니다.' % scenario_list[detected_scenario])
            sys.exit(detected_scenario)

        else:
            print('Unknown scenario or codec mismatched!', f'(inv{header_count[0]} vs x_or{header_count[1]})')
            print('Let me try the second best prediction!')

    sys.exit(0)

