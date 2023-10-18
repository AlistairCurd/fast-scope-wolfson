"""Create numpy arrays from acquired Mono8 data,
transpose arrays and use opencv to show images"""

from egrabber import EGenTL, EGrabber, Buffer
from egrabber import BUFFER_INFO_BASE, BUFFER_INFO_WIDTH
from egrabber import BUFFER_INFO_HEIGHT, BUFFER_INFO_DATA_SIZE
from egrabber import INFO_DATATYPE_PTR, INFO_DATATYPE_SIZET
import ctypes as ct
import cv2
import numpy as np
import sys
import time
import set_grabber_properties


gui = 'nogui' not in sys.argv


def mono8_to_ndarray(ptr, w, h, size):
    data = ct.cast(ptr, ct.POINTER(ct.c_ubyte * size)).contents
    c = 1
    return np.frombuffer(data, count=size, dtype=np.uint8).reshape((h, w, c))


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


# Get camera setting arguments
cmd_args = set_grabber_properties.get_cmd_inputs()

# Make sure exposure time is less than cycling time
# Set if not given
exp_time = set_grabber_properties.check_and_set_exposure(cmd_args.fps,
                                                         cmd_args.exp_time
                                                         )

# Display settings
print('\nNumber of frames : {}'.format(cmd_args.n_frames))
print('Frames per second : {:.1f}'.format(cmd_args.fps))
print('Cycling time : {:.1f}'.format(1e6 / cmd_args.fps), 'us')
print('Exposure time :', exp_time, 'us')
print('Image width: ', cmd_args.roi_width)
print('Image height: ', cmd_args.roi_height)
print('Bit depth of pixel: ', cmd_args.bit_depth)

# Create grabber
gentl = EGenTL()
grabber = EGrabber(gentl)

# Set up ROI
set_grabber_properties.set_roi(grabber,
                               width=cmd_args.roi_width,
                               height=cmd_args.roi_height
                               )

# Set bit-depth
if cmd_args.bit_depth == 8:
    grabber.remote.set('PixelFormat', 'Mono8')
if cmd_args.bit_depth == 12:
    grabber.remote.set('PixelFormat', 'Mono12')

# Set up grabber stream for unscrambled images
set_grabber_properties.unscramble_phantom_S710_output(
    grabber, cmd_args.roi_width, bit_depth=cmd_args.bit_depth
    )

# Configure fps and exposure time
grabber.remote.set('AcquisitionFrameRate', cmd_args.fps)
time.sleep(0.001)  # Allow fps to set first
grabber.remote.set('ExposureTime', exp_time)

# Set up two banks - although one bank gives full resolution!
grabber.remote.set('Banks', 'Banks_AB')  # 2 banks

# Add a pause to allow grabber settings to take effect
time.sleep(0.1)

# Acquire images
run(grabber)

# pixelFormat = grabber.get_pixel_format()

"""
if pixelFormat != 'Mono8':
    print("Unsupported {} pixel format."
          "This sample works with Mono8 pixel format only."
          .format(pixelFormat))
else:
    # Set up stream to unscramble the middle-outwards reading sequence
    grabber.stream.set('StripeArrangement', 'Geometry_1X_2YM')
    grabber.stream.set('LineWidth', 1280)
    # LinePitch = 0 is default and sets LinePitch = LineWidth
    grabber.stream.set('StripeHeight', 1)
    grabber.stream.set('StripePitch', 1)
    grabber.stream.set('BlockHeight', 8)
    # StripeOffset = 0 should be default and fine

    # Set up two banks - although one bank gives full resolution!
    grabber.remote.set('Banks', 'Banks_AB')  # 2 banks

    # Add a pause to allow grabber settings to take effect
    time.sleep(0.1)

    # Acquire images
    run(grabber)
"""
