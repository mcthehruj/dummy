import os, glob
import winsound
import threading
import tkinter.messagebox
from tkinter.filedialog import askopenfilename, askopenfilenames
from tkinter import *
from tkinter.ttk import *
import subprocess

import PIL.Image
import PIL.ImageTk
import cv2
from utils import *
import tiff_scenario, png_scenario, bmp_scenario


class VideoCaptureYUV:
    def __init__(self, filename, size):
        self.height, self.width = size
        self.frame_len = self.width * self.height * 3 / 2
        self.f = open(filename, 'rb')
        self.shape = (int(self.height * 1.5), self.width)

    def isOpened(self):
        return 0

    def read_raw(self):
        try:
            raw = self.f.read(int(self.frame_len))
            yuv = np.frombuffer(raw, dtype=np.uint8)
            yuv = yuv.reshape(self.shape)
        except Exception as e:
            print(str(e))
            return False, None
        return True, yuv

    def read(self):
        ret, yuv = self.read_raw()
        if not ret:
            return ret, yuv
        bgr = cv2.cvtColor(yuv, cv2.COLOR_YUV420p2BGR)
        return ret, bgr


class LoadDisplay(object):  # ui 영상창 클래스
    # 추가해야할 디스플레이 클래스 기능: 프로그래스바, 모든비디오시퀀스가 33ms의 프레임레이트를 가지는문제, 드래그시 클릭되는 문제
    pausedisplay = 1  # 클래스간 공통변수
    progressbar = 0

    def __init__(self, win, x, y):
        self.win = win
        self.frame = None
        self.frame_count = 0.99
        self.x = x
        self.y = y
        self.f_width = 352
        self.f_height = 288
        self.video_source = ''
        self.move_x = 0
        self.move_y = 0
        self.zoom_x = 1
        self.zoom_y = 1
        self.vid = cv2.VideoCapture(self.video_source)
        self.i_width = 55555
        self.i_height = 55555
        self.name = ""

        if not self.vid.isOpened():
            pass  # raise ValueError("Unable", self.video_source)
        else:
            pass  # self.width = self.vid.get(cv2.CAP_PROP_FRAME_WIDTH)
        self.canvas = tkinter.Canvas(self.win, width=self.f_width, height=self.f_height, bg="white", bd=0, highlightthickness=0, relief='ridge')
        self.canvas.pack(pady=(3, 1), padx=(1, 2))

        self.canvas.bind("<Button-1>", self.l_click)
        self.canvas.bind("<Button-3>", self.r_click)
        self.canvas.bind("<B1-Motion>", self.drag)
        self.canvas.bind("<space>", self.keypress)
        self.canvas.bind("<ButtonRelease-1>", self.l_click_off)
        self.canvas.bind("<MouseWheel>", self.mousewheel)

        self.delay = 33
        self.update()

        self.r_popup = Menu(window, tearoff=0)
        self.r_popup.add_command(label="x0.5", command=lambda: self.zoom_change(0.5))
        self.r_popup.add_command(label="x1.0", command=lambda: self.zoom_change(1.0))
        self.r_popup.add_command(label="x1.5", command=lambda: self.zoom_change(1.5))
        self.r_popup.add_command(label="x2.0", command=lambda: self.zoom_change(2.0))

    def __del__(self):
        if self.vid.isOpened():
            self.vid.release()

    def zoom_change(self, zoom):
        if zoom == 1.0:
            self.move_x = 0
            self.move_y = 0
        self.zoom_x = zoom
        self.zoom_y = zoom
        frame = cv2.resize(self.frame, None, fx=self.zoom_x, fy=self.zoom_y, interpolation=cv2.INTER_LINEAR)

    def changevideo(self, src=''):

        def set_srctext_and_return(s):
            srctext = os.path.basename(s)               # 파일이름 출력용
            text = self.win.children['!text']
            text.configure(state='normal')
            text.delete(1.0, END)
            text.insert(END, srctext)
            text.tag_add('cen', 1.0, END)               # 가운데정렬
            text.tag_config('cen', justify='center')    # 가운데정렬
            text.configure(state='disabled')
            canvas_loading.forget()
            return s

        LoadDisplay.pausedisplay = 1
        if src == '':
            tem = askopenfilename(initialdir="", filetypes=(("All", "*.*"), ("All Files", "*.*")), title="Choose a file.")
            if tem == '':
                return ''  # ask 창 cancel 한 경우
            self.video_source = tem
        elif src == 'close':
            self.vid = cv2.VideoCapture('clod.png')
            print('디스플레이 닫기')
            ret, self.frame = self.get_frame()
            self.vid.release()
            return set_srctext_and_return('')
        else:
            self.video_source = src

        canvas_loading.show()
        if self.vid.isOpened():
            self.vid.release()  # 만약 클래스에 이전 영상이 열려있다면, 소멸처리
        self.vid = cv2.VideoCapture(self.video_source)
        self.name = os.path.splitext(self.video_source)[1]

        if not self.vid.isOpened():  # 열리지 않았다면
            if os.path.isfile(self.video_source):  ## 영상 존재   png,  YUV 케이스?
                print('(debug) imread로 시도')
                self.frame = cv2.imread(self.video_source)
                if self.frame is not None:  # imread로 열기 성공
                    b, g, r = cv2.split(self.frame)
                    self.frame = cv2.merge([r, g, b])
                    self.i_width = self.frame.shape[1]
                    self.i_height = self.frame.shape[0]
                    ratio = 352 / self.i_width
                    self.zoom_x = ratio
                    self.zoom_y = ratio
                    self.move_x = 0
                    self.move_y = 0
                    self.frame = cv2.resize(self.frame, None, fx=1, fy=1, interpolation=cv2.INTER_LINEAR)
                    self.frame_num_p = 0
                    window.update()
                    time.sleep(0.01)
                    sli1.set(0)
                    sli2.set(0)
                    canvas_loading.forget()
                    return set_srctext_and_return(self.video_source)
                else:  # imread로 열기 실패
                    if '.yuv' in self.video_source:
                        self.vid = VideoCaptureYUV(self.video_source, (288, 352))
                        ret, self.frame = self.vid.read()
                        print_dual(self.canvas.master.master.children['!labelframe3'].children['!text'], "(debug) YUV 열기 완료, 이미지는 보이나 인코딩된 상태가 아니기 때문에 시나리오 적용 불가")
                        return set_srctext_and_return(self.video_source)
                    else:
                        # print_dual(self.canvas.master.master.children['!labelframe3'].children['!text'], "(debug) 무엇을 연것?")
                        self.vid = cv2.VideoCapture('errd2.png')
                        print('오류디스플레이 출력')
                        ret, self.frame = self.get_frame()
            else:
                print("@@@@@@@@@@@@@@@@@@@@@@@@@@@")  ## 영상 노존재
                print("error, file not exist in %s" % self.video_source)
                ## 에러영상 메세지 디스플레이기능 넣기
                self.video_source = ""
                return set_srctext_and_return('')

        else:  # vid.isOpened True 일때:  영상 정보를 얻자
            ret, self.frame = self.get_frame()  # 동영상의 초기 1프레임 얻어 띄우기
            if self.frame is None:  ## 파일은 존재하지만 디코딩이 안됐단뜻    ## IVC 디코더로 시도
                self.vid.release()
                print("IVC 디코더로 시도")
                subprocess.run("ldecod_ivc.exe %s 1t_youcandelete_%s" % (self.video_source, os.path.basename(self.video_source)), stdout=subprocess.DEVNULL)  # 현재폴더에 재인코딩된 임시파일 생성
                yuv_src = '1t_youcandelete_' + os.path.basename(self.video_source)
                subprocess.run("ffmpeg.exe -f rawvideo -s 352x288 -pix_fmt yuv420p -i %s -c:v hevc -y %s.hevc" % (yuv_src, os.path.splitext(yuv_src)[0]), stdout=subprocess.DEVNULL)
                # if os.path.isfile(os.path.splitext(yuv_src)[0] + '.hevc'): 파일이존재하지않을이유는없을걸
                if os.path.getsize(os.path.splitext(yuv_src)[0] + '.hevc') > 1:
                    self.vid = cv2.VideoCapture(os.path.splitext(yuv_src)[0] + '.hevc')
                else:
                    self.vid = cv2.VideoCapture('errd1.png')
                    print('오류디스플레이 출력')  ## ivc디코더로도 안뜬다면 시퀀스는 에러영상 일것임     화면상에 에러 메세지로 디스플레이기능 넣기
                ret, self.frame = self.get_frame()
            self.frame_count = self.vid.get(cv2.CAP_PROP_FRAME_COUNT)  ##### 정리좀 할것
            if self.frame_count < 1 or self.frame_count > 30000:  # 음수거나 너무크면
                self.frame_count = 300
                self.vid.set(7, 300)
                print('프레임카운트 헤더에 오류가 있음', self.frame_count, '으로 변경')
        self.i_width = self.vid.get(3)
        self.i_height = self.vid.get(4)
        ratio = 352 / self.i_width
        self.zoom_x = ratio
        self.zoom_y = ratio
        self.move_x = 0
        self.move_y = 0
        self.frame = cv2.resize(self.frame, None, fx=1, fy=1, interpolation=cv2.INTER_LINEAR)
        self.frame_num_p = 0
        window.update()
        time.sleep(0.01)
        sli1.set(0)
        sli2.set(0)
        return set_srctext_and_return(self.video_source)

    def get_frame(self):
        if self.vid.isOpened():  # self.vid.set(cv2.CV_CAP_PROP_POS_FRAMES, frame_number - 1)
            try:
                ret, frame = self.vid.read()  # cv가 코덱모를경우 에러뿜음
            except:
                None
            LoadDisplay.progressbar = self.vid.get(cv2.CAP_PROP_POS_FRAMES)
            if ret:
                return 2, cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)  # success
            else:
                self.vid = cv2.VideoCapture(self.video_source)  # opencv 이상한게 프레임 재생 할당량만 채우면 종료되버리네 ㄷ  bit은 오류날듯
                LoadDisplay.pausedisplay = 1
                return 3, None  # 시퀀스 끝 빈 프레임
        else:
            return 0, 0  # 초기 init 상태

    def update(self):
        if LoadDisplay.pausedisplay == 1:
            ret = 3  # pause 기능
        else:
            ret, temframe = self.get_frame()  # Get a frame from the video source
            cur = self.vid.get(1)
            if self.frame_count < cur: self.frame_count = cur
            if self.canvas.master.winfo_name() == '!labelframe':  # labelframe2는 우측 디스플레이임, 즉 좌측디스플레이 기준으로 슬라이드가 움직인다
                self.canvas.master.master.children['!scale'].set((cur / self.frame_count) * 100)

        if ret == 2:  # 일반 재생 시
            self.frame = temframe
            temframe = cv2.resize(temframe, None, fx=self.zoom_x, fy=self.zoom_y, interpolation=cv2.INTER_LINEAR)
            self.photo = PIL.ImageTk.PhotoImage(image=PIL.Image.fromarray(temframe))
            self.canvas.create_image(self.move_x, self.move_y, image=self.photo, anchor=tkinter.NW)
        if ret == 3:  # 영상의 끝일때 마지막 프레임을 재생하도록
            if self.frame is None:
                pass
            else:
                temframe = cv2.resize(self.frame, None, fx=self.zoom_x, fy=self.zoom_y, interpolation=cv2.INTER_LINEAR)
                self.photo = PIL.ImageTk.PhotoImage(image=PIL.Image.fromarray(temframe))
                self.canvas.create_image(self.move_x, self.move_y, image=self.photo, anchor=tkinter.NW)
        window.after(self.delay, self.update)  # 반복 호출

    def l_click(self, event):
        self.lock_x = -self.move_x + event.x
        self.lock_y = -self.move_y + event.y

    def r_click(self, event):
        try:
            self.r_popup.tk_popup(event.x_root + 30, event.y_root + 10, 0)
        finally:
            self.r_popup.grab_release()
        pass

    def drag(self, event):
        self.move_x = - (self.lock_x - event.x)
        self.move_y = - (self.lock_y - event.y)

    def keypress(self, event):  # canvas 에선 작동안하나봄
        kp = repr(event.char)
        print("pressed", kp)  # repr(event.char))
        if (kp == 'x'):
            print("pressed x", repr(event.char))

    def l_click_off(self, event):
        if self.lock_x == -self.move_x + event.x and self.lock_y == -self.move_y + event.y:
            if LoadDisplay.pausedisplay == 1:
                LoadDisplay.pausedisplay = 0
            else:
                LoadDisplay.pausedisplay = 1

    def mousewheel(self, event):
        if event.delta > 0:
            self.move_x = self.move_x - (self.i_width * self.zoom_x) * 0.125 + 2.5
            self.move_y = self.move_y - (self.i_height * self.zoom_y) * 0.125 + 2.5
            self.zoom_x = self.zoom_x * 1.333333
            self.zoom_y = self.zoom_y * 1.333333
        else:
            self.move_x = self.move_x + (self.i_width * self.zoom_x) * 0.125 - 2.5
            self.move_y = self.move_y + (self.i_height * self.zoom_y) * 0.125 - 2.5
            self.zoom_x = self.zoom_x * 0.750000
            self.zoom_y = self.zoom_y * 0.750000

    def touch_slide(self, event):
        if self.vid.isOpened():
            self.vid.set(cv2.CAP_PROP_POS_FRAMES, LoadDisplay.progressbar)


def set_slider(slidername, *args):
    t = 0
    for i in args:
        if t < i.frame_count:
            t = i.frame_count


def print_dual(text, aa):
    now = datetime.now()
    print('[%d.%02d.%02d %d:%02d:%02d]' % (now.year, now.month, now.day, now.hour, now.minute, now.second), end='')
    text.insert(END, '[%d.%02d.%02d %d:%02d:%02d]' % (now.year, now.month, now.day, now.hour, now.minute, now.second))
    print(aa)
    if aa == '': return;
    if type(aa) == str: text.insert(END, aa + '\n')
    if type(aa) == list:
        print_dual_nocl(text, '   frequency is [')
        for a in aa:
            print_dual_nocl(text, '%d, ' % (a))
        print_dual_nocl(text, ']\n')
    text.see(END)
    text.update()


def print_dual_nocl(text, aa):
    print(aa, end='')
    if type(aa) == str: text.insert(END, aa)
    if type(aa) == list:
        print_dual_nocl(text, '   frequency is [')
        for a in aa:
            print_dual_nocl(text, '%d, ' % (a))
        print_dual_nocl(text, ']\n')
    text.update()


def non_block_threding_popen(text, src, encoding='utf-8'):  # stdout를 read로 읽으면 먹통되는 현상 고치는 함수
    from queue import Queue
    def enqueue_output(out, queue):
        try:
            for line in iter(out.readline, b''):
                queue.put(line)
        except:
            return  # print("탈출");

    def time_write():
        for n in range(2, 20):
            tem = text.get('end-%dlines' % n, 'end-%dlines' % (n - 1))
            if tem == '': break
            if tem[0] != '[':
                now = datetime.now()
                text.insert('end-%dlines' % n, '[%d.%02d.%02d %d:%02d:%02d]' % (now.year, now.month, now.day, now.hour, now.minute, now.second))

    LoadDisplay.pausedisplay = 1
    canvas_loading.show()
    p = subprocess.Popen(src, encoding=encoding, stdout=subprocess.PIPE)
    q = Queue()
    t = threading.Thread(target=enqueue_output, args=(p.stdout, q))
    t.daemon = True
    t.start()

    while p.poll() is None:  # read line without blocking
        try:
            line = q.get(timeout=.03)  # or q.get(timeout=.1)
        except:
            time_write()
            text.see(END)
            window.update()  # print('no output yet')
        else:  # got line
            text.insert(END, line)
            continue
    time.sleep(0.01)
    p.stdout.close()  # 개거지같은 파이썬
    time_write()
    text.see(END)
    canvas_loading.forget()


#########################################################################################################
#########################################################################################################
#########################################################################################################
#########################################################################################################
def srcs_g(a):
    srcs_g.count = a



#                           가능 코덱
# "Scenario-1 inverse"          모두
# "Scenario-2 xor"              모두
# "Scenario-3 더미-히든"         mpeg2 263 264 hevc ivc        (vp8 제외)
# "Scenario-4 start code"      mpeg2 264 hevc ivc            (vp8 263 제외)
# "Scenario-5 jpg, j2k"        jpg j2k
# "Scenario-6 bmp"             bmp
# "Scenario-7 png"             png
# "Scenario-8 tiff"            tiff
# * vp8 = webm , ivc = bit

def scenario_act(event):  ### 변조과정 ###                  # 이 함수는 input stream 버튼을 눌러도 호출되고 combobox를 선택해도 호출됨 event 인자의 차이
    if event == 'askmode':          # input stream 버튼을 통한 접근시
        srcs_g.count = askopenfilenames(initialdir="", filetypes=(("All", "*.*"), ("All Files", "*.*")), title="Choose a file.")
        srcs = srcs_g.count
        if len(srcs) == 0:      # 사용자가 ask 창을 캔슬 누른 경우 아웃
            frame1.children['!combobox']['values'] = ("Scenario-1 inverse", "Scenario-2 xor", "Scenario-3 더미-히든", "Scenario-4 start code", "Scenario-5 jpg, j2k", "Scenario-6 bmp", "Scenario-7 png", "Scenario-8 tiff")
            return
        if len(srcs) >= 1:      # 하나 선택한경우 보여주기만 하고 아웃  두개이상 선택한 경우 첫번째 파일의 화면만 보여주고 아웃
            c_i = ["Scenario-1 inverse" , "Scenario-2 xor", ' ', ' ', ' ', ' ', ' ', ' ']
            for s in srcs:
                ext = os.path.splitext(s)[1]
                if '.jpg'  in ext or '.j2k' in ext: c_i[4] = "Scenario-5 jpg, j2k"
                if '.bmp'  in ext: c_i[5] = "Scenario-6 bmp"
                if '.png'  in ext: c_i[6] = "Scenario-7 png"
                if '.tiff' in ext: c_i[7] = "Scenario-8 tiff"
                if '.m2v'  in ext: c_i[2] = "Scenario-3 더미-히든"; c_i[3] = "Scenario-4 start code";
                if '.263'  in ext: c_i[2] = "Scenario-3 더미-히든"
                if '.264'  in ext: c_i[2] = "Scenario-3 더미-히든"; c_i[3] = "Scenario-4 start code";
                if '.hevc' in ext: c_i[2] = "Scenario-3 더미-히든"; c_i[3] = "Scenario-4 start code";
                if '.bit'  in ext: c_i[2] = "Scenario-3 더미-히든"; c_i[3] = "Scenario-4 start code";
            while ' '  in c_i: c_i.remove(' ')           # 빈 리스트 제거
            frame1.children['!combobox']['values'] = c_i
            print_dual(text_1_3, f' {len(srcs)}개의 입력 영상을 선택하였습니다.  ')
            vid1.changevideo(srcs[0])
            return


    # combobox 리스트를 통한 접근시
    srcs = srcs_g.count
    if len(srcs) == 0:  return     # 입력영상을 아직 선택하지 않았을 경우 그냥 아웃

    for iii, seq1 in enumerate(srcs):
        if seq1 == '' and event.widget.current() != 9:
            print_dual(text_1_3, 'input stream을 지정해 주세요')
            return
        src_plus_name = os.path.splitext(seq1)[0]   # 파일경로+파일이름
        ext = os.path.splitext(seq1)[1]             # 확장자
        name = os.path.basename(src_plus_name)      # 파일이름

        print_dual(text_1_3, f'({iii + 1}/{len(srcs)}) {name}{ext}')
        vid1.changevideo(seq1)                      # 입력영상 띄우기

        if 'Scenario-1' in event.widget.get():  ## 시나리오1 inverse 변조
            print_dual(text_1_3, 'inverse 변조 중입니다..')
            bits_inv = bitstring.BitStream(~bitstring.Bits(filename=seq1))
            bits_inv.tofile(open(src_plus_name + '_inv' + ext, 'wb'))  # 경로/seq.확장자 -> 경로/seq_inv.확장자
            vid2.changevideo(src_plus_name + '_inv' + ext)
            print_dual(text_1_3, '변조가 완료되었습니다.')

        elif 'Scenario-2' in event.widget.get():  ## 시나리오2 xor 변조
            print_dual(text_1_3, 'xor 변조 중입니다..')
            bitstream = bitstring.ConstBitStream(filename=seq1)
            bitstream = xor_fast_bitstream(bitstream)
            (open(src_plus_name + '_xor' + ext, 'wb')).write(bitstream)  # 경로/seq.확장자 -> 경로/seq_xor.확장자
            vid2.changevideo(src_plus_name + '_xor' + ext)
            print_dual(text_1_3, '변조가 완료되었습니다.')

        elif 'Scenario-3' in event.widget.get():  ## 시나리오3 더미-히든 변조               현재 mpeg2,263,264,265,IVC 만 지원 됨
            if ext in 'webm': print_dual(text_1_3, 'vp8 은 더미-히든 변조를 지원하지 않습니다'); continue
            if ext in ['jpg', 'j2k', 'bmp', 'tiff', 'png']: print_dual(text_1_3, '이미지 포멧은 더미-히든 변조를 지원하지 않습니다'); continue
            print_dual(text_1_3, '숨길 영상을 추가로 선택 해 주세요')
            seq2 = askopenfilename(initialdir="", filetypes=(("All", "*.*"), ("All Files", "*.*")), title="Choose a file.")  # 더미-히든 변조과정에 필요한 추가시퀀스(히든) 열기
            if seq2 == '': print_dual(text_1_3, '추가 영상을 선택하지 않아 취소되었습니다'); continue
            print_dual(text_1_3, '더미-히든 변조 중입니다..')
            non_block_threding_popen(text_1_3, "python.exe fakeke_enc_dec.py %s %s" % (seq1, seq2))  # 더미-히든 시나리오 변조 실행
            seq3 = os.path.splitext(seq1)[0] + '_' + os.path.basename(seq2)
            vid2.changevideo(seq3) if os.path.isfile(seq3) else print_dual(text_1_3, '%s 존재하지 않음' % seq3)  # 더미-히든 실행 후 완료된 파일 vid2에 띄우기
            print_dual(text_1_3, '변조가 완료되었습니다.')

        elif 'Scenario-4' in event.widget.get():  ## 시나리오4 header 변조
            if ext in ['webm', 'bit']: print_dual(text_1_3, 'vp8 은 header변조를 지원하지 않습니다'); continue
            if ext in ['jpg', 'j2k', 'bmp', 'tiff', 'png']: print_dual(text_1_3, '이미지 포멧은 header변조를 지원하지 않습니다'); continue
            print_dual(text_1_3, 'header 변조 중입니다..')
            if subprocess.call("start_code_encryptor.exe %s" % seq1) == 0: vid2.changevideo(seq1 + '.st'); print_dual(text_1_3, '변조가 완료되었습니다.')
            else: print_dual(text_1_3, 'header 변조 불가한 비트스트림입니다.')

        elif 'Scenario-5' in event.widget.get():  ## 시나리오5 JPEG 양자화 테이블 변조
            print_dual(text_1_3, 'JPEG 양자화 테이블 변조 중입니다.')
            if ext in ['.jpg', '.j2k']:
                try:
                    non_block_threding_popen(text_1_3, "python.exe JPEG.py %s %d" % (seq1, 0))
                    seq2 = src_plus_name + '_Distorted' + ext
                    vid2.changevideo(seq2) if os.path.isfile(seq2) else print_dual(text_1_3, '%s 존재하지 않음' % seq2)
                except:
                    print_dual(text_1_3, 'JPEG 양자화 테이블 변조가 불가합니다.')
            else:
                print_dual(text_1_3, '입력 영상이 \'JPEG\' 영상이 아닙니다.')

        elif 'Scenario-6' in event.widget.get():  ## 시나리오6 BMP 변조
            print_dual(text_1_3, 'BMP 변조 중입니다..')
            if ext in ['.bmp']:
                try:
                    non_block_threding_popen(text_1_3, "python.exe bmp_scenario.py %s %d" % (seq1, 0))
                    seq2 = src_plus_name + '_Distorted' + ext
                    vid2.changevideo(seq2) if os.path.isfile(seq2) else print_dual(text_1_3, '%s 존재하지 않음' % seq2)
                except:
                    print_dual(text_1_3, 'BMP 변조가 불가합니다.')
            else:
                print_dual(text_1_3, '입력 영상이 \'BMP\' 영상이 아닙니다.')

        elif 'Scenario-7' in event.widget.get():  ## 시나리오7 PNG 변조
            print_dual(text_1_3, 'PNG 변조 중입니다..')
            if ext in ['.png']:
                try:
                    non_block_threding_popen(text_1_3, "python.exe png_scenario.py %s %d" % (seq1, 0))
                    seq2 = src_plus_name + '_Distorted' + ext
                    vid2.changevideo(seq2) if os.path.isfile(seq2) else print_dual(text_1_3, '%s 존재하지 않음' % seq2)
                except:
                    print_dual(text_1_3, 'PNG 변조가 불가합니다.')
            else:
                print_dual(text_1_3, '입력 영상이 \'PNG\' 영상이 아닙니다.')

        elif 'Scenario-8' in event.widget.get():  ## 시나리오8 TIFF 변조
            print_dual(text_1_3, 'TIFF 변조 중입니다..')
            if ext in ['.tiff']:
                try:
                    non_block_threding_popen(text_1_3, "python.exe tiff_scenario.py %s %d" % (seq1, 0))
                    seq2 = src_plus_name + '_Distorted' + ext
                    vid2.changevideo(seq2) if os.path.isfile(seq2) else print_dual(text_1_3, '%s 존재하지 않음' % seq2)
                except:
                    print_dual(text_1_3, 'TIFF 변조가 불가합니다.')
            else:
                print_dual(text_1_3, '입력 영상이 \'TIFF\' 영상이 아닙니다.')

        print_dual(text_1_3, "　")
        window.focus_force()
        # winsound.PlaySound('SystemQuestion', winsound.SND_ALIAS)  # 사운드에 딜레이가 함께 있다.. ㄷㄷ
        # time.sleep(0.5)


#########################################################################################################
#########################################################################################################
#########################################################################################################
# 1. 어떤 시나리오가 적용되어있는지 판단
# 2. 판단된 시나리오로 각 연구실의 복조과정 실행
def scenario_inv_act():  ### 복조과정   시나리오별로 각 연구실에서 작성한 win32어플리케이션을 인자전달해서 복조 하도록 해주세요
    srcs = askopenfilenames(initialdir="", filetypes=(("All", "*.*"), ("All Files", "*.*")), title="Choose a file.")
    if srcs == '':   # 사용자가 ask 창을 캔슬 누른 경우 아웃
        return

    for iii, seq1 in enumerate(srcs):
        src_plus_name = os.path.splitext(seq1)[0]   # 파일경로+파일이름
        ext = os.path.splitext(seq1)[1]             # 확장자
        name = os.path.basename(src_plus_name)      # 파일이름

        print_dual(text_2_3, f'({iii + 1}/{len(srcs)}) {name}{ext}')
        vid3.changevideo(seq1)  # 입력영상 띄우기

        if subprocess.call("start_code_decryptor.exe %s" % seq1) == 0: ## 시나리오4 header 변조 check
            print_dual(text_2_3, '2. 시나리오 복조를 시작합니다.')
            print_dual(text_2_3, 'header 복조 중입니다..')
            vid4.changevideo(seq1 + '.restored')
            print_dual(text_2_3, '복조가 완료되었습니다.')
            time.sleep(0.2)
            continue

        if subprocess.call(['python.exe', 'JPEG.py', seq1, '2']) == 0:  ## 시나리오5 JPEG 양자화 테이블 변조 check
            print_dual(text_2_3, "JPEG 복조 중입니다..")
            non_block_threding_popen(text_2_3, "python.exe JPEG.py %s %d" % (seq1, 1))
            vid4.changevideo(seq1.replace('Distorted', 'Restored'))
            print_dual(text_2_3, '복조가 완료되었습니다.')
            continue

        elif subprocess.call(['python.exe', 'bmp_scenario.py', seq1, '2']) == 0:  ## 시나리오6 BMP 변조 check
            print_dual(text_2_3, "BMP 복조 중입니다..")
            non_block_threding_popen(text_2_3, "python.exe bmp_scenario.py %s %d" % (seq1, 1))
            vid4.changevideo(seq1.replace('Distorted.bmp', 'Restored.bmp'))
            print_dual(text_2_3, '복조가 완료되었습니다.')
            continue

        elif subprocess.call(['python.exe', 'png_scenario.py', seq1, '2']) == 0:  ## 시나리오7 PNG 변조 check
            print_dual(text_2_3, "PNG 복조 중입니다..")
            non_block_threding_popen(text_2_3, "python.exe png_scenario.py %s %d" % (seq1, 1))
            vid4.changevideo(seq1.replace('Distorted.png', 'Restored.png'))
            print_dual(text_2_3, '복조가 완료되었습니다.')
            continue

        elif subprocess.call(['python.exe', 'tiff_scenario.py', seq1, '2']) == 0:  ## 시나리오8 TIFF 변조 check
            print_dual(text_2_3, "TIFF 복조 중입니다..")
            non_block_threding_popen(text_2_3, "python.exe tiff_scenario.py %s %d" % (seq1, 1))
            vid4.changevideo(seq1.replace('Distorted.tiff', 'Restored.tiff'))
            print_dual(text_2_3, '복조가 완료되었습니다.')
            continue

        print_dual(text_2_3, '범용적 변형 시나리오 적용여부 판단 중입니다..')                               ## 시나리오1-3 변조 check
        non_block_threding_popen(text_2_3, "python.exe fakeke_enc_dec.py %s" % seq1)                # 1.1 더미-히든 판별모드 실행 (임시 하드코딩)
        if 'hidden' in text_2_3.get('end-2lines', END): None                                        # 더미-히든시나리오로 판단됐다면 codec_prediction.py 안돌리고 통과
        else: non_block_threding_popen(text_2_3, "python.exe codec_prediction.py %s" % seq1)        # 1.2 더미-히든 아닐경우 codec_prediction.py 돌림


        # MPEG2 H.263 H.264 H.265 IVC VP8 JPEG JPEG2000 BMP PNG TIFF 코덱과
        # 'default', 'inverse', 'xor' 시나리오에 대해 판별함
        catched_last1_line = text_2_3.get('end-2lines', END)
        if catched_last1_line[-3:-2] is not '.': text_2_3.delete('end-5c', 'end-1c')                # 파이썬 버전에따라 프로세스 종료시 서식 초기화 문자가 찍혀나오는거 삭제
        print_dual(text_2_3, '예측된 변형 시나리오를 기반으로 복원 실행')

        if 'default' in catched_last1_line:  # 시나리오 적용 안된 경우
            print_dual(text_2_3, '변조된 내역이 없습니다.')

        elif 'inverse' in catched_last1_line:  # 시나리오 1 inverse 복조
            print_dual(text_2_3, 'inverse 복조 중입니다..')
            bits_inv = bitstring.BitStream(~bitstring.Bits(filename=seq1))
            bits_inv.tofile(open(src_plus_name + '_restored' + ext, 'wb'))
            vid4.changevideo(src_plus_name + '_restored' + ext)
            print_dual(text_2_3, '복조가 완료되었습니다.')

        elif 'xor' in catched_last1_line:  # 시나리오 2 xor 복조
            print_dual(text_2_3, 'xor 복조 중입니다..')
            bitstream = bitstring.ConstBitStream(filename=seq1)
            bitstream = dxor_fast_bitstream(bitstream)
            (open(src_plus_name + '_restored' + ext, 'wb')).write(bitstream)
            vid4.changevideo(src_plus_name + '_restored' + ext)
            print_dual(text_2_3, '복조가 완료되었습니다.')

        elif 'dummy-hidden.' in catched_last1_line:  # 시나리오 3     # 더미-히든 복조
            print_dual(text_2_3, "dummy-hidden restore start")
            non_block_threding_popen(text_2_3, "python.exe fakeke_enc_dec.py %s %s" % (seq1, '1'))  # 더미-히든 시나리오 복조모드 실행
            vid4.changevideo(src_plus_name + '_restored' + ext)  # 복조된 _restored 파일 디스플레이
            print_dual(text_2_3, "dummy-hidden restore complete")

        else:
            print_dual(text_2_3, '%s <- 이 마지막 메세지를 인식하지 못했기에 복조 시나리오로 넘어가지 못했습니다. 혹은 복조 프로세스가 오류종료 하였음' % catched_last1_line[:-2])
        print_dual(text_2_3, " ")
        window.focus_force()
        # winsound.PlaySound('SystemQuestion', winsound.SND_ALIAS)
        time.sleep(0.2)


# 여기까지 복조과정
#########################################################################################################
#########################################################################################################
# 이후 UI 관련 코드
def release(event):
    def ddd(vid, slider):
        current = int(vid.vid.get(1))
        goingto = int(vid.frame_count * slider.get() / 100) + 1

        if current < goingto:
            nn = goingto - current - 1
            for n in range(1, nn):
                vid.get_frame()
            tt, vid.frame = vid.get_frame()
            print(current, '    ', goingto)
        elif current > goingto:
            print(current, '    ', goingto)
            vid.vid.set(1, goingto)
            current = int(vid.vid.get(1))
            nn = goingto - current - 1
            for n in range(1, nn):
                vid.get_frame()
            tt, vid.frame = vid.get_frame()
            print('    ', current, '    ', goingto)
        time.sleep(0.81)

    if event.widget.master.winfo_name() == '!frame':
        ddd(vid1, sli1)
    elif event.widget.master.winfo_name() == '!frame2':
        ddd(vid3, sli2)


def sliderdrag(event):
    # time.sleep(0.02)
    # release(event)
    None


window = tkinter.Tk()
window.title('UI test')
window.iconbitmap('ho.ico')
window.geometry("845x705+900+160")

style = tkinter.ttk.Style()  # https://wiki.tcl-lang.org/page/List+of+ttk+Themes
style.theme_create("yummy", parent='winnative', settings={  # 커스텀 스타일을 만들어야만 탭배경색이 변경가능하데
    "TNotebook": {"configure": {"tabmargins": [7, 5, 0, 0]}},
    "TNotebook.Tab": {
        "configure": {"padding": [14, 5], "background": '#cfdfc5'},  # 흰국방색
        "map": {"background": [("selected", '#FFFFFF')],  # 흰색
                "expand": [("selected", [1, 1, 1, 1])]}}})
style.theme_use("yummy")
tkinter.ttk.Style().configure("TNotebook", background='#536349')  # 국방색

# tkinter.ttk.Style().configure("TNotebook", background='#536349')        #국방색
# tkinter.ttk.Style().configure('TNotebook.Tab', padding=[11, 4], background='red',foreground='blue' )
# tkinter.ttk.Style().map('TNotebook.Tab', background=[('selected', 'yellow')])

notebook = tkinter.ttk.Notebook(window, width=845, height=670)
notebook.pack()

# Tap 1
frame1 = tkinter.Frame(window)
notebook.add(frame1, text="변조")

Origin_labelframe_1 = tkinter.LabelFrame(frame1, text="Origin")
Modified_labelframe_1 = tkinter.LabelFrame(frame1, text="Modified")
States_labelframe_1 = tkinter.LabelFrame(frame1, text="States")

Origin_labelframe_1.pack()
Modified_labelframe_1.pack()
States_labelframe_1.pack()

# Vertical (y) Scroll Bar
yscrollbar = Scrollbar(States_labelframe_1)
yscrollbar.pack(side="right", fill="both")

# text_1_1 = Text(Origin_labelframe_1, width=50, height=20)
# text_1_2 = Text(Modified_labelframe_1, width=50, height=20)
text_1_3 = Text(States_labelframe_1, width=113, height=13, wrap=NONE, yscrollcommand=yscrollbar.set)

# text_1_1.insert(tkinter.INSERT, '''Origin''')
# text_1_2.insert(tkinter.INSERT, '''Modified''')
text_1_3.insert(tkinter.INSERT, '''''')

# text_1_1.pack()
# text_1_2.pack()
text_1_3.pack()

# Configure the scrollbars
yscrollbar.config(command=text_1_3.yview)

sli1 = DoubleVar();
slider_1 = Scale(frame1, from_=1, to=101, orient=HORIZONTAL, length=810, variable=sli1)
slider_1.bind("<B1-Motion>", sliderdrag)
slider_1.bind("<ButtonRelease-1>", release)
slider_1.pack()

# btn_1_2 = tkinter.Button(frame1, text="ㅁ")
# btn_1_3 = tkinter.Button(frame1, text=">>")

# Tap 2
frame2 = tkinter.Frame(window)
notebook.add(frame2, text="복조")

Origin_labelframe_2 = tkinter.LabelFrame(frame2, text="Modified")
Modified_labelframe_2 = tkinter.LabelFrame(frame2, text="Recovered")
States_labelframe_2 = tkinter.LabelFrame(frame2, text="States")

Origin_labelframe_2.pack()
Modified_labelframe_2.pack()
States_labelframe_2.pack()

# Vertical (y) Scroll Bar
yscrollbar = Scrollbar(States_labelframe_2)
yscrollbar.pack(side="right", fill="both")

# text_2_1 = Text(Origin_labelframe_2, width=50, height=20)
# text_2_2 = Text(Modified_labelframe_2, width=50, height=20)
text_2_3 = Text(States_labelframe_2, width=113, height=13, wrap=NONE, yscrollcommand=yscrollbar.set)

# text_2_1.insert(tkinter.INSERT, '''Modified''')
# text_2_2.insert(tkinter.INSERT, '''Recovered''')
text_2_3.insert(tkinter.INSERT, '''''')

# text_2_1.pack()
# text_2_2.pack()
text_2_3.pack()

# Configure the scrollbars
yscrollbar.config(command=text_2_3.yview)

# combobox
# combo_1_1 = Combobox(frame1)
# combo_1_1['values'] = ("MPEG-2", "H.263", "H.264", "HEVC", "IVC", "VP8", "JPEG", "JPEG2000", "BMP", "PNG", "TIFF")
# combo_1_1.current(0)  # set the selected item


combo_1_2 = Combobox(frame1)
combo_1_2['values'] = ("Scenario-1 inverse", "Scenario-2 xor", "Scenario-3 더미-히든", "Scenario-4 start code", "Scenario-5 jpg, j2k", "Scenario-6 bmp", "Scenario-7 png", "Scenario-8 tiff")
combo_1_2.bind("<<ComboboxSelected>>", lambda event: canvas_loading.show() or scenario_act(event) or window.focus_force() or canvas_loading.forget())  # 함수 주소 전달인데 or이 먹히네...
combo_1_2.current(0)  # set the selected item

# combo_1_1.place(x=150, y=0)
combo_1_2.place(x=150, y=10)

sli2 = DoubleVar();
slider_2 = Scale(frame2, from_=1, to=101, orient=HORIZONTAL, length=810, variable=sli2)
slider_2.bind("<B1-Motion>", sliderdrag)
slider_2.bind("<ButtonRelease-1>", release)
slider_2.pack()

#


# button click event set
# btn_1 = tkinter.Button(window, text='input sequence & encode', command=lambda: vid1.changevideo(), compound=LEFT)
# btn_2 = tkinter.Button(window, text='distortion', command=lambda: vid2.changevideo(), compound=LEFT)
# btn_3 = tkinter.Button(window, text='load model & classify', command=lambda: vid3.changevideo(), compound=LEFT)
# btn_4 = tkinter.Button(window, text='recover', command=lambda: vid4.changevideo(), compound=LEFT)

# text_1_1 = Text(frame1,width = 10,height=1 )
btn_1_1 = tkinter.Button(frame1, text="input stream", command=lambda: scenario_act('askmode') or vid2.changevideo('close'))
# btn_1_2 = tkinter.Button(frame1, text="Encode", command=lambda: vid2.detect(text_1_3, combo_1_2.current()+1, codec_list.index(os.path.splitext(vid1.video_source)[1]), os.path.splitext(vid1.video_source)[0]))
# vid2.detect(text_1_3)
# vid2.detect(text_1_3, combo_1_2.current()+1, codec_list.index(os.path.splitext(vid1.video_source)[1]), os.path.splitext(vid1.video_source)[0])
# detect.main(combo_1_2.current(),3,vid1.video_source)
# text_2_1 = Text(frame2,width = 10,height=1 )
btn_2_1 = tkinter.Button(frame2, text="restore stream", command=lambda: scenario_inv_act() or window.focus_force())  # 프로세스 종료되면 윈도우가 깜빡이도록 알람
# btn_2_2 = tkinter.Button(frame2, text="Decode", command=lambda: vid4.detect_inv(text_2_3, os.path.splitext(vid3.video_source)))


# button position
# text_1_1.place(x = 110, y = 5)
btn_1_1.place(x=10, y=10)
# btn_1_2.place(x=53, y=0)
# text_2_1.place(x = 110, y = 5)
btn_2_1.place(x=10, y=10)
# btn_2_2.place(x=53, y=0)
# btn_1_2.place(x=0, y=350)
# btn_2_2.place(x=0, y=350)
# btn_1_3.place(x=30, y=350)
# btn_2_3.place(x=30, y=350)

# windows positions
Origin_labelframe_1.place(x=10, y=50)
Origin_labelframe_2.place(x=10, y=50)
Modified_labelframe_1.place(x=460, y=50)
Modified_labelframe_2.place(x=460, y=50)
States_labelframe_1.place(x=10, y=450)
States_labelframe_2.place(x=10, y=450)

slider_1.place(x=10, y=400)
slider_2.place(x=10, y=400)

vid1 = LoadDisplay(Origin_labelframe_1, 0, 0)
vid2 = LoadDisplay(Modified_labelframe_1, 0, 0)
vid3 = LoadDisplay(Origin_labelframe_2, 0, 0)
vid4 = LoadDisplay(Modified_labelframe_2, 0, 0)

text_1_a = Text(Origin_labelframe_1, width=40, height=1)
text_1_a.configure(background=window["bg"], border=0);
text_1_a.pack()
text_1_b = Text(Origin_labelframe_2, width=40, height=1);
text_1_b.configure(background=window["bg"], border=0);
text_1_b.pack()
text_2_a = Text(Modified_labelframe_1, width=40, height=1);
text_2_a.configure(background=window["bg"], border=0);
text_2_a.pack()
text_2_b = Text(Modified_labelframe_2, width=40, height=1);
text_2_b.configure(background=window["bg"], border=0);
text_2_b.pack()


class canvas_loding_class:
    def __init__(self, width, height, x, y, hide=1):
        self.hide = hide
        self.x = x
        self.y = y
        self.canvas_loadingimage = tkinter.Canvas(window, width=width, height=height, bg="yellow", bd=0,
                                                  highlightthickness=0, relief='ridge')
        self.canvas_loadingimage.place(x=x, y=y)
        self.vid = cv2.VideoCapture('load_lgreen.gif')
        ret, self.temframe = self.vid.read()
        cv2.cvtColor(self.temframe, cv2.COLOR_BGR2RGB)
        self.photo = PIL.ImageTk.PhotoImage(image=PIL.Image.fromarray(self.temframe))
        self.canvas_loadingimage.create_image(0, 0, image=self.photo, anchor=tkinter.NW)
        self.forget()
        self.update()

    def update(self):
        if self.hide == 1:
            None
        else:
            try:
                ret, self.temframe = self.vid.read()  # cv가 코덱모를경우 에러뿜음
                cv2.cvtColor(self.temframe, cv2.COLOR_BGR2RGB)
            except:
                self.vid = cv2.VideoCapture('load_lgreen.gif')  # opencv 이상한게 프레임 재생 할당량만 채우면 종료되버리네 ㄷ  bit은 오류날듯
                ret, self.temframe = self.vid.read()
            self.photo = PIL.ImageTk.PhotoImage(image=PIL.Image.fromarray(self.temframe))
            self.canvas_loadingimage.create_image(0, 0, image=self.photo, anchor=tkinter.NW)
        window.after(27, self.update)
        # window.update()

    def forget(self):
        self.hide = 1
        self.canvas_loadingimage.place_forget()
        window.update()

    def show(self):
        self.hide = 0
        self.canvas_loadingimage.place(x=self.x, y=self.y)
        window.update()


canvas_loading = canvas_loding_class(290, 290, 250, 200)

for filename in glob("1t_youcandelete*"): os.remove(filename)
srcs_g('')  # 전역변수 초기화

window.mainloop()
for filename in glob("1t_youcandelete*"): os.remove(filename)