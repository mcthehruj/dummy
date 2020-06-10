# 더미-히든 영상 시나리오     사용법!!

# 변조 시!! (입력인자 2 or 3개)
# 첫번째 인자: 더미 동영상 경로
# 두번째 인자: 히든 동영상 경로
# 세번째 인자(선택): 모드 ( 1 , 2 )
#                    1: 더미에 맞추기 ( 더미가 히든보다 길 경우 히든을 반복, 더미가 히든보다 짧을 경우 히든을 트림 )
#                    2: 히든에 맞추기 ( 히든이 더미보다 길 경우 더미를 반복, 히든이 더미보다 짧을 경우 더미를 트림 )
#            적지않을시: 양측 보존 ( 둘중 짧은영상을 반복하여 긴 영상 길이에 맞춤 )

# 복조 시!! (입력인자 2개)
# 첫번째인자 : 변조된 더미-히든 영상 경로
# 두번째인자 : 모드 (무조건 1 적을 것)

# 변조여부 판단 시!! (입력인자 1개)
# 첫번째인자 : 변조된 더미-히든 영상 경로


#         변조 시:  .bin파일 , .bin파일   ->   .bin파일 생성
#         복조 시:  .bin파일              ->   .yuv파일 , .bin파일 생성
# 변조여부 판단 시: .bin파일              ->    변조여부가 커멘드라인 메세지로 출력

# ex)    fakeke_enc_dec.py C:\aaa\bbb\ccc.264  C:\aaa\bbb\ddd.264      ->    ccc_ddd.264 생성
# ex)    fakeke_enc_dec.py C:\aaa\bbb\ccc.264  1                       ->    ccc_hidden.264,  ccc_hidden.yuv 생성
# ex)    fakeke_enc_dec.py C:\aaa\bbb\ccc.264                          ->    숨겨진 영상이 존재합니다.  or  숨겨진 영상이 존재하지 않습니다.  출력됨

import re
import sys
import os
import subprocess
from os.path import basename

# 더미-히든 시나리오는    더미(보여질미끼영상) 와 히든(숨길목적영상)을 하나의 264 스트림으로 만들어주는 시나리오 입니다

def codecdecision(seq):
    # 각 코덱의 스타트코드 특징 count
    d0 = b'(\x00\x00\x01[\xB0-\xB8|\x03-\x11])'                                                 # mpeg2
    d1 = b'(\x00\x00[\x80-\x8F])'                                                               # 263
    d1_ex = b'(\x80\x00\x00[\x80-\x8F])'                                                        # 263 뒤집혔을때 잘못된 start code 제외
    d2 = b'(\x00\x00\x01[\x68|\x67|\x65|\x61|\x41|\x21|\x01])'                                  # 264
    d3 = b'(\x00\x00\x01[\x40|\x41|\x42|\x43|\x44|\x4E|\x26|\x28|\x00|\x02|\x2A|\x10|\x12])'    # hevc 40, 41: VPS, 42, 43: SPS, 44: PPS, 4E: SEI, 26: IDR Frame, 뭔지 모르는 2A, 10 12 추가함
    d3_ex = b'(\x00\x00\x01\x00[\x1F|\x80|\x00])'                                               # IVC와 중복성 제거
    d4 = b'(\x00\x00\x01[\x00|\xAF|\xB0|\xB1|\xB2|\xB3|\xB6|\xB7])'                             # IVC
    seq0    = re.split(d0,    seq);  del seq0[0];    seq0    = [x + y for x, y in zip(seq0[0::2],    seq0[1::2])]
    seq1    = re.split(d1,    seq);  del seq1[0];    seq1    = [x + y for x, y in zip(seq1[0::2],    seq1[1::2])]
    seq1_ex = re.split(d1_ex, seq);  del seq1_ex[0]; seq1_ex = [x + y for x, y in zip(seq1_ex[0::2], seq1_ex[1::2])]
    seq2    = re.split(d2,    seq);  del seq2[0];    seq2    = [x + y for x, y in zip(seq2[0::2],    seq2[1::2])]
    seq3    = re.split(d3,    seq);  del seq3[0];    seq3    = [x + y for x, y in zip(seq3[0::2],    seq3[1::2])]
    seq3_ex = re.split(d3_ex, seq);  del seq3_ex[0]; seq3_ex = [x + y for x, y in zip(seq3_ex[0::2], seq3_ex[1::2])]
    seq4    = re.split(d4,    seq);  del seq4[0];    seq4    = [x + y for x, y in zip(seq4[0::2],    seq4[1::2])]

    #print("mpeg2: %d, 263: %d, 264: %d hevc: %d IVC: %d" % (len(seq0), len(seq1)-len(seq1_ex), len(seq2), len(seq3)-len(seq3_ex), len(seq4)))
    # codec 결정
    cdx = [len(seq0), len(seq1)-len(seq1_ex), len(seq2), len(seq3)-len(seq3_ex), len(seq4)].index(max([len(seq0), len(seq1)-len(seq1_ex), len(seq2), len(seq3)-len(seq3_ex), len(seq4)]))

    # 실제 사용할 start code 별로 seq split
    d0 = b'(\x00\x00\x01[\xB0-\xB5])'                                                           # mpeg2
    d1 = b'(\x00\x00[\x80-\x8F])'                                                               # 263
    d2 = b'(\x00\x00\x01[\x68|\x67|\x65|\x61|\x41|\x21|\x01])'                                  # 264
    d3 = b'(\x00\x00\x01[\x40|\x41|\x42|\x43|\x44|\x4E|\x26|\x28|\x00|\x02|\x2A|\x10|\x12])'    # hevc
    d4 = b'(\x00\x00\x01[\x00|\xAF|\xB0|\xB1|\xB2|\xB3|\xB6|\xB7])'                             # ICV
    seq0    = re.split(d0,    seq);  del seq0[0];    seq0    = [x + y for x, y in zip(seq0[0::2],    seq0[1::2])]
    seq1    = re.split(d1,    seq);  del seq1[0];    seq1    = [x + y for x, y in zip(seq1[0::2],    seq1[1::2])]
    seq2    = re.split(d2,    seq);  del seq2[0];    seq2    = [x + y for x, y in zip(seq2[0::2],    seq2[1::2])]
    seq3    = re.split(d3,    seq);  del seq3[0];    seq3    = [x + y for x, y in zip(seq3[0::2],    seq3[1::2])]
    seq4    = re.split(d4,    seq);  del seq4[0];    seq4    = [x + y for x, y in zip(seq4[0::2],    seq4[1::2])]

    return [seq0, seq1, seq2, seq3, seq4][cdx], cdx

if (len(sys.argv) == 1):   #### goto 1:변조모드로    2:복조모드로    3:변조여부판단모드로    4:인자오류메세지출력으로
    goto = 4
elif (len(sys.argv) == 2):
    goto = 3
elif (len(sys.argv) == 3):
    if sys.argv[2] == '1':
        goto = 2
    else:
        goto = 1
elif (len(sys.argv) == 4):
    goto = 1



if goto == 1:                                                                       ######################## 변조 모드
    print("변조 모드 진행 중")
    if len(sys.argv) == 3: mode = 3
    else:
        if sys.argv[3] == '1': mode = 1
        if sys.argv[3] == '2': mode = 2

    v_dum = open(sys.argv[1],'rb');   stream_d = v_dum.read()
    v_hid = open(sys.argv[2],'rb');   stream_h = v_hid.read()
    outsrc = os.path.splitext( (sys.argv[1]))[0] + '_' + os.path.splitext(basename(sys.argv[2]))[0]

    stream_d, cdx  = codecdecision(stream_d)            # 2 263 264
    stream_h, cdx2 = codecdecision(stream_h)
    if(cdx != cdx2): print("코덱을 일치시키시오"); exit(1)
    if  (cdx == 0): ext = '.m2v'
    elif(cdx == 1): ext = '.h263'
    elif(cdx == 2): ext = '.264'
    elif(cdx == 3): ext = '.hevc'
    elif(cdx == 4): ext = '.bit'    #IVC


    if cdx == 4:
        # IVC
        #[\x00|\xAF|\xB0|\xB1|\xB2|\xB3|\xB6|\xB7] # PPS: xB3,B6
        PPScnt = 0
        for i in range(len(stream_d)):   # 더미의 0x68 pps 개수 파악
            if stream_d[i][3] == 0xB3 or stream_d[i][3] == 0xB6:
                PPScnt += 1

        for i in range(len(stream_h)):                          # 히든의 pps 뒤에 사용자 종료코드 넣음.. 복조시나리오때 활용
            if stream_h[i][3] == 0xAF or stream_h[i][3] == 0xB0 or stream_h[i][3] == 0xB1 or stream_h[i][3] == 0xB2 or stream_h[i][3] == 0xB3 or stream_h[i][3] == 0xB6 or stream_h[i][3] == 0xB7:
                stream_h[i] = stream_h[i] + b'\x55\x56\x57'

        print("dum NALU: ",len(stream_d),"PPS:",PPScnt)
        print("hid NALU: ",len(stream_h))

    if cdx == 3:
        # HEVC
        # VPS: x40, x41
        # SPS: x42, x43
        # PPS: x44
        # SEI: x4E
        # IDR Frame: x26
        PPScnt = 0; SEIcnt = 0; VPScnt = 0
        for i in range(len(stream_d)):   # 더미의 0x68 pps 개수 파악
            if stream_d[i][3] == 0x44:
                PPScnt += 1
            if stream_d[i][3] == 0x4E:
                SEIcnt += 1
            if stream_d[i][3] == 0x40:
                VPScnt += 1
            if stream_d[i][3] == 0x41:
                VPScnt += 1

        for i in range(len(stream_h)):                          # 히든의 pps 뒤에 사용자 종료코드 넣음.. 복조시나리오때 활용
            if stream_h[i][3]==0x40 or stream_h[i][3]==0x41 or stream_h[i][3]==0x42 or stream_h[i][3]==0x43 or stream_h[i][3]==0x44 or stream_h[i][3]==0x4E or stream_h[i][3]==0x26 or stream_h[i][3]==0x28:
                stream_h[i] = stream_h[i] + b'\x55\x56\x57'

        for i, v in reversed(list(enumerate(stream_h))):                          # 0x4E 히든의 sei 메세지는 삭제한다
            if v[3] == 0x4E:
                del stream_h[i]

        for i, v in reversed(list(enumerate(stream_d))):                          # 0x4E 더미의 sei 메세지는 삭제한다
            if v[3] == 0x4E:
                del stream_d[i]

        print("dum NALU: ",len(stream_d),"VPS:",VPScnt,"PPS:",PPScnt, "SEI:",SEIcnt)
        print("hid NALU: ",len(stream_h))


    if cdx == 2:
        PPScnt = 0; SEIcnt = 0
        for i in range(len(stream_d)):   # 더미의 0x68 pps 개수 파악
            if stream_d[i][3] == 0x68:
                PPScnt += 1
            if stream_d[i][3] == 0x06:
                SEIcnt += 1

        for i in range(len(stream_h)):                          # 히든의 pps 뒤에 사용자 종료코드 넣음.. 복조시나리오때 활용
            if stream_h[i][3]==0x67 or stream_h[i][3]==0x68 or stream_h[i][3]==0x06:
                stream_h[i] = stream_h[i] + b'\x55\x56\x57'

        for i, v in reversed(list(enumerate(stream_h))):                          # 0x06 히든의 sei 메세지는 삭제한다
            if v[3] == 0x06:
                del stream_h[i]

        for i, v in reversed(list(enumerate(stream_d))):                          # 0x06 더미의 sei 메세지는 삭제한다
            if v[3] == 0x06:
                del stream_d[i]

        print("dum NALU: ",len(stream_d),"PPS:",PPScnt, "SEI:",SEIcnt)
        print("hid NALU: ",len(stream_h))
    if cdx == 0:
        for i in range(len(stream_h)):                          # 히든의 sps gop 뒤에 사용자 종료코드 넣음.. 복조시나리오때 활용
            if stream_h[i][3]==0xB3 or stream_h[i][3]==0xB8 :
                stream_h[i] = stream_h[i] + b'\x55\x56\x57'


    if mode == 3:                          # 양측 보존                  NALU의 개수
        if len(stream_d) > len(stream_h): itermax = len(stream_d); flag = 1
        else: itermax = len(stream_h); flag = 2
    if mode == 1:                           # 더미 보존
        itermax = len(stream_d); flag = 1
    if mode == 2:                           # 히든 보존
        itermax = len(stream_h); flag = 2

    dummy_mixed = b'' ;   vd = stream_d;  vh = stream_h
    # for i in range(len(stream_d)):
    #     vd.append(stream_d[i])
    # for i in range(len(stream_h)):
    #     vh.append(stream_h[i])

    if cdx == 2:
        ## 역히든의 에뮬레이션 방지 처리 000001 000002 000003
        for i in range(len(vh)):
            vh[i] = (re.sub(b'\x00\x00\x01', b'\xE3\x00\xD0\x01\xC5', vh[i][:2:-1]) + vh[i][:3][::-1] )[::-1]
            vh[i] = (re.sub(b'\x00\x00\x02', b'\xE3\x00\xD0\x02\xC5', vh[i][:2:-1]) + vh[i][:3][::-1] )[::-1]
            vh[i] = (re.sub(b'\x00\x00\x03', b'\xE3\x00\xD0\x03\xC5', vh[i][:2:-1]) + vh[i][:3][::-1] )[::-1]
        ## 정히든의 에뮬레이션 방지 처리 000001 000002 000003        ?!?!?!?! 이게 왜 필요하지 ?! 필요하네
        for i in range(len(vh)):
            vh[i] = vh[i][:3] + re.sub(b'\x00\x00\x01', b'\xE3\x00\xD0\x01\xC5', vh[i][3:])
            vh[i] = vh[i][:3] + re.sub(b'\x00\x00\x02', b'\xE3\x00\xD0\x02\xC5', vh[i][3:])
            vh[i] = vh[i][:3] + re.sub(b'\x00\x00\x03', b'\xE3\x00\xD0\x03\xC5', vh[i][3:])
    if cdx == 0:
        for i in range(len(vh)):
            vh[i] = (re.sub(b'\x00\x00\x01', b'\xE3\x00\xD0\x01\xC5', vh[i][:2:-1]) + vh[i][:3][::-1] )[::-1]
        for i in range(len(vh)):
            vh[i] = vh[i][:3] + re.sub(b'\x00\x00\x01', b'\xE3\x00\xD0\x01\xC5', vh[i][3:])
    if cdx == 1:
        for i in range(len(vh)):
            vh[i] = (re.sub(b'\x00\x00\x80', b'\xE3\x00\xD0\x80\xC5', vh[i][:2:-1]) + vh[i][:3][::-1] )[::-1]
        for i in range(len(vh)):
            vh[i] = vh[i][:3] + re.sub(b'\x00\x00\x80', b'\xE3\x00\xD0\x80\xC5', vh[i][3:])

        # VPS: x40, x41
        # SPS: x42, x43
        # PPS: x44
        # SEI: x4E
        # IDR Frame: x26

    aa = len(vd)
    bb = len(vh); n = 0
    if flag == 1: # 더미 길이에 맞춤
        for i in range(itermax):
            # [\x00|\xAF|\xB0|\xB1|\xB2|\xB3|\xB6|\xB7] # PPS: xB3,B6
            if (cdx == 4):
                if vd[i % aa][3] == 0xAF or vd[i % aa][3] == 0xB0 or vd[i % aa][3] == 0xB1 or vd[i % aa][3] == 0xB2 or vd[i % aa][3] == 0xB3 or vd[i % aa][3] == 0xB6 or vd[i % aa][3] == 0xB7:
                    dummy_mixed = dummy_mixed + vd[i%aa];                           n+=1
                else:
                    dummy_mixed = dummy_mixed + vd[i%aa] + vh[(i-n)%bb][::-1]
            if (cdx == 3):
                if vd[i % aa][3] == 0x40 or vd[i % aa][3] == 0x41 or vd[i % aa][3] == 0x42 or vd[i % aa][3] == 0x43 or vd[i % aa][3] == 0x44 or vd[i % aa][3] == 0x4E:
                    dummy_mixed = dummy_mixed + vd[i%aa];                           n+=1
                else:
                    dummy_mixed = dummy_mixed + vd[i%aa] + vh[(i-n)%bb][::-1]
            if (cdx == 2):
                if vd[i%aa][3] == 0x67 or vd[i%aa][3] == 0x68 or vd[i%aa][3] == 0x06:       # 더미에 pps or sei가 있으면 더미 단독으로
                    dummy_mixed = dummy_mixed + vd[i%aa];                           n+=1
                else:
                    dummy_mixed = dummy_mixed + vd[i%aa] + vh[(i-n)%bb][::-1]
            if (cdx == 0):
                if vd[i%aa][3] == 0xB3 or vd[i%aa][3] == 0xB8 :                              # SPS GOP
                    dummy_mixed = dummy_mixed + vd[i%aa];                           n+=1
                else:
                    dummy_mixed = dummy_mixed + vd[i%aa] + vh[(i-n)%bb][::-1]
            if (cdx == 1):
                dummy_mixed = dummy_mixed + vd[i%aa] + vh[(i-n)%bb][::-1]
    elif flag == 2: # 히든 길이에 맞춤
        i = 0
        while i < itermax+n: # +n의 차이만 있다.
            if (cdx == 4):
                if vd[i % aa][3] == 0xAF or vd[i % aa][3] == 0xB0 or vd[i % aa][3] == 0xB1 or vd[i % aa][3] == 0xB2 or vd[i % aa][3] == 0xB3 or vd[i % aa][3] == 0xB6 or vd[i % aa][3] == 0xB7:
                    dummy_mixed = dummy_mixed + vd[i%aa];                          i+=1; n+=1
                else:
                    dummy_mixed = dummy_mixed + vd[i%aa] + vh[(i-n)%bb][::-1];     i+=1
            if (cdx == 3):
                if vd[i % aa][3] == 0x40 or vd[i % aa][3] == 0x41 or vd[i % aa][3] == 0x42 or vd[i % aa][3] == 0x43 or vd[i % aa][3] == 0x44 or vd[i % aa][3] == 0x4E:
                    dummy_mixed = dummy_mixed + vd[i%aa];                          i+=1; n+=1
                else:
                    dummy_mixed = dummy_mixed + vd[i%aa] + vh[(i-n)%bb][::-1];     i+=1
            if (cdx == 2):
                if vd[i%aa][3] == 0x67 or vd[i%aa][3] == 0x68 or vd[i%aa][3] == 0x06:
                    dummy_mixed = dummy_mixed + vd[i%aa];                          i+=1; n+=1
                else:
                    dummy_mixed = dummy_mixed + vd[i%aa] + vh[(i-n)%bb][::-1];     i+=1
            if (cdx == 0):
                if vd[i%aa][3] == 0xB3 or vd[i%aa][3] == 0xB8 :                              # SPS GOP
                    dummy_mixed = dummy_mixed + vd[i%aa];                          i+=1; n+=1
                else:
                    dummy_mixed = dummy_mixed + vd[i%aa] + vh[(i-n)%bb][::-1];     i+=1
            if (cdx == 1):
                dummy_mixed = dummy_mixed + vd[i%aa] + vh[(i-n)%bb][::-1];     i+=1

    out = open(outsrc + ext, 'wb')
    out.write(dummy_mixed)
    v_dum.close()
    v_hid.close()
    out.close()
    print("변조 완료")


elif goto == 2:                                                                       ####################### 복조 모드
    print("복호 모드 진행 중")
    f_str = open(sys.argv[1], 'rb')
    stream = f_str.read()

    stream, cdx = codecdecision(stream)

    print(" NALU: ", len(stream))

    if (cdx == 4):
        i = 0
        while i < len(stream):
            if stream[i][3] == 0xAF or stream[i][3] == 0xB0 or stream[i][3] == 0xB1 or stream[i][3] == 0xB2 or stream[i][3] == 0xB3 or stream[i][3] == 0xB6 or stream[i][3] == 0xB7:  # 더미의 sps, pps, sei nalu 에는 히든의 데이터를 넣지 않았으므로 삭제처리
                del stream[i]; i-=1
            else:
                i += 1

    # VPS: x40, x41
    # SPS: x42, x43
    # PPS: x44
    # SEI: x4E
    # IDR Frame: x26

    if (cdx == 3):
        i = 0
        while i < len(stream):
            if stream[i][3] == 0x40 or stream[i][3] == 0x41 or stream[i][3] == 0x42 or stream[i][3] == 0x43 or stream[i][3] == 0x44 or stream[i][3] == 0x4E:  # 더미의 sps, pps, sei nalu 에는 히든의 데이터를 넣지 않았으므로 삭제처리
                del stream[i]; i-=1
            else:
                i += 1
    if (cdx == 2):
        i = 0
        while i < len(stream):
            if stream[i][3] == 0x67 or stream[i][3] == 0x68 or stream[i][3] == 0x06:  # 더미의 sps, pps, sei nalu 에는 히든의 데이터를 넣지 않았으므로 삭제처리 (264만)
                del stream[i]; i-=1
            else:
                i += 1
    if (cdx == 0):
        i = 0
        while i < len(stream):
            if stream[i][3] == 0xB3 or stream[i][3] == 0xB8:                           # 더미의 sps gop 삭제처리 (mpeg2)
                del stream[i]; i-=1
            else:
                i += 1


    if (cdx == 4):
        ## 뒤집힌 더미에서 발생하는 스타트코드 삭제처리
        for i in range(len(stream)):
            stream[i] = re.split(b'\x00\x00\x01', stream[i][-4::-1])[0][-4::-1] + stream[i][-3:]
       #     stream[i] = re.split(b'\x00\x00\x02', stream[i][-4::-1])[0][-4::-1] + stream[i][-3:]
       #     stream[i] = re.split(b'\x00\x00\x03', stream[i][-4::-1])[0][-4::-1] + stream[i][-3:]
        ## 정히든의 에뮬레이션 방지 처리 되돌리기 000001 000002 000003
        for i in range(len(stream)):
            stream[i] = re.sub(b'\xE3\x00\xD0\x01\xC5', b'\x00\x00\x01', stream[i][::-1])[::-1]
            stream[i] = re.sub(b'\xE3\x00\xD0\x02\xC5', b'\x00\x00\x02', stream[i][::-1])[::-1]
            stream[i] = re.sub(b'\xE3\x00\xD0\x03\xC5', b'\x00\x00\x03', stream[i][::-1])[::-1]
        ## 역히든의 에뮬레이션 방지 처리 되돌리기 000001 000002 000003
        for i in range(len(stream)):
            stream[i] = re.sub(b'\xE3\x00\xD0\x01\xC5', b'\x00\x00\x01', stream[i])
            stream[i] = re.sub(b'\xE3\x00\xD0\x02\xC5', b'\x00\x00\x02', stream[i])
            stream[i] = re.sub(b'\xE3\x00\xD0\x03\xC5', b'\x00\x00\x03', stream[i])

    if (cdx == 3):
        ## 뒤집힌 더미에서 발생하는 스타트코드 삭제처리
        for i in range(len(stream)):
            stream[i] = re.split(b'\x00\x00\x01', stream[i][-4::-1])[0][-4::-1] + stream[i][-3:]
       #     stream[i] = re.split(b'\x00\x00\x02', stream[i][-4::-1])[0][-4::-1] + stream[i][-3:]
       #     stream[i] = re.split(b'\x00\x00\x03', stream[i][-4::-1])[0][-4::-1] + stream[i][-3:]
        ## 정히든의 에뮬레이션 방지 처리 되돌리기 000001 000002 000003
        for i in range(len(stream)):
            stream[i] = re.sub(b'\xE3\x00\xD0\x01\xC5', b'\x00\x00\x01', stream[i][::-1])[::-1]
            stream[i] = re.sub(b'\xE3\x00\xD0\x02\xC5', b'\x00\x00\x02', stream[i][::-1])[::-1]
            stream[i] = re.sub(b'\xE3\x00\xD0\x03\xC5', b'\x00\x00\x03', stream[i][::-1])[::-1]
        ## 역히든의 에뮬레이션 방지 처리 되돌리기 000001 000002 000003
        for i in range(len(stream)):
            stream[i] = re.sub(b'\xE3\x00\xD0\x01\xC5', b'\x00\x00\x01', stream[i])
            stream[i] = re.sub(b'\xE3\x00\xD0\x02\xC5', b'\x00\x00\x02', stream[i])
            stream[i] = re.sub(b'\xE3\x00\xD0\x03\xC5', b'\x00\x00\x03', stream[i])

    if (cdx == 2):
        ## 뒤집힌 더미에서 발생하는 스타트코드 삭제처리
        for i in range(len(stream)):
            stream[i] = re.split(b'\x00\x00\x01', stream[i][-4::-1])[0][-4::-1] + stream[i][-3:]
            stream[i] = re.split(b'\x00\x00\x02', stream[i][-4::-1])[0][-4::-1] + stream[i][-3:]
            stream[i] = re.split(b'\x00\x00\x03', stream[i][-4::-1])[0][-4::-1] + stream[i][-3:]
        ## 정히든의 에뮬레이션 방지 처리 되돌리기 000001 000002 000003
        for i in range(len(stream)):
            stream[i] = re.sub(b'\xE3\x00\xD0\x01\xC5', b'\x00\x00\x01', stream[i][::-1])[::-1]
            stream[i] = re.sub(b'\xE3\x00\xD0\x02\xC5', b'\x00\x00\x02', stream[i][::-1])[::-1]
            stream[i] = re.sub(b'\xE3\x00\xD0\x03\xC5', b'\x00\x00\x03', stream[i][::-1])[::-1]
        ## 역히든의 에뮬레이션 방지 처리 되돌리기 000001 000002 000003
        for i in range(len(stream)):
            stream[i] = re.sub(b'\xE3\x00\xD0\x01\xC5', b'\x00\x00\x01', stream[i])
            stream[i] = re.sub(b'\xE3\x00\xD0\x02\xC5', b'\x00\x00\x02', stream[i])
            stream[i] = re.sub(b'\xE3\x00\xD0\x03\xC5', b'\x00\x00\x03', stream[i])
    if (cdx == 0):
        for i in range(len(stream)):        ## 뒤집힌 더미에서 발생하는 스타트코드 삭제처리
            stream[i] = re.split(b'\x00\x00\x01', stream[i][-4::-1])[0][-4::-1] + stream[i][-3:]
        for i in range(len(stream)):        ## 정히든의 에뮬레이션 방지 처리 되돌리기 000001 000002 000003
            stream[i] = re.sub(b'\xE3\x00\xD0\x01\xC5', b'\x00\x00\x01', stream[i][::-1])[::-1]
        for i in range(len(stream)):        ## 역히든의 에뮬레이션 방지 처리 되돌리기 000001 000002 000003
            stream[i] = re.sub(b'\xE3\x00\xD0\x01\xC5', b'\x00\x00\x01', stream[i])

    # VPS: x40, x41
    # SPS: x42, x43
    # PPS: x44
    # SEI: x4E
    # IDR Frame: x26

    if (cdx == 4):
        for i in range(len(stream)):
            # [\x00|\xAF|\xB0|\xB1|\xB2|\xB3|\xB6|\xB7] # PPS: xB3,B6
            if stream[i][::-1][3] == 0xAF or stream[i][::-1][3] == 0xB0 or stream[i][::-1][3] == 0xB1 or stream[i][::-1][3] == 0xB2 or stream[i][::-1][3] == 0xB3 or stream[i][::-1][3] == 0xB6 or stream[i][::-1][3] == 0xB7:  # 히든의 pps는 단독으로 써야하니 종료코드 확인해서 자른다
                stream[i] = re.split(b'\x55\x56\x57', stream[i][::-1])[0][::-1]
    if (cdx == 3):
        for i in range(len(stream)):
            if stream[i][::-1][3] == 0x40 or stream[i][::-1][3] == 0x41 or stream[i][::-1][3] == 0x42 or stream[i][::-1][3] == 0x43 or stream[i][::-1][3] == 0x44 or stream[i][::-1][3] == 0x4E:  # 히든의 pps는 단독으로 써야하니 종료코드 확인해서 자른다
                stream[i] = re.split(b'\x55\x56\x57', stream[i][::-1])[0][::-1]
    if (cdx == 2):
        for i in range(len(stream)):
            if stream[i][::-1][3] == 0x67 or stream[i][::-1][3] == 0x68 or stream[i][::-1][3] == 6:  # 히든의 pps는 단독으로 써야하니 종료코드 확인해서 자른다
                stream[i] = re.split(b'\x55\x56\x57', stream[i][::-1])[0][::-1]
    if (cdx == 0):
        for i in range(len(stream)):
            if stream[i][::-1][3] == 0xB3 or stream[i][::-1][3] == 0xB8 or stream[i][::-1][3] == 6:  # 히든의 pps는 단독으로 써야하니 종료코드 확인해서 자른다
                stream[i] = re.split(b'\x55\x56\x57', stream[i][::-1])[0][::-1]

    reversed_stream = b''
    for i in range(len(stream)):
        reversed_stream = reversed_stream + stream[i][::-1]
    if (cdx == 4): f_bin = open(os.path.splitext(sys.argv[1])[0] + '_rev.bit', 'wb'); src = "ldecod_ivc.exe "            + os.path.splitext(sys.argv[1])[0] + "_rev.bit "              + os.path.splitext(sys.argv[1])[0] + "_rev.yuv"
    if (cdx == 3): f_bin = open(os.path.splitext(sys.argv[1])[0] + '_rev.hevc', 'wb'); src = "ffmpeg.exe -y -i "          + os.path.splitext(sys.argv[1])[0] + "_rev.hevc "              + os.path.splitext(sys.argv[1])[0] + "_rev.yuv"
    if (cdx == 2): f_bin = open(os.path.splitext(sys.argv[1])[0] + '_rev.264', 'wb'); src = "ldecod.exe -p InputFile="   + os.path.splitext(sys.argv[1])[0] + "_rev.264 -p OutputFile=" + os.path.splitext(sys.argv[1])[0] + "_rev.yuv"
    if (cdx == 0): f_bin = open(os.path.splitext(sys.argv[1])[0] + '_rev.m2v', 'wb'); src = "ffmpeg.exe -y -i "           + os.path.splitext(sys.argv[1])[0] + "_rev.m2v "               + os.path.splitext(sys.argv[1])[0] + "_rev.yuv"
    if (cdx == 1): f_bin = open(os.path.splitext(sys.argv[1])[0] + '_rev.h263','wb'); src = "ffmpeg.exe -y -i "           + os.path.splitext(sys.argv[1])[0] + "_rev.h263 "              + os.path.splitext(sys.argv[1])[0] + "_rev.yuv"

    f_bin.write(reversed_stream)        # 히든 스트림 만드는것
    #subprocess.call(src)                # 디코딩해서 yuv만드는 것
    f_bin.close()
    f_str.close()


elif goto == 3:                                                                       ####################### 변조여부 확인모드
    f_str = open(sys.argv[1], 'rb');
    stream = f_str.read()

    stream, cdx = codecdecision(stream)


    # VPS: x40, x41
    # SPS: x42, x43
    # PPS: x44
    # SEI: x4E
    # IDR Frame: x26



    tta = len(stream);

    if (cdx == 4):
        ## 뒤집힌 더미에서 발생하는 스타트코드 삭제처리
        for i in range(len(stream)):
            stream[i] = re.split(b'\x00\x00\x01', stream[i][-4::-1])[0][-4::-1] + stream[i][-3:]
       #     stream[i] = re.split(b'\x00\x00\x02', stream[i][-4::-1])[0][-4::-1] + stream[i][-3:]
       #     stream[i] = re.split(b'\x00\x00\x03', stream[i][-4::-1])[0][-4::-1] + stream[i][-3:]
        ## 정히든의 에뮬레이션 방지 처리 되돌리기 000001 000002 000003
        for i in range(len(stream)):
            stream[i] = re.sub(b'\xE3\x00\xD0\x01\xC5', b'\x00\x00\x01', stream[i][::-1])[::-1]
            stream[i] = re.sub(b'\xE3\x00\xD0\x02\xC5', b'\x00\x00\x02', stream[i][::-1])[::-1]
            stream[i] = re.sub(b'\xE3\x00\xD0\x03\xC5', b'\x00\x00\x03', stream[i][::-1])[::-1]
        ## 역히든의 에뮬레이션 방지 처리 되돌리기 000001 000002 000003
        for i in range(len(stream)):
            stream[i] = re.sub(b'\xE3\x00\xD0\x01\xC5', b'\x00\x00\x01', stream[i])
            stream[i] = re.sub(b'\xE3\x00\xD0\x02\xC5', b'\x00\x00\x02', stream[i])
            stream[i] = re.sub(b'\xE3\x00\xD0\x03\xC5', b'\x00\x00\x03', stream[i])
    if (cdx == 3):
        ## 뒤집힌 더미에서 발생하는 스타트코드 삭제처리
        for i in range(len(stream)):
            stream[i] = re.split(b'\x00\x00\x01', stream[i][-4::-1])[0][-4::-1] + stream[i][-3:]
       #     stream[i] = re.split(b'\x00\x00\x02', stream[i][-4::-1])[0][-4::-1] + stream[i][-3:]
       #     stream[i] = re.split(b'\x00\x00\x03', stream[i][-4::-1])[0][-4::-1] + stream[i][-3:]
        ## 정히든의 에뮬레이션 방지 처리 되돌리기 000001 000002 000003
        for i in range(len(stream)):
            stream[i] = re.sub(b'\xE3\x00\xD0\x01\xC5', b'\x00\x00\x01', stream[i][::-1])[::-1]
            stream[i] = re.sub(b'\xE3\x00\xD0\x02\xC5', b'\x00\x00\x02', stream[i][::-1])[::-1]
            stream[i] = re.sub(b'\xE3\x00\xD0\x03\xC5', b'\x00\x00\x03', stream[i][::-1])[::-1]
        ## 역히든의 에뮬레이션 방지 처리 되돌리기 000001 000002 000003
        for i in range(len(stream)):
            stream[i] = re.sub(b'\xE3\x00\xD0\x01\xC5', b'\x00\x00\x01', stream[i])
            stream[i] = re.sub(b'\xE3\x00\xD0\x02\xC5', b'\x00\x00\x02', stream[i])
            stream[i] = re.sub(b'\xE3\x00\xD0\x03\xC5', b'\x00\x00\x03', stream[i])
    if (cdx == 2):
        ## 뒤집힌 더미에서 발생하는 스타트코드 삭제처리
        for i in range(len(stream)):
            stream[i] = re.split(b'\x00\x00\x01', stream[i][-4::-1])[0][-4::-1] + stream[i][-3:]
            stream[i] = re.split(b'\x00\x00\x02', stream[i][-4::-1])[0][-4::-1] + stream[i][-3:]
            stream[i] = re.split(b'\x00\x00\x03', stream[i][-4::-1])[0][-4::-1] + stream[i][-3:]
        ## 정히든의 에뮬레이션 방지 처리 되돌리기 000001 000002 000003
        for i in range(len(stream)):
            stream[i] = re.sub(b'\xE3\x00\xD0\x01\xC5', b'\x00\x00\x01', stream[i][::-1])[::-1]
            stream[i] = re.sub(b'\xE3\x00\xD0\x02\xC5', b'\x00\x00\x02', stream[i][::-1])[::-1]
            stream[i] = re.sub(b'\xE3\x00\xD0\x03\xC5', b'\x00\x00\x03', stream[i][::-1])[::-1]
        ## 역히든의 에뮬레이션 방지 처리 되돌리기 000001 000002 000003
        for i in range(len(stream)):
            stream[i] = re.sub(b'\xE3\x00\xD0\x01\xC5', b'\x00\x00\x01', stream[i])
            stream[i] = re.sub(b'\xE3\x00\xD0\x02\xC5', b'\x00\x00\x02', stream[i])
            stream[i] = re.sub(b'\xE3\x00\xD0\x03\xC5', b'\x00\x00\x03', stream[i])
    if (cdx == 0):
        for i in range(len(stream)):        ## 뒤집힌 더미에서 발생하는 스타트코드 삭제처리
            stream[i] = re.split(b'\x00\x00\x01', stream[i][-4::-1])[0][-4::-1] + stream[i][-3:]
        for i in range(len(stream)):        ## 정히든의 에뮬레이션 방지 처리 되돌리기 000001 000002 000003
            stream[i] = re.sub(b'\xE3\x00\xD0\x01\xC5', b'\x00\x00\x01', stream[i][::-1])[::-1]
        for i in range(len(stream)):        ## 역히든의 에뮬레이션 방지 처리 되돌리기 000001 000002 000003
            stream[i] = re.sub(b'\xE3\x00\xD0\x01\xC5', b'\x00\x00\x01', stream[i])


    ttb = 0
    d0 = b'(\x00\x00\x01[\xB0-\xB5])'  # mpeg2
    d1 = b'(\x00\x00[\x80-\x8F])'  # 263
    d1_ex = b'(\x80\x00\x00[\x80-\x8F])'
    d2 = b'(\x00\x00\x01[\x68|\x67|\x65|\x61|\x41|\x21|\x01])'  # 264
    d3 = b'(\x00\x00\x01[\x40|\x41|\x42|\x43|\x44|\x4E|\x26|\x28|\x00|\x02|\x2A|\x10|\x12])'  # hevc 40, 41: VPS, 42, 43: SPS, 44: PPS, 4E: SEI, 26: IDR Frame
    d3_ex = b'(\x00\x00\x01\x00[\x1F|\x01|\x80|\x00])'
    d4 = b'(\x00\x00\x01[\x00|\xAF|\xB0|\xB1|\xB2|\xB3|\xB6|\xB7])'  # IVC


    for i in range(len(stream)):
        if cdx is 0:
            try:
                if re.match(d0, stream[i][::-1]).lastindex is 1: ttb += 1
            except: pass
        if cdx is 1:
            try:
                if re.match(d1, stream[i][::-1]).lastindex is 1: ttb += 1
            except: pass
        if cdx is 2:
            try:
                if re.match(d2, stream[i][::-1]).lastindex is 1: ttb += 1
            except: pass
        if cdx is 3:
            try:
                if re.match(d3, stream[i][::-1]).lastindex is 1: ttb += 1
            except: pass
        if cdx is 4:
            try:
                if re.match(d4, stream[i][::-1]).lastindex is 1: ttb += 1
            except: pass


    tta +=1
    if (ttb / tta) > 0.4:
        print("(NALU: %d  ratio: %.2f)" % (tta, ttb / tta), "scenario found: dummy-hidden.")
    else:
        #print("(NALU: %d  ratio: %.2f)" % (tta, ttb / tta), "숨겨진 영상이 존재하지 않습니다.")  # 없을땐 보이지 않도록하자 (임시)
        None


elif goto == 4:                                                                       ####################### 오류 메세지 출력
    print(""" !!입력인자 오류!!m
변조 시!! (입력인자 2 or 3개)
첫번째 인자: 더미 동영상 경로
두번째 인자: 히든 동영상 경로
세번째 인자(선택): 모드 ( 1 , 2 )
                   1: 더미에 맞추기 ( 더미가 히든보다 길 경우 히든을 반복, 더미가 히든보다 짧을 경우 히든을 트림 )
                   2: 히든에 맞추기 ( 히든이 더미보다 길 경우 더미를 반복, 히든이 더미보다 짧을 경우 더미를 트림 )
           적지않을시: 양측 보존 ( 둘중 짧은영상을 반복하여 긴 영상 길이에 맞춤 )

복조 시!! (입력인자 2개)
첫번째인자 : 변조된 더미-히든 영상 경로
두번째인자 : 모드 (무조건 1 적을 것)

변조여부 판단 시!! (입력인자 1개)
첫번째인자 : 변조된 더미-히든 영상 경로


        변조 시:  .bin파일 , .bin파일   ->   .bin파일 생성
        복조 시:  .bin파일              ->   .yuv파일 , .bin파일 생성
변조여부 판단 시: .bin파일              ->    변조여부가 커멘드라인 메세지로 출력

ex)    fakeke_enc_dec.py C:\aaa\bbb\ccc.264  C:\aaa\bbb\ddd.264      ->    ccc_ddd.264 생성
ex)    fakeke_enc_dec.py C:\aaa\bbb\ccc.264  1                       ->    ccc_hidden.264,  ccc_hidden.yuv 생성
ex)    fakeke_enc_dec.py C:\aaa\bbb\ccc.264                          ->    숨겨진 영상이 존재합니다.  or  숨겨진 영상이 존재하지 않습니다.  출력됨""")



