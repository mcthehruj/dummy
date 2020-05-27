import os
import threading
import tkinter.messagebox
from tkinter.filedialog import askopenfilename
from tkinter import *
from tkinter.ttk import *
import subprocess

import PIL.Image
import PIL.ImageTk
import cv2
from utils import *


class LoadDisplay(object):  #ui 영상창 클래스
    #추가해야할 디스플레이 클래스 기능: 프로그래스바, 모든비디오시퀀스가 33ms의 프레임레이트를 가지는문제, 드래그시 클릭되는 문제
    pausedisplay = 1  # 클래스간 공통변수
    progressbar = 0
    def __init__(self, win, x, y):
        self.win = win
        self.frame = None
        self.frame_count = 0
        self.x = x
        self.y = y
        self.f_width = 352
        self.f_height = 288
        self.video_source = ""
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
        self.canvas = tkinter.Canvas(self.win, width=self.f_width, height=self.f_height, bg="white")
        self.canvas.place(x=x, y=y)
        self.canvas.pack()

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

    def changevideo(self, src = ''):
        LoadDisplay.pausedisplay = 1
        if src == '':
            self.video_source = askopenfilename(initialdir="dataset/training_set/", filetypes=(("All", "*.*"), ("All Files", "*.*")), title="Choose a file.")
            if self.video_source == '': return  # ask 창 cancel 한 경우
        else:
            self.video_source = src

        if self.vid.isOpened(): self.vid.release()           # 만약 클래스에 이전 영상이 열려있다면, 소멸처리
        self.vid = cv2.VideoCapture(self.video_source)
        self.name = os.path.splitext(self.video_source)[1]

        if not self.vid.isOpened():
            if os.path.isfile(self.video_source):
                None        ## 경로만 존재해도 vid는 열린걸로 인식하는듯
            else:
                print("@@@@@@@@@@@@@@@@@@@@@@@@@@@")             ## 영상 노존재
                print("error, file not exist in %s" % self.video_source)
                ## 에러영상 메세지 디스플레이기능 넣기
                self.video_source = ""

        else:   # 정상로드되었다면 영상 정보를 얻자
            ret, self.frame = self.get_frame()  # 동영상의 초기 1프레임 얻어 띄우기
            if self.frame is None:             ## 파일은 존재하지만 디코딩이 안됐단뜻    ## IVC 디코더로 시도
                self.vid.release();    print("IVC 디코더로 시도")
                subprocess.run("ldecod_ivc.exe %s 1t_youcandelete_%s" % (self.video_source, os.path.basename(self.video_source)))     # 현재폴더에 재인코딩된 임시파일 생성
                yuv_src = '1t_youcandelete_' + os.path.basename(self.video_source)
                subprocess.run("ffmpeg.exe -f rawvideo -s 352x288 -pix_fmt yuv420p -i %s -c:v hevc -y %s.hevc" % (yuv_src, os.path.splitext(yuv_src)[0]))
                self.vid = cv2.VideoCapture(os.path.splitext(yuv_src)[0] + '.hevc')
                ret, self.frame = self.get_frame()
                ## 그래도 안뜬다면 시퀀스는 에러영상 일것임     화면상에 에러 메세지로 디스플레이기능 넣기
            self.frame_count = self.vid.get(cv2.CAP_PROP_FRAME_COUNT)                   ##### 정리좀 할것
            self.i_width = self.vid.get(3)
            self.i_height = self.vid.get(4)
            ratio = 352 / self.i_width
            self.zoom_x=ratio; self.zoom_y=ratio; self.move_x=0; self.move_y=0;
            self.frame = cv2.resize(self.frame, None, fx=1, fy=1, interpolation=cv2.INTER_LINEAR)
            self.frame_num_p = 0
            window.update()
            time.sleep(0.01)
            return self.video_source

    def get_frame(self):
        if self.vid.isOpened():  # self.vid.set(cv2.CV_CAP_PROP_POS_FRAMES, frame_number - 1)
            try: ret, frame = self.vid.read()           # cv가 코덱모를경우 에러뿜음
            except: None
            LoadDisplay.progressbar = self.vid.get(cv2.CAP_PROP_POS_FRAMES)
            if ret:
                return 2, cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)  # success
            else:
                return 3, None  # 시퀀스 끝 빈 프레임
        else:
            return 0, 0  # 초기 init 상태

    def update(self):
        if LoadDisplay.pausedisplay == 1:
            ret = 3  # pause 기능
        else:
            ret, temframe = self.get_frame()  # Get a frame from the video source
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
        print("pressed", kp)    # repr(event.char))
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
            self.move_x = self.move_x + (self.i_width  * self.zoom_x) * 0.125 - 2.5
            self.move_y = self.move_y + (self.i_height * self.zoom_y) * 0.125 - 2.5
            self.zoom_x = self.zoom_x * 0.750000
            self.zoom_y = self.zoom_y * 0.750000

    def touch_slide(self, event):
        if self.vid.isOpened():
            self.vid.set(cv2.CAP_PROP_POS_FRAMES, LoadDisplay.progressbar)



def set_slider(slidername, *args):
    t = 0
    for i in args:
        if t < i.frame_count: t = i.frame_count

def print_dual(text, aa):
    now = datetime.now()
    print('[%d.%02d.%02d %d:%02d:%02d] ' % (now.year, now.month, now.day, now.hour, now.minute, now.second), end='')
    text.insert(END, '[%d.%02d.%02d %d:%02d:%02d] ' % (now.year, now.month, now.day, now.hour, now.minute, now.second))
    print(aa)
    if aa == '': return;
    if type(aa) == str: text.insert(END, aa + '\n')
    if type(aa) == list:
        print_dual_nocl(text, '   frequency is [')
        for a in aa:
            print_dual_nocl(text, '%d, ' % (a))
        print_dual_nocl(text, ']\n')
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

def non_block_threding_popen(text, src, encoding='utf-8'):  ### 헉헉 겨우 찾았다 stdout를 read로 읽으면 먹통되는 현상 고치는 함수
    from queue import Queue
    def enqueue_output(out, queue):
        try:
            for line in iter(out.readline, b''):
                queue.put(line)
        except:
            return                      # print("탈출");                            # 개거지같은 파이썬

    p = subprocess.Popen(src, encoding=encoding, stdout=subprocess.PIPE)
    q = Queue()
    t = threading.Thread(target=enqueue_output, args=(p.stdout, q))
    t.daemon = True
    t.start()

    while p.poll() is None:  # read line without blocking
        try:
            line = q.get(timeout=.2)  # or q.get(timeout=.1)
        except:
            window.update();   # print('no output yet')
        else:  # got line
            text.insert(END, line)
            continue
    time.sleep(0.01)
    p.stdout.close()                         # 개거지같은 파이썬


#########################################################################################################
#########################################################################################################
#########################################################################################################
#########################################################################################################

def scenario_act(event):                    ### 변조과정       각 연구실 알아서 작성 요망
    seq1 = vid1.video_source

    if event.widget.current() == 0:                             ## inverse (미완)
        video = bitstring.ConstBitStream(filename=seq1)
        #video.tofile(open('original' + ext, 'wb'))
        video = video.read(video.length).bin
        video = encode(video, 'inv')

    elif event.widget.current() == 1:                             ## xor (미완)
        video = bitstring.ConstBitStream(filename=seq1)
        # video.tofile(open('original' + ext, 'wb'))
        video = video.read(video.length).bin
        count = factor(len(video))
        video = xor_fast(video, count)

    elif event.widget.current() == 2:
        pass    # 연구실별 변조 코드s here

    elif event.widget.current() == 3:
        pass    # 연구실별 변조 코드s here

    elif event.widget.current() == 4:
        pass    # 연구실별 변조 코드s here

    elif event.widget.current() == 5:        ## 시나리오6 ipconfig출력 예시
        non_block_threding_popen(text_1_3, ["ipconfig"], encoding='cp949')
        # with subprocess.Popen(["ipconfig"], stdout=subprocess.PIPE, encoding='cp949') as proc:
        #     text_1_3.insert(tkinter.INSERT, proc.stdout.read())

    elif event.widget.current() == 6:        ## 시나리오7 더미-히든 시나리오 예시     현재 mpeg2,263,264,265 만 됨
        seq2 = askopenfilename(initialdir="", filetypes=(("All", "*.*"), ("All Files", "*.*")), title="Choose a file.") # 더미-히든 변조과정에 필요한 추가시퀀스(히든) 열기
        non_block_threding_popen(text_1_3, "python.exe fakeke_enc_dec.py %s %s" % (seq1, seq2))                         # 더미-히든 시나리오 변조 실행
        seq3 = os.path.splitext(seq1)[0] + '_' + os.path.basename(seq2)
        vid2.changevideo(seq3) if os.path.isfile(seq3) else print_dual(text_1_3, '%s 존재하지 않음' % seq3)               # 더미-히든 실행 후 완료된 파일 vid2에 띄우기 ?.?.? 넣을까뺄까


#########################################################################################################
#########################################################################################################
#########################################################################################################

def scenario_inv_act():                       ### 복조과정      각 연구실 알아서 작성 요망
    seq1 = vid3.changevideo()                                             # 영상 ask창으로 불러오기
    if seq1 == '': return  # 사용자가 ask 창을 캔슬 누른 경우 아웃

    non_block_threding_popen(text_2_3, "python.exe fakeke_enc_dec.py %s" % seq1)            # 더미-히든 판별모드 실행 (임시 하드코딩)
    if text_2_3.get('end-2lines', END)[-9:-3] == 'hidden':
        None
    else:
        non_block_threding_popen(text_2_3, "python.exe 상민딥예측.py %s" % seq1)              # 더미-히든 아닐경우 상민딥 돌림
                                                                                            # MPEG2 H.263 H.264 H.265 IVC VP8 JPEG JPEG2000 BMP PNG TIFF 코덱과
                                                                                            # 'default', 'inverse', 'xor' 시나리오에 대해 판별함
    if text_2_3.get('end-2lines', END) == 'default':
        None            # 연구실별 복조 코드s here
    elif text_2_3.get('end-2lines', END) == 'inverse':
        None            # 연구실별 복조 코드s here
    elif text_2_3.get('end-2lines', END) == 'xor':
        None            # 연구실별 복조 코드s here
    elif text_2_3.get('end-2lines', END)[-9:-3] == 'hidden':                                       # 더미-히든 시나리오라면
        print("1. restoring hidden video")
        non_block_threding_popen(text_2_3, "python.exe fakeke_enc_dec.py %s %s" % (seq1, '1'))     # 더미-히든 시나리오 복조모드 실행
        vid4.changevideo(os.path.splitext(seq1)[0] + '_rev' + os.path.splitext(seq1)[1])
        print("완료")


#########################################################################################################
#########################################################################################################
# 이후 UI 관련 코드

window = tkinter.Tk()
window.title('UI test')
window.geometry("900x700+200+200")

notebook = tkinter.ttk.Notebook(window, width=900, height=600)
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
text_1_3 = Text(States_labelframe_1, width=120, height=10, wrap=NONE, yscrollcommand=yscrollbar.set)
#
# text_1_1.insert(tkinter.INSERT, '''Origin''')
# text_1_2.insert(tkinter.INSERT, '''Modified''')
text_1_3.insert(tkinter.INSERT, '''''')
#
# text_1_1.pack()
# text_1_2.pack()
text_1_3.pack()

# Configure the scrollbars
yscrollbar.config(command=text_1_3.yview)

slider_1 = Scale(frame1, from_=0, to=200, orient=HORIZONTAL, length=810)
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
text_2_3 = Text(States_labelframe_2, width=120, height=10, wrap=NONE, yscrollcommand=yscrollbar.set)

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
combo_1_2['values'] = ("Scenario-1 inverse(미완)", "Scenario-2 xor(미완)", "Scenario-3", "Scenario-4", "Scenario-5", "Scenario-6 테스트용", "Scenario-7 더미히든")
combo_1_2.bind("<<ComboboxSelected>>", scenario_act)
combo_1_2.current(0)  # set the selected item

# combo_1_1.place(x=150, y=0)
combo_1_2.place(x=350, y=0)

slider_2 = Scale(frame2, from_=0, to=200, orient=HORIZONTAL, length=800)
slider_2.pack()

#


# button click event set
# btn_1 = tkinter.Button(window, text='input sequence & encode', command=lambda: vid1.changevideo(), compound=LEFT)
# btn_2 = tkinter.Button(window, text='distortion', command=lambda: vid2.changevideo(), compound=LEFT)
# btn_3 = tkinter.Button(window, text='load model & classify', command=lambda: vid3.changevideo(), compound=LEFT)
# btn_4 = tkinter.Button(window, text='recover', command=lambda: vid4.changevideo(), compound=LEFT)

#text_1_1 = Text(frame1,width = 10,height=1 )
btn_1_1 = tkinter.Button(frame1, text="input stream", command=lambda: vid1.changevideo())
#btn_1_2 = tkinter.Button(frame1, text="Encode", command=lambda: vid2.detect(text_1_3, combo_1_2.current()+1, codec_list.index(os.path.splitext(vid1.video_source)[1]), os.path.splitext(vid1.video_source)[0]))
# vid2.detect(text_1_3)
# vid2.detect(text_1_3, combo_1_2.current()+1, codec_list.index(os.path.splitext(vid1.video_source)[1]), os.path.splitext(vid1.video_source)[0])
#detect.main(combo_1_2.current(),3,vid1.video_source)
#text_2_1 = Text(frame2,width = 10,height=1 )
btn_2_1 = tkinter.Button(frame2, text="restore stream", command=lambda: scenario_inv_act())
#btn_2_2 = tkinter.Button(frame2, text="Decode", command=lambda: vid4.detect_inv(text_2_3, os.path.splitext(vid3.video_source)))


# button position
#text_1_1.place(x = 110, y = 5)
btn_1_1.place(x=0, y=0)
#btn_1_2.place(x=53, y=0)
#text_2_1.place(x = 110, y = 5)
btn_2_1.place(x=0, y=0)
#btn_2_2.place(x=53, y=0)
# btn_1_2.place(x=0, y=350)
# btn_2_2.place(x=0, y=350)
# btn_1_3.place(x=30, y=350)
# btn_2_3.place(x=30, y=350)

# windows positions
Origin_labelframe_1.place(x=0, y=30)
Origin_labelframe_2.place(x=0, y=30)
Modified_labelframe_1.place(x=450, y=30)
Modified_labelframe_2.place(x=450, y=30)
States_labelframe_1.place(x=0, y=450)
States_labelframe_2.place(x=0, y=450)

slider_1.place(x=0, y=400)
slider_2.place(x=0, y=400)

vid1 = LoadDisplay(Origin_labelframe_1, 0, 0)
vid2 = LoadDisplay(Modified_labelframe_1, 0, 0)
vid3 = LoadDisplay(Origin_labelframe_2, 0, 0)
vid4 = LoadDisplay(Modified_labelframe_2, 0, 0)


window.mainloop()


