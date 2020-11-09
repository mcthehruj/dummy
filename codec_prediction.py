from utils import *

#########################################################################################################
#   메인 함수 (딥러닝 네트워크 불러오는 과정)
#########################################################################################################
if __name__ == "__main__":
    if (len(sys.argv) == 2):
        src = sys.argv[1]
        print('딥네트워크 코덱 식별중..', 'cuda' if torch.cuda.is_available() else 'cpu', '환경')
        video = bitstring.ConstBitStream(filename=src)
        video = video.read(video.length).bin
        video = bitstring.BitStream('0b' + video)                           #video.tofile(open('decoded' + name[1], 'wb'))
        predicted_codec = codec_decide(video)
        print('top-1 codec is ', codec[predicted_codec.index(max(predicted_codec))])
        print('{MPG2 H263 H264 H265  IVC  VP8 JPEG JP2K  BMP  PNG TIFF}')
        print('{', end='')
        for i, a in enumerate(predicted_codec): print('%4d' % a, end=''); print(',', end='') if i != len(predicted_codec)-1 else None

        print('}')
        sys.exit(0)

    else:   # if (len(sys.argv) != 2):
        print('입력 인자 오류')

