"""Create numpy arrays from acquired Mono8 data, transpose arrays and use opencv to show images"""

from egrabber import *
import ctypes as ct
import cv2
import numpy as np
import sys
import time


gui = 'nogui' not in sys.argv

def mono8_to_ndarray(ptr, w, h, size):
    data = ct.cast(ptr, ct.POINTER(ct.c_ubyte * size)).contents
    c = 1
    return np.frombuffer(data, count=size, dtype=np.uint8).reshape((h,w,c))

def process(ptr, w, h, size):
    img = mono8_to_ndarray(ptr, w, h, size)
    return np.reshape(img, (-1, w))

def loop(grabber):
    if not gui:
        countLimit = 10
    count = 0
    grabber.start()
    while True:
        with Buffer(grabber, timeout=1000) as buffer:
            ptr = buffer.get_info(BUFFER_INFO_BASE, INFO_DATATYPE_PTR)
            w = buffer.get_info(BUFFER_INFO_WIDTH, INFO_DATATYPE_SIZET)
            h = buffer.get_info(BUFFER_INFO_HEIGHT, INFO_DATATYPE_SIZET)
            size = buffer.get_info(BUFFER_INFO_DATA_SIZE, INFO_DATATYPE_SIZET)
            img = process(ptr, w, h, size)
            count += 1
            if gui:
                cv2.imshow("Press any key to exit", img)
                if cv2.waitKey(1) >= 0:
                    break
            elif count == countLimit:
                break

def run(grabber):
    grabber.realloc_buffers(3)
    loop(grabber)
    if gui:
        cv2.destroyAllWindows()

gentl = EGenTL()
grabber = EGrabber(gentl)
pixelFormat = grabber.get_pixel_format()
if pixelFormat != 'Mono8':
    print("Unsupported {} pixel format. This sample works with Mono8 pixel format only.".format(pixelFormat))
else:
    # Set up stream to unscramble the middle-outwards reading sequence
    grabber.stream.set('StripeArrangement', 'Geometry_1X_2YM')
    grabber.stream.set('LineWidth', 1280) # LinePitch = 0 should be default and fine
    grabber.stream.set('StripeHeight', 1)
    grabber.stream.set('StripePitch', 1)
    grabber.stream.set('BlockHeight', 8)
    # StripeOffset = 0 should be default and fine

    # Set up two banks - although one bank gives full resolution!
    grabber.remote.set('Banks', 'Banks_AB') # 2 banks

    # Add a pause to allow grabber settings to take effect
    time.sleep(0.1)

    # Acquire images
    run(grabber)
