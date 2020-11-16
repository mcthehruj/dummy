import sys
import os

def Find_Marker(Content, Marker):  # 찾고자 하는 비트스트림(Marker)의 위치 찾기
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


def Fix_Byte_Stream(Stream, val, location):  # Stream의 location에 있는 비트스트림을 val로 바꾸기
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


def Fix_Byte_Stream_v2(Stream, val, location):  # Stream의 location에 있는 비트스트림을 val로 바꾸기
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
