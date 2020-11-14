import operator
import threading
import tkinter.messagebox
from tkinter.filedialog import askopenfilename, askopenfilenames
from tkinter import *
from tkinter.ttk import *
import subprocess
import re

import PIL.Image
import PIL.ImageTk
import cv2
from utils import *
import tiff_scenario, png_scenario, bmp_scenario
from brisque import *


def isHangul(text):
    encText = text
    hanCount = len(re.findall(u'[\u3130-\u318F\uAC00-\uD7A3]+', encText))
    return hanCount > 0

def close_ask(win,vid,w,h):
    vid.i_width  = int(''.join(list(filter(str.isdigit,w.get(0.0,'end')))))
    vid.i_height = int(''.join(list(filter(str.isdigit,h.get(0.0,'end')))))
    win.destroy()

def NewYuv_Askwindow(vid):
    if re.search('_[0-9]{2,}x[0-9]{2,}', vid.video_source):             # 파일이름에 _숫자x숫자 꼴 존재
        s = re.search('_[0-9]{2,}x[0-9]{2,}', vid.video_source).regs[0][0] + 1
        e = re.search('_[0-9]{2,}x[0-9]{2,}', vid.video_source).regs[0][1]
        vid.i_width  = vid.video_source[s:e].split('x')[0]
        vid.i_height = vid.video_source[s:e].split('x')[1]
    else:                                                               # 그렇지 않으면 묻기 창
        askpop_win = tkinter.Toplevel(window)
        askpop_win.geometry('260x230')
        askpop_win.attributes('-topmost', 'true')

        label_0 = tkinter.Label(askpop_win, text="%s \n\n파일에 대한 추가 정보를 입력해 주세요" % vid.video_source , justify='left')
        label_1 = tkinter.Label(askpop_win, text="해상도:            x")
        label_2 = tkinter.Label(askpop_win, text="색포맷:  YUV420 only")
        text_width  = Text(askpop_win, width=5, height=1);  text_width.insert(0.0, "352") ; text_width.tag_configure("right", justify='right');  text_width.tag_add("right", 1.0, "end")
        text_height = Text(askpop_win, width=5, height=1); text_height.insert(0.0, "288") ; text_height.tag_configure("right", justify='right'); text_height.tag_add("right", 1.0, "end")
        button_0 = tkinter.Button(askpop_win, text="확인",width=30, height=2, command=lambda: close_ask(askpop_win, vid,text_width,text_height))

        label_0.place(x=10, y=9)
        label_1.place(x=30, y=80)
        label_2.place(x=30, y=110)
        text_width.place(x=78, y=83)
        text_height.place(x=130, y=83)
        button_0.place(x=20, y=160)

        while tkinter.Toplevel.winfo_exists(askpop_win): time.sleep(0.1);  askpop_win.update();          # 완료 되기전까진 ask창 잡아두며 리플레시




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
            if os.path.isfile(self.video_source):  # 영상이이 존재  png,  YUV 케이스?
                print('(debug) imread로 시도')
                if isHangul(self.video_source): print_dual(self.canvas.master.master.children['!labelframe3'].children['!text'], "(debug) cv2.imread png: 경로에 한글 주소가 포함되어 있어 디코딩 불가"); return
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
                    sli3.set(0)
                    canvas_loading.forget()
                    return set_srctext_and_return(self.video_source)
                else:  # imread로 열기 실패
                    if '.yuv' in self.video_source:
                        NewYuv_Askwindow(self)
                        self.vid = VideoCaptureYUV(self.video_source, (self.i_height, self.i_width)); ratio = 352 / self.i_width;  self.zoom_x = ratio;  self.zoom_y = ratio
                        ret, self.frame = self.vid.read()
                        # print_dual(self.canvas.master.master.children['!labelframe3'].children['!text'], "(debug) YUV 열기 완료, 이미지는 보이나 인코딩된 상태가 아니기 때문에 시나리오 적용 불가")
                        return set_srctext_and_return(self.video_source)
                    else:
                        self.vid = cv2.VideoCapture('errd2.png')
                        print('오류디스플레이 출력')
                        ret, self.frame = self.get_frame()
            else:
                print("@@@@@@@@@@@@@@@@@@@@@@@@@@@")  ## 영상 노존재
                print("error, file not exist in %s" % self.video_source)
                ## 에러영상 메세지 디스플레이기능 넣기
                self.video_source = ""
                return set_srctext_and_return('')

        else:  # vid.isOpened True 일때: 영상 정보를 얻자
            ret, self.frame = self.get_frame()  # 이미지/동영상의 첫 프레임을 출력
            if self.frame is None:  # 파일은 존재하지만 디코딩이 실패 -> IVC 디코더로 시도
                self.vid.release()
                print("IVC 디코더로 시도")
                subprocess.run("ldecod_ivc.exe %s tmp_file_%s" % (self.video_source, os.path.splitext(os.path.basename(self.video_source))[0]+'.bit'), stdout=subprocess.DEVNULL)  # 현재폴더에 재인코딩된 임시파일 생성(yuv)
                list_of_yuv_files = glob('tmp_file_%s*' % os.path.splitext(os.path.basename(self.video_source))[0])     # 이름_resㅇㅇㅇxㅇㅇㅇ.bit
                if '_res' in list_of_yuv_files[0] and '0x0' not in list_of_yuv_files[0]:
                    latest_file = max(list_of_yuv_files, key=os.path.getctime)                                          # 가장최근에 생성된
                    width = int(re.findall("\d+", latest_file)[-2])
                    height = int(re.findall("\d+", latest_file)[-1])
                    yuv_src = 'tmp_file_' + os.path.splitext(os.path.basename(self.video_source))[0] + '_res%dx%d' %(width,height) + '.bit'
                    yuv_srcn = 'tmp_file_' + os.path.splitext(os.path.basename(self.video_source))[0]
                    subprocess.run("ffmpeg.exe -f rawvideo -s %dx%d -pix_fmt yuv420p -i %s -c:v hevc -y %s.hevc" % (width, height, yuv_src, yuv_srcn), stdout=subprocess.DEVNULL)
                    # if os.path.isfile(os.path.splitext(yuv_src)[0] + '.hevc'): 파일이존재하지않을이유는없을걸
                if 'yuv_src' in vars():
                    if os.path.getsize(yuv_srcn + '.hevc') > 1:      self.vid = cv2.VideoCapture(yuv_srcn + '.hevc')    # 존재, 용량있음, 띄우기
                else:       # IVC 디코더로 디코딩 불가시 시퀀스는 에러(변조)영상 화면상에 에러 메세지 띄우기
                    self.vid = cv2.VideoCapture('errd1.png')
                    print('오류디스플레이 출력')
                ret, self.frame = self.get_frame()
            self.frame_count = self.vid.get(cv2.CAP_PROP_FRAME_COUNT)
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
                ret, frame = self.vid.read()  # cv가 코덱인식 못할 경우 에러
            except:
                None
            LoadDisplay.progressbar = self.vid.get(cv2.CAP_PROP_POS_FRAMES)
            if ret:
                return 2, cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)  # success
            else:
                self.vid = cv2.VideoCapture(self.video_source)  # opencv 프레임 재생 할당량만 채우면 종료
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

        if ret == 2:  # 일반 재생시
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
    if aa == '': return
    now = datetime.now(); strt = '[%d.%02d.%02d %d:%02d:%02d] ' % (now.year, now.month, now.day, now.hour, now.minute, now.second)
    print(strt, end='')
    text.insert(END, strt)
    print(aa)
    if type(aa) == str:
        text.insert(END, aa + '\n')
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

def do_inv(text, seq):
    src_plus_name = os.path.splitext(seq)[0]   # 파일경로+파일이름
    ext = os.path.splitext(seq)[1]             # 확장자
    print_dual(text, 'inverse 복조 중입니다..')
    bits_inv = bitstring.BitStream(~bitstring.Bits(filename=seq))
    bits_inv.tofile(open(src_plus_name + '_restored' + ext, 'wb'))
    vid4.changevideo(src_plus_name + '_restored' + ext)
    print_dual(text, '복조가 완료되었습니다.')

def do_dxor(text, seq):
    src_plus_name = os.path.splitext(seq)[0]   # 파일경로+파일이름
    ext = os.path.splitext(seq)[1]             # 확장자
    print_dual(text, 'xor 복조 중입니다..')
    bitstream = bitstring.ConstBitStream(filename=seq)
    bitstream = dxor_fast_bitstream(bitstream)
    (open(src_plus_name + '_restored' + ext, 'wb')).write(bitstream)
    vid4.changevideo(src_plus_name + '_restored' + ext)
    print_dual(text, '복조가 완료되었습니다.')


def non_block_threading_popen(text, src, encoding='utf-8'):  # stdout를 read로 읽으면 먹통되는 현상을 고치는 함수
    from queue import Queue
    def enqueue_output(out, queue):
        try:
            for line in iter(out.readline, b''):
                queue.put(line)
        except:
            return  # print("탈출");

    def time_write():
        for n in range(2, 8):
            tem = text.get('end-%dlines' % n, 'end-%dlines' % (n - 1))
            if tem == '': break
            if tem[0] != '[':
                now = datetime.now()
                text.insert('end-%dlines' % n, '[%d.%02d.%02d %d:%02d:%02d] ' % (now.year, now.month, now.day, now.hour, now.minute, now.second))

    LoadDisplay.pausedisplay = 1
    canvas_loading.show()

    if os.device_encoding(0) is not None:      encoding = os.device_encoding(0)     ####### 터미널 실행시에 인코딩안맞는경우!!!!!!!!  #print(os.device_encoding(0))

    p = subprocess.Popen(src, encoding=encoding, stdout=subprocess.PIPE)
    q = Queue()
    t = threading.Thread(target=enqueue_output, args=(p.stdout, q))
    t.daemon = True
    t.start()

    while p.poll() is None:  # read line without blocking
        try:
            line = q.get(timeout=.1)  # or q.get(timeout=.1)
        except:
            time_write()
            text.see(END)
            window.update()  # print('no output yet')
        else:  # got line
            text.insert(END, line)
            continue
    time.sleep(0.01)
    p.stdout.close()  # 파이썬..
    time_write()
    text.see(END)
    canvas_loading.forget()
    text_ = text.get('end-2lines', END)
    if text_[-5:-4] == '':
        text.delete('end-5c', 'end-1c')
    after_text = text.get('end-2lines', END)



#########################################################################################################
#   변조과정
# "변조 시나리오"                 가능 코덱
# "Scenario-1 inverse"          모두
# "Scenario-2 xor"              모두
# "Scenario-3 더미-히든"          mpeg2 263 264 hevc ivc        (vp8 제외)
# "Scenario-4 start code"       mpeg2 264 hevc ivc            (vp8 263 제외)
# "Scenario-5 jpg, j2k"         jpg j2k
# "Scenario-6 bmp"              bmp
# "Scenario-7 png"              png
# "Scenario-8 tiff"             tiff
# * vp8 = webm , ivc = bit
#########################################################################################################

def srcs_g(a):
    srcs_g.count = a

def scenario_act(event):            # 이 함수는 input stream 버튼을 눌러도 호출되고 combobox를 선택해도 호출됨 event 인자의 차이
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
                if ext in ['.jpg','.j2k']: c_i[4] = "Scenario-5 jpg, j2k"
                if ext in '.bmp' : c_i[5] = "Scenario-6 bmp"
                if ext in '.png' : c_i[6] = "Scenario-7 png"
                if ext in '.tiff': c_i[7] = "Scenario-8 tiff"
                if ext in '.m2v' : c_i[2] = "Scenario-3 더미-히든"; c_i[3] = "Scenario-4 start code";
                if '263' in ext  : c_i[2] = "Scenario-3 더미-히든"
                if '264' in ext  : c_i[2] = "Scenario-3 더미-히든"; c_i[3] = "Scenario-4 start code";
                if ext in '.hevc': c_i[2] = "Scenario-3 더미-히든"; c_i[3] = "Scenario-4 start code";
                if ext in '.bit' : c_i[2] = "Scenario-3 더미-히든"; c_i[3] = "Scenario-4 start code";
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

        elif 'Scenario-3' in event.widget.get():  ## 시나리오3 dummy-hidden 변조
            if ext in 'webm': print_dual(text_1_3, 'vp8 은 더미-히든 변조를 지원하지 않습니다'); continue
            if ext in ['jpg', 'j2k', 'bmp', 'tiff', 'png']: print_dual(text_1_3, '이미지 포멧은 더미-히든 변조를 지원하지 않습니다'); continue
            print_dual(text_1_3, '숨길 영상을 추가로 선택 해 주세요')
            seq2 = askopenfilename(initialdir="", filetypes=(("All", "*.*"), ("All Files", "*.*")), title="Choose a file.")  # 더미-히든 변조과정에 필요한 추가시퀀스(히든) 열기
            if seq2 == '': print_dual(text_1_3, '추가 영상을 선택하지 않아 취소되었습니다'); continue
            print_dual(text_1_3, '더미-히든 변조 중입니다..')
            non_block_threading_popen(text_1_3, "python.exe dummy_hidden.py %s %s" % (seq1, seq2))  # 더미-히든 시나리오 변조 실행
            seq3 = os.path.splitext(seq1)[0] + '_' + os.path.basename(seq2)
            vid2.changevideo(seq3) if os.path.isfile(seq3) else print_dual(text_1_3, '%s 존재하지 않음' % seq3)  # 더미-히든 실행 후 완료된 파일 vid2에 띄우기
            print_dual(text_1_3, '변조가 완료되었습니다.')

        elif 'Scenario-4' in event.widget.get():  ## 시나리오4 start code 변조
            if ext in ['webm', 'bit']: print_dual(text_1_3, 'vp8 은 header변조를 지원하지 않습니다'); continue
            if ext in ['jpg', 'j2k', 'bmp', 'tiff', 'png']: print_dual(text_1_3, '이미지 포멧은 header변조를 지원하지 않습니다'); continue
            print_dual(text_1_3, 'header 변조 중입니다..')
            if subprocess.call("start_code_encryptor.exe %s" % seq1) == 0: vid2.changevideo(seq1 + '.st'); print_dual(text_1_3, '변조가 완료되었습니다.')
            else: print_dual(text_1_3, 'header 변조 불가한 비트스트림입니다.')

        elif 'Scenario-5' in event.widget.get():  ## 시나리오5 JPEG 양자화 테이블 변조
            print_dual(text_1_3, 'JPEG 양자화 테이블 변조 중입니다.')
            if ext in ['.jpg', '.j2k']:
                try:
                    non_block_threading_popen(text_1_3, "python.exe JPEG.py %s %d" % (seq1, 0))
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
                    non_block_threading_popen(text_1_3, "python.exe bmp_scenario.py %s %d" % (seq1, 0))
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
                    non_block_threading_popen(text_1_3, "python.exe png_scenario.py %s %d" % (seq1, 0))
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
                    non_block_threading_popen(text_1_3, "python.exe tiff_scenario.py %s %d" % (seq1, 0))
                    seq2 = src_plus_name + '_Distorted' + ext
                    vid2.changevideo(seq2) if os.path.isfile(seq2) else print_dual(text_1_3, '%s 존재하지 않음' % seq2)
                except:
                    print_dual(text_1_3, 'TIFF 변조가 불가합니다.')
            else:
                print_dual(text_1_3, '입력 영상이 \'TIFF\' 영상이 아닙니다.')

        print_dual(text_1_3, "　")
        window.focus_force()
        # winsound.PlaySound('SystemQuestion', winsound.SND_ALIAS)  # 사운드에 딜레이가 포함되어 있음
        # time.sleep(0.5)


#########################################################################################################
#   복조과정
# 1. 어떤 시나리오가 적용되어있는지 판단
# 2. 판단된 시나리오로 각 연구실의 복조과정 실행
#########################################################################################################
def scenario_inv_act():
    srcs = askopenfilenames(initialdir="", filetypes=(("All", "*.*"), ("All Files", "*.*")), title="Choose a file.")
    if srcs == '':   # 사용자가 ask 창을 캔슬 누른 경우 아웃
        return

    for iii, seq1 in enumerate(srcs):
        src_plus_name = os.path.splitext(seq1)[0]   # 파일경로+파일이름
        ext = os.path.splitext(seq1)[1]             # 확장자
        name = os.path.basename(src_plus_name)      # 파일이름

        print_dual(text_2_3, f'({iii + 1}/{len(srcs)}) {name}{ext}')
        vid3.changevideo(seq1)  # 입력영상 띄우기

        print('(d) 더미히든여부확인');  non_block_threading_popen(text_2_3, "python.exe dummy_hidden.py %s" % seq1)     # dummy-hidden 판별
        if 'hidden' in text_2_3.get('end-2lines', END):                                                              # dummy-hidden 복조
            print_dual(text_2_3, "dummy-hidden restore start")
            non_block_threading_popen(text_2_3, "python.exe dummy_hidden.py %s %s" % (seq1, '1'))
            vid4.changevideo(src_plus_name + '_restored' + ext)                                                      # 복조된 _restored 파일 디스플레이
            print_dual(text_2_3, "dummy-hidden restore complete") ; continue

        non_block_threading_popen(text_2_3, "python.exe codec_prediction.py %s" % seq1)         # 딥러닝으로 코덱 식별          # 11개 코덱 후보에 대한 확률 반환

        frequency =  text_2_3.get('end-2lines', END)[23:-3].split(',')                          # {MPEG2 H.263 H.264 H.265 IVC VP8 JPEG JPEG2000 BMP PNG TIFF} 순서로 catched_last1_line 변수에 저장,,, 각 시나리오 판단과정에서 활용
        frq_dict = {c:int(frequency[i]) for i, c in enumerate(codec)}
        frq_dict = sorted(frq_dict.items(), key=operator.itemgetter(1), reverse=True)

        for c, v in frq_dict:                       # 코덱별로 확률이 높은 순서대로 복조과정 반복
            print_dual(text_2_3, '%s 코덱의 변형 시나리오 예측중..' % c)
            if c == 'MPEG-2':
                if subprocess.call("start_code_decryptor.exe %s" % seq1) == 0: ## 시나리오4 header 변조 check
                    print_dual(text_2_3, '2. 시나리오 복조를 시작합니다.')
                    print_dual(text_2_3, 'header 복조 중입니다..')
                    vid4.changevideo(seq1 + '.restored')
                    print_dual(text_2_3, '복조가 완료되었습니다.')
                    time.sleep(0.2)
                    break
                non_block_threading_popen(text_2_3, "python.exe utils.py %s %s" % (seq1, c))    # MPEG-2에 대한 inv xor 판단
                if 'inverse' in text_2_3.get('end-2lines', END): do_inv(text_2_3, seq1); break  # inv 복조
                elif 'xor' in text_2_3.get('end-2lines', END):  do_dxor(text_2_3, seq1); break  # xor 복조

            if c == 'H.263':
                non_block_threading_popen(text_2_3, "python.exe utils.py %s %s" % (seq1, c))    # H.263에 대한 inv xor 판단
                if 'inverse' in text_2_3.get('end-2lines', END): do_inv(text_2_3, seq1); break  # inv 복조
                elif 'xor' in text_2_3.get('end-2lines', END):  do_dxor(text_2_3, seq1); break  # xor 복조

            if c == 'H.264':
                if subprocess.call("start_code_decryptor.exe %s" % seq1) == 0:                  # 시나리오4 start code 변조 check
                    print_dual(text_2_3, '2. 시나리오 복조를 시작합니다.')
                    print_dual(text_2_3, 'header 복조 중입니다..')
                    vid4.changevideo(seq1 + '.restored')
                    print_dual(text_2_3, '복조가 완료되었습니다.')
                    time.sleep(0.2)
                    break
                non_block_threading_popen(text_2_3, "python.exe utils.py %s %s" % (seq1, c))    # H.264에 대한 inv xor 판단
                if 'inverse' in text_2_3.get('end-2lines', END): do_inv(text_2_3, seq1); break  # inv 복조
                elif 'xor' in text_2_3.get('end-2lines', END):  do_dxor(text_2_3, seq1); break  # xor 복조

            if c == 'H.265':
                if subprocess.call("start_code_decryptor.exe %s" % seq1) == 0:                  # 시나리오4 start code 변조 check
                    print_dual(text_2_3, '2. 시나리오 복조를 시작합니다.')
                    print_dual(text_2_3, 'header 복조 중입니다..')
                    vid4.changevideo(seq1 + '.restored')
                    print_dual(text_2_3, '복조가 완료되었습니다.')
                    time.sleep(0.2)
                    break
                non_block_threading_popen(text_2_3, "python.exe utils.py %s %s" % (seq1, c))    # hevc에 대한 inv xor 판단
                if 'inverse' in text_2_3.get('end-2lines', END): do_inv(text_2_3, seq1); break  # inv 복조
                elif 'xor' in text_2_3.get('end-2lines', END):  do_dxor(text_2_3, seq1); break  # xor 복조

            if c == 'IVC':
                if subprocess.call("start_code_decryptor.exe %s" % seq1) == 0:                  # 시나리오4 start code 변조 check
                    print_dual(text_2_3, '2. 시나리오 복조를 시작합니다.')
                    print_dual(text_2_3, 'header 복조 중입니다..')
                    vid4.changevideo(seq1 + '.restored')
                    print_dual(text_2_3, '복조가 완료되었습니다.')
                    time.sleep(0.2)
                    break
                non_block_threading_popen(text_2_3, "python.exe utils.py %s %s" % (seq1, c))    # IVC에 대한 inv xor 판단
                if 'inverse' in text_2_3.get('end-2lines', END): do_inv(text_2_3, seq1); break  # inv 복조
                elif 'xor' in text_2_3.get('end-2lines', END):  do_dxor(text_2_3, seq1); break  # xor 복조

            if c == 'VP8':
                non_block_threading_popen(text_2_3, "python.exe utils.py %s %s" % (seq1, c))    # VP8에 대한 inv xor 판단
                if 'inverse' in text_2_3.get('end-2lines', END): do_inv(text_2_3, seq1); break  # inv 복조
                elif 'xor' in text_2_3.get('end-2lines', END):  do_dxor(text_2_3, seq1); break  # xor 복조

            if c == 'JPEG':
                if subprocess.call(['python.exe', 'JPEG.py', seq1, '2']) == 0:                  # 시나리오5 JPEG/JPEG2000 양자화 테이블 변조 check
                    print_dual(text_2_3, "JPEG 복조 중입니다..")
                    non_block_threading_popen(text_2_3, "python.exe JPEG.py %s %d" % (seq1, 1))
                    vid4.changevideo(seq1.replace('Distorted', 'Restored'))
                    print_dual(text_2_3, '복조가 완료되었습니다.')
                    break
                non_block_threading_popen(text_2_3, "python.exe utils.py %s %s" % (seq1, c))    # JPEG에 대한 inv xor 판단
                if 'inverse' in text_2_3.get('end-2lines', END): do_inv(text_2_3, seq1); break  # inv 복조
                elif 'xor' in text_2_3.get('end-2lines', END):  do_dxor(text_2_3, seq1); break  # xor 복조

            if c == 'JPEG2000':
                if subprocess.call(['python.exe', 'JPEG.py', seq1, '2']) == 0:                  # 시나리오5 JPEG/JPEG2000 양자화 테이블 변조 check
                    print_dual(text_2_3, "JPEG 복조 중입니다..")
                    non_block_threading_popen(text_2_3, "python.exe JPEG.py %s %d" % (seq1, 1))
                    vid4.changevideo(seq1.replace('Distorted', 'Restored'))
                    print_dual(text_2_3, '복조가 완료되었습니다.')
                    break
                non_block_threading_popen(text_2_3, "python.exe utils.py %s %s" % (seq1, c))    # JPEG2000에 대한 inv xor 판단
                if 'inverse' in text_2_3.get('end-2lines', END): do_inv(text_2_3, seq1); break  # inv 복조
                elif 'xor' in text_2_3.get('end-2lines', END):  do_dxor(text_2_3, seq1); break  # xor 복조

            if c == 'BITMAP':
                if subprocess.call(['python.exe', 'bmp_scenario.py', seq1, '2']) == 0:          # 시나리오6 BMP 변조 check
                    print_dual(text_2_3, "BMP 복조 중입니다..")
                    non_block_threading_popen(text_2_3, "python.exe bmp_scenario.py %s %d" % (seq1, 1))
                    vid4.changevideo(seq1.replace('Distorted.bmp', 'Restored.bmp'))
                    print_dual(text_2_3, '복조가 완료되었습니다.')
                    break
                non_block_threading_popen(text_2_3, "python.exe utils.py %s %s" % (seq1, c))    # BITMAP에 대한 inv xor 판단
                if 'inverse' in text_2_3.get('end-2lines', END):
                    do_inv(text_2_3, seq1);
                    break  # inv 복조
                elif 'xor' in text_2_3.get('end-2lines', END):
                    do_dxor(text_2_3, seq1); break  # xor 복조
            if c == 'PNG':
                if subprocess.call(['python.exe', 'png_scenario.py', seq1, '2']) == 0:          # 시나리오7 PNG 변조 check
                    print_dual(text_2_3, "PNG 복조 중입니다..")
                    non_block_threading_popen(text_2_3, "python.exe png_scenario.py %s %d" % (seq1, 1))
                    vid4.changevideo(seq1.replace('Distorted.png', 'Restored.png'))
                    print_dual(text_2_3, '복조가 완료되었습니다.')
                    break
                non_block_threading_popen(text_2_3, "python.exe utils.py %s %s" % (seq1, c))    # PNG에 대한 inv xor 판단
                if 'inverse' in text_2_3.get('end-2lines', END): do_inv(text_2_3, seq1); break  # inv 복조
                elif 'xor' in text_2_3.get('end-2lines', END):  do_dxor(text_2_3, seq1); break  # xor 복조
            if c == 'TIFF':
                if subprocess.call(['python.exe', 'tiff_scenario.py', seq1, '2']) == 0:         # 시나리오8 TIFF 변조 check
                    print_dual(text_2_3, "TIFF 복조 중입니다..")
                    non_block_threading_popen(text_2_3, "python.exe tiff_scenario.py %s %d" % (seq1, 1))
                    vid4.changevideo(seq1.replace('Distorted.tiff', 'Restored.tiff'))
                    print_dual(text_2_3, '복조가 완료되었습니다.')
                    break
                non_block_threading_popen(text_2_3, "python.exe utils.py %s %s" % (seq1, c))    # TIFF에 대한 inv xor 판단
                if 'inverse' in text_2_3.get('end-2lines', END): do_inv(text_2_3, seq1); break  # inv 복조
                elif 'xor' in text_2_3.get('end-2lines', END):  do_dxor(text_2_3, seq1); break  # xor 복조

        print_dual(text_2_3, " ")           # 파일간 사이 공백
        window.focus_force()
        # winsound.PlaySound('SystemQuestion', winsound.SND_ALIAS)
        time.sleep(0.2)


#########################################################################################################
#   인코딩 과정
#   ffmpeg.exe -f rawvideo -s 352x288 -pix_fmt yuv420p -i akiyo_cif_300f.yuv -c:v mpeg2video -y akiyo_cif.m2v
#   ffmpeg.exe -f rawvideo -s 352x288 -pix_fmt yuv420p -i akiyo_cif_300f.yuv -c:v h263p -y akiyo_cif.h263
#   ffmpeg.exe -f rawvideo -s 352x288 -pix_fmt yuv420p -i akiyo_cif_300f.yuv -c:v h264 -y akiyo_cif.h264
#   ffmpeg.exe -f rawvideo -s 352x288 -pix_fmt yuv420p -i akiyo_cif_300f.yuv -c:v hevc -y akiyo_cif.hevc
#   ffmpeg.exe -f rawvideo -s 352x288 -pix_fmt yuv420p -i akiyo_cif_300f.yuv -c:v libvpx -y akiyo_cif.webm
#   lencod_ivc.exe -f encoder_ai.cfg -p InputFile="akiyo_cif_300f.yuv" InputHeaderLength=0 FramesToBeEncoded=30 SourceWidth=352 SourceHeight=288 OutputFile="akiyo_cif.bit"
#   ffmpeg -s 352x288 -pix_fmt yuv420p -i akiyo_cif_300f.yuv -frames:v 1 -y akiyo_cif.jpg
#   ffmpeg -s 352x288 -pix_fmt yuv420p -i akiyo_cif_300f.yuv -c:v jpeg2000 -frames:v 1 akiyo_cif.j2k    //      ffmpeg -s 352x288 -pix_fmt yuv420p -i akiyo_cif_300f.yuv -c:v libopenjpeg -frames:v 1 akiyo_cif.j2k
#   ffmpeg -s 352x288 -pix_fmt yuv420p -i akiyo_cif_300f.yuv -frames:v 1 akiyo_cif.bmp
#   ffmpeg -s 352x288 -pix_fmt yuv420p -i akiyo_cif_300f.yuv -frames:v 1 akiyo_cif.png
#   ffmpeg -s 352x288 -pix_fmt yuv420p -i akiyo_cif_300f.yuv -frames:v 1 akiyo_cif.tiff
#########################################################################################################


def encoding_act(event):            # 이 함수는 input stream 버튼을 눌러도 호출되고 combobox를 선택해도 호출됨 event 인자의 차이
    if event == 'askmode':          # input stream 버튼을 통한 접근시
        srcs_g.count = askopenfilenames(initialdir="", filetypes=(("All", "*.*"), ("All Files", "*.*")), title="Choose a file.")
        srcs2 = srcs_g.count
        if len(srcs2) == 0:      # 사용자가 ask 창을 캔슬 누른 경우 아웃
            frame3.children['!combobox']['values'] = ("yuv to mpeg2", "yuv to h.263", "yuv to h.264", "yuv to hevc", "yuv to vp8", "yuv to bit", "yuv to jpg", "yuv to j2k", "yuv to bmp", "yuv to png", "yuv to tiff")
            return

        if len(srcs2) >= 1:
            print_dual(text_3_3, f' {len(srcs2)}개의 입력 영상을 선택하였습니다.  ')
            vid5.changevideo(srcs2[0])
            return

    # combobox 리스트를 통한 접근시
    srcs2 = srcs_g.count
    if len(srcs2) == 0:  return     # 입력영상을 아직 선택하지 않았을 경우 그냥 아웃

    for iii, seq3 in enumerate(srcs2):
        if seq3 == '' and event.widget.current() != 9: print_dual(text_3_3, 'input stream을 지정해 주세요');   return

        vid5.changevideo(seq3)  # 입력영상 띄우기          # yuv 파일의 경우 src입력 영상을 띄우는 순간  ->   파일이름을통한 가로세로길이인식과정 or 가로세로 ask창 뜸   -> 이 때 i_width i_height 완성
        width2 = vid5.i_width
        height2 = vid5.i_height

        src_plus_name2 = os.path.splitext(seq3)[0]   # 파일경로+파일이름
        ext2 = os.path.splitext(seq3)[1]             # 확장자
        name2 = os.path.basename(src_plus_name2)      # 파일이름



        print_dual(text_3_3, f'({iii + 1}/{len(srcs2)}) {name2}{ext2}')


        if 'yuv to mpeg2' in event.widget.get():  ## yuv to mpeg2
            print_dual(text_3_3, 'yuv → mpeg2 인코딩 중 입니다..')
            subprocess.run("ffmpeg.exe -f rawvideo -s %sx%s -pix_fmt yuv420p -i %s -c:v mpeg2video -y %s.m2v" % (
                width2, height2, seq3, src_plus_name2), stdout=subprocess.DEVNULL)
            vid6.changevideo(src_plus_name2 + '.m2v')
            print_dual(text_3_3, '인코딩이 완료되었습니다.')

        elif 'yuv to h.263' in event.widget.get():  ## yuv to h.263
            print_dual(text_3_3, 'yuv → h.263 인코딩 중 입니다..')
            subprocess.run("ffmpeg.exe -f rawvideo -s %sx%s -pix_fmt yuv420p -i %s -c:v h263p -y %s.h263" % (
                width2, height2, seq3, src_plus_name2), stdout=subprocess.DEVNULL)
            vid6.changevideo(src_plus_name2 + '.h263')
            print_dual(text_3_3, '인코딩이 완료되었습니다.')

        elif 'yuv to h.264' in event.widget.get():  ## yuv to h.264
            print_dual(text_3_3, 'yuv → h.264 인코딩 중 입니다..')
            subprocess.run("ffmpeg.exe -f rawvideo -s %sx%s -pix_fmt yuv420p -i %s -c:v h264 -y %s.h264" % (
                width2, height2, seq3, src_plus_name2), stdout=subprocess.DEVNULL)
            vid6.changevideo(src_plus_name2 + '.h264')
            print_dual(text_3_3, '인코딩이 완료되었습니다.')

        elif 'yuv to hevc' in event.widget.get():  ## yuv to hevc
            print_dual(text_3_3, 'yuv → hevc 인코딩 중 입니다..')
            subprocess.run("ffmpeg.exe -f rawvideo -s %sx%s -pix_fmt yuv420p -i %s -c:v hevc -y %s.hevc" % (
                width2, height2, seq3, src_plus_name2), stdout=subprocess.DEVNULL)
            vid6.changevideo(src_plus_name2 + '.hevc')
            print_dual(text_3_3, '인코딩이 완료되었습니다.')

        elif 'yuv to vp8' in event.widget.get():  ## yuv to vp8
            print_dual(text_3_3, 'yuv → vp8 인코딩 중 입니다..')
            subprocess.run("ffmpeg.exe -f rawvideo -s %sx%s -pix_fmt yuv420p -i %s -c:v libvpx -y %s.webm" % (
                width2, height2, seq3, src_plus_name2), stdout=subprocess.DEVNULL)
            vid6.changevideo(src_plus_name2 + '.webm')
            print_dual(text_3_3, '인코딩이 완료되었습니다.')

        elif 'yuv to bit' in event.widget.get():  ## yuv to bit
            print_dual(text_3_3, 'yuv → bit 인코딩 중 입니다..')
            subprocess.run("lencod_ivc.exe -f encoder_ai.cfg -p InputFile=%s InputHeaderLength=0 FramesToBeEncoded=30 SourceWidth=%s SourceHeight=%s OutputFile=%s.bit" % (
                seq3, width2, height2, src_plus_name2), stdout=subprocess.DEVNULL)
            vid6.changevideo(src_plus_name2 + '.bit')
            print_dual(text_3_3, '인코딩이 완료되었습니다.')

        elif 'yuv to jpg' in event.widget.get():  ## yuv to jpg
            print_dual(text_3_3, 'yuv → jpg 인코딩 중 입니다..')
            subprocess.run("ffmpeg.exe -f rawvideo -s %sx%s -pix_fmt yuv420p -i %s -frames:v 1 -y %s.jpg" % (
                width2, height2, seq3, src_plus_name2), stdout=subprocess.DEVNULL)
            vid6.changevideo(src_plus_name2 + '.jpg')
            print_dual(text_3_3, '인코딩이 완료되었습니다.')

        elif 'yuv to j2k' in event.widget.get():  ## yuv to j2k
            print_dual(text_3_3, 'yuv → j2k 인코딩 중 입니다..')
            subprocess.run("ffmpeg.exe -f rawvideo -s %sx%s -pix_fmt yuv420p -i %s -c:v jpeg2000 -y %s.j2k" % (
                width2, height2, seq3, src_plus_name2), stdout=subprocess.DEVNULL)
            vid6.changevideo(src_plus_name2 + '.j2k')
            print_dual(text_3_3, '인코딩이 완료되었습니다.')

        elif 'yuv to bmp' in event.widget.get():  ## yuv to bmp
            print_dual(text_3_3, 'yuv → bmp 인코딩 중 입니다..')
            subprocess.run("ffmpeg.exe -f rawvideo -s %sx%s -pix_fmt yuv420p -i %s -frames:v 1 -y %s.bmp" % (
                width2, height2, seq3, src_plus_name2), stdout=subprocess.DEVNULL)
            vid6.changevideo(src_plus_name2 + '.bmp')
            print_dual(text_3_3, '인코딩이 완료되었습니다.')

        elif 'yuv to png' in event.widget.get():  ## yuv to png
            print_dual(text_3_3, 'yuv → png 인코딩 중 입니다..')
            subprocess.run("ffmpeg.exe -f rawvideo -s %sx%s -pix_fmt yuv420p -i %s -frames:v 1 -y %s.png" % (
                width2, height2, seq3, src_plus_name2), stdout=subprocess.DEVNULL)
            vid6.changevideo(src_plus_name2 + '.png')
            print_dual(text_3_3, '인코딩이 완료되었습니다.')

        elif 'yuv to tiff' in event.widget.get():  ## yuv to tiff
            print_dual(text_3_3, 'yuv → tiff 인코딩 중 입니다..')
            subprocess.run("ffmpeg.exe -f rawvideo -s %sx%s -pix_fmt yuv420p -i %s -frames:v 1 -y %s.tiff" % (
                width2, height2, seq3, src_plus_name2), stdout=subprocess.DEVNULL)
            vid6.changevideo(src_plus_name2 + '.tiff')
            print_dual(text_3_3, '인코딩이 완료되었습니다.')


        print_dual(text_3_3, "　")
        window.focus_force()
        # winsound.PlaySound('SystemQuestion', winsound.SND_ALIAS)  # 사운드에 딜레이가 포함되어 있음
        # time.sleep(0.5)

#########################################################################################################
#   UI 관련 코드
#########################################################################################################
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
    elif event.widget.master.winfo_name() == '!frame3':
        ddd(vid5, sli3)


def sliderdrag(event):
    # time.sleep(0.02)
    # release(event)
    None


window = tkinter.Tk()
window.title('GUI for SS-42')
window.iconbitmap('ho.ico')
window.geometry("845x705+900+160")

style = tkinter.ttk.Style()  # https://wiki.tcl-lang.org/page/List+of+ttk+Themes
style.theme_create("yummy", parent='winnative', settings={  # 커스텀 스타일을 만들어야만 탭배경색이 변경가능
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

#########################################################################################################
#   Tap 1
#########################################################################################################
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

sli1 = DoubleVar()
slider_1 = Scale(frame1, from_=1, to=101, orient=HORIZONTAL, length=810, variable=sli1)
slider_1.bind("<B1-Motion>", sliderdrag)
slider_1.bind("<ButtonRelease-1>", release)
slider_1.pack()

# btn_1_2 = tkinter.Button(frame1, text="ㅁ")
# btn_1_3 = tkinter.Button(frame1, text=">>")

#########################################################################################################
#   Tap 2
#########################################################################################################
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
combo_1_2 = Combobox(frame1)
combo_1_2['values'] = ("Scenario-1 inverse", "Scenario-2 xor", "Scenario-3 더미-히든", "Scenario-4 start code", "Scenario-5 jpg, j2k", "Scenario-6 bmp", "Scenario-7 png", "Scenario-8 tiff")
combo_1_2.bind("<<ComboboxSelected>>", lambda event: canvas_loading.show() or scenario_act(event) or window.focus_force() or canvas_loading.forget())  # 함수 주소 전달
combo_1_2.current(0)  # set the selected item

# combo_1_1.place(x=150, y=0)
combo_1_2.place(x=150, y=10)

sli2 = DoubleVar()
slider_2 = Scale(frame2, from_=1, to=101, orient=HORIZONTAL, length=810, variable=sli2)
slider_2.bind("<B1-Motion>", sliderdrag)
slider_2.bind("<ButtonRelease-1>", release)
slider_2.pack()


#########################################################################################################
#   Tap 3
#########################################################################################################
frame3 = tkinter.Frame(window)
notebook.add(frame3, text="인코딩")

Origin_labelframe_3 = tkinter.LabelFrame(frame3, text="Raw")
Modified_labelframe_3 = tkinter.LabelFrame(frame3, text="Encoded")
States_labelframe_3 = tkinter.LabelFrame(frame3, text="States")

Origin_labelframe_3.pack()
Modified_labelframe_3.pack()
States_labelframe_3.pack()

# Vertical (y) Scroll Bar
yscrollbar = Scrollbar(States_labelframe_3)
yscrollbar.pack(side="right", fill="both")

text_3_3 = Text(States_labelframe_3, width=113, height=13, wrap=NONE, yscrollcommand=yscrollbar.set)
text_3_3.insert(tkinter.INSERT, '''''')

text_3_3.pack()

# Configure the scrollbars
yscrollbar.config(command=text_3_3.yview)

# combobox
combo_1_3 = Combobox(frame3)
combo_1_3['values'] = ("yuv to mpeg2", "yuv to h.263", "yuv to h.264", "yuv to hevc", "yuv to vp8", "yuv to bit", "yuv to jpg", "yuv to j2k", "yuv to bmp", "yuv to png", "yuv to tiff")
combo_1_3.bind("<<ComboboxSelected>>", lambda event: canvas_loading.show() or encoding_act(event) or window.focus_force() or canvas_loading.forget())  # 함수 주소 전달
combo_1_3.current(0)  # set the selected item
combo_1_3.place(x=150, y=10)

sli3 = DoubleVar()
slider_3 = Scale(frame3, from_=1, to=101, orient=HORIZONTAL, length=810, variable=sli3)
slider_3.bind("<B1-Motion>", sliderdrag)
slider_3.bind("<ButtonRelease-1>", release)
slider_3.pack()


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
btn_3_1 = tkinter.Button(frame3, text="encoding", command=lambda: encoding_act('askmode'))

# button position
btn_1_1.place(x=10, y=10)
btn_2_1.place(x=10, y=10)
btn_3_1.place(x=10, y=10)

# windows positions
Origin_labelframe_1.place(x=10, y=50)
Origin_labelframe_2.place(x=10, y=50)
Origin_labelframe_3.place(x=10, y=50)
Modified_labelframe_1.place(x=460, y=50)
Modified_labelframe_2.place(x=460, y=50)
Modified_labelframe_3.place(x=460, y=50)
States_labelframe_1.place(x=10, y=450)
States_labelframe_2.place(x=10, y=450)
States_labelframe_3.place(x=10, y=450)

slider_1.place(x=10, y=400)
slider_2.place(x=10, y=400)
slider_3.place(x=10, y=400)

vid1 = LoadDisplay(Origin_labelframe_1, 0, 0)
vid2 = LoadDisplay(Modified_labelframe_1, 0, 0)
vid3 = LoadDisplay(Origin_labelframe_2, 0, 0)
vid4 = LoadDisplay(Modified_labelframe_2, 0, 0)
vid5 = LoadDisplay(Origin_labelframe_3, 0, 0)
vid6 = LoadDisplay(Modified_labelframe_3, 0, 0)

text_1_a = Text(Origin_labelframe_1, width=40, height=1)
text_1_a.configure(background=window["bg"], border=0)
text_1_a.pack()
text_1_b = Text(Origin_labelframe_2, width=40, height=1)
text_1_b.configure(background=window["bg"], border=0)
text_1_b.pack()
text_1_c = Text(Origin_labelframe_3, width=40, height=1)
text_1_c.configure(background=window["bg"], border=0)
text_1_c.pack()

text_2_a = Text(Modified_labelframe_1, width=40, height=1)
text_2_a.configure(background=window["bg"], border=0)
text_2_a.pack()
text_2_b = Text(Modified_labelframe_2, width=40, height=1)
text_2_b.configure(background=window["bg"], border=0)
text_2_b.pack()
text_2_c = Text(Modified_labelframe_3, width=40, height=1)
text_2_c.configure(background=window["bg"], border=0)
text_2_c.pack()


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
                ret, self.temframe = self.vid.read()  # cv가 코덱인식 못할 경우 에러
                cv2.cvtColor(self.temframe, cv2.COLOR_BGR2RGB)
            except:
                self.vid = cv2.VideoCapture('load_lgreen.gif')  # opencv 프레임 재생 할당량만 채우면 종료
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

for filename in glob("tmp_file*"): os.remove(filename)
srcs_g('')  # 전역변수 초기화

window.mainloop()
for filename in glob("tmp_file*"): os.remove(filename)