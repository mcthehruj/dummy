import random
import PIL.Image as Image
import sys
import os

def Load_JPEG(fn):
    with open(fn, 'rb') as f:
        return f.read()

def CheckRGB(fn):
    if Image.open(fn).mode == 'RGB':
        return True
    else:
        return False

def Find_Marker(Content, Marker):
    """
        Return Marker location(index)
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


def Fix_Byte_Stream(Stream, val, location):
    """
        Stream(Bytes object): JPEG file bytes stream
        val(hexadecimal)    : new value to replace original value in stream
        location(int)       : location(index) of byte stream to replace old value with new value
    """

    # Initial DQT table data appear after passing 5bytes from '0xff' location
    DQT_offset = 16
    str_stream = Stream.hex()

    a = bytes.fromhex(str_stream[:location*2 + DQT_offset] + val + str_stream[location*2 + DQT_offset:])
    b = bytes.fromhex(str_stream[:location*2 + DQT_offset] + val + str_stream[location*2 + DQT_offset + 2:])
    c = bytes.fromhex(str_stream[:location*2 + DQT_offset] + val + str_stream[location*2 + DQT_offset + 4:])

    return bytes.fromhex(str_stream[:location*2 + DQT_offset] + val + str_stream[location*2 + DQT_offset + 4:])

def Fix_Byte_Stream_v2(Stream, val, location):
    """
        Stream(Bytes object): JPEG file bytes stream
        val(hexadecimal)    : new value to replace original value in stream
        location(int)       : location(index) of byte stream to replace old value with new value
    """

    # Initial DQT table data appear after passing 5bytes from '0xff' location
    val_hex = val.hex()
    str_stream = Stream.hex()

    mod_stream = str_stream[:location*2] + val_hex + str_stream[location*2 + len(val_hex):]

    return bytes.fromhex(mod_stream), bytes.fromhex(str_stream[location*2 : location*2 + len(val_hex)])


def Write_JPEG(output_fn, Stream):
    with open(output_fn, 'wb') as f:
        f.write(Stream)
    print('[%s] is generated!' % output_fn)


def Distortion(Bin_Jpeg):
    """
        Randomly transform DQT table in JPEG file header to cause distorted image problem when JPEG file is decoded by a viewer program(codec).
    """
    DQT_MARKER = b'\xff\xdb'

    loc = Find_Marker(Bin_Jpeg, DQT_MARKER)

    Corrupted_val = hex(random.randint(30, 150))[2:]

    return Fix_Byte_Stream(Bin_Jpeg, Corrupted_val, loc[0])


def Candidate(Bin_Jpeg, val):
    DQT_MARKER = b'\xff\xdb'

    loc = Find_Marker(Bin_Jpeg, DQT_MARKER)

    Candidate_val = hex(val)[2:]

    return Fix_Byte_Stream(Bin_Jpeg, Candidate_val, loc[0])

#
# def Inspect_candidates():
#     list = os.listdir('candidate')
#     for line in list:
#         Score =


def Make_dataset():
    path = 'C:/Users/MCL/Desktop/tiff_cifar/cifar_tiff/'
    object_list = os.listdir(path)
    for num, line in enumerate(object_list, 1):
        for i in range(1, 16):
            f = Load_JPEG('%s/%s/%06d.tif' % (path, line, i))
            if not CheckRGB('%s/%s/%06d.tif' % (path, line, i)):
                continue
            loc = Find_Marker(f, b'\xff\xdb')[0]

            str_stream = f.hex()

            original_val = f[loc + 5]  # hex number (string)
            for j in range(0, 100):
                fixed_val = hex(original_val + j)[2:]
                if len(fixed_val) == 1:
                    fixed_val = '0' + fixed_val[-1]

                Write_JPEG('%s/%s/image_%04d_%d.tif' % (path, line, i, j), bytes.fromhex(str_stream[:loc * 2 + 10] + fixed_val + str_stream[loc * 2 + 12:]))
                with open('train_list_score_100.txt', 'a') as txt:
                    txt.write('%s/%s/image_%04d_%d.tif\n' % (path, line, i, j))
        print('[%d/%d] is finished' % (num, len(object_list)))

def Make_validation_list():
    import random
    path = '101_ObjectCategories_score'
    object_list = os.listdir(path)
    for line in object_list:
        for i in range(16, 21):
            if not CheckRGB('%s/%s/image_%04d.tif'%(path, line, i)):
                continue
            rand_list = [random.randint(0,99)]
            while len(rand_list) < 10:
                temp = random.randint(0,99)
                if not temp in rand_list:
                    rand_list.append(temp)

            rand_list.sort()
            with open('val_list_score_100.txt', 'a') as txt:
                for val in rand_list:
                    txt.write('%s/%s/%06d.tif\n'%(path, line, i, val))



if __name__ == "__main__":
    input_fn = sys.argv[1]
    output_fn = sys.argv[2]
    mode = sys.argv[3]

    Bin_JPEG = Load_JPEG(input_fn)

    if mode == 'Distortion':
        Result = Distortion(Bin_JPEG)
        Write_JPEG(output_fn, Result)

    if mode == 'Restore':
        if not os.path.isdir('candidate'):
            os.mkdir('candidate')

        for i in range(20):
            Result = Candidate(Bin_JPEG, 10*i)
            Write_JPEG('candidate/%d.jpg'%i, Result)

        Inspect_candidates()

