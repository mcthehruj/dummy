import cv2

for i in range(1 ,5):
    for j in range(1 ,5):
        vid = cv2.VideoCapture('tmp/Candidates_%d_%d.j2k'%(i,j))
        ret, img = vid.read()
        cv2.imwrite('tmp/Candidates_%d_%d.jpg'%(i,j), img)