"""Create numpy arrays from acquired Mono8 data,
transpose arrays and use opencv to show images"""

from egrabber import Buffer
import ctypes as ct
import cv2
import numpy as np
import sys
import time
import set_grabber_properties
from set_grabber_properties import create_and_configure_grabber
from convert_display_data import display_8bit_numpy_opencv
from input_output import display_grabber_settings


gui = 'nogui' not in sys.argv


def mono8_to_ndarray(ptr, w, h, size):
    data = ct.cast(ptr, ct.POINTER(ct.c_ubyte * size)).contents
    return np.frombuffer(data, count=size, dtype=np.uint8).reshape((h, w))


def loop(grabber):
    if not gui:
        countLimit = 10
    count = 1
    frames_dt = 0.25
    # timestamps = []
    time_start = time.time()
    grabber.start()
    while True:
        with Buffer(grabber, timeout=1000) as buffer:
            # if count % 100 == 0:
            # timestamps.append(buffer.get_info(cmd=3, info_datatype=8))
            # if timestamps[-1] - timestamps[0] > 1e-6 * \
            if time.time() - time_start > \
                    count * frames_dt:
                if gui:
                    stop_decision = display_8bit_numpy_opencv(buffer)
                    count += 1
                    if stop_decision:
                        break
                elif count == countLimit:
                    break


def run(grabber):
    grabber.stream.set('BufferPartCount', 1)  # Images ready per buffer
    grabber.realloc_buffers(3)
    loop(grabber)
    if gui:
        cv2.destroyAllWindows()


# Get camera setting arguments
cmd_args = set_grabber_properties.get_cmd_inputs()

# Make sure exposure time is less than cycling time
# Set if not given
cmd_args.exp_time = set_grabber_properties.check_exposure(cmd_args.fps,
                                                          cmd_args.exp_time
                                                          )

# Display settings
display_grabber_settings(cmd_args)

# Create and configure grabber
grabber = create_and_configure_grabber(cmd_args)

# Set up two banks - although one bank gives full resolution!
grabber.remote.set('Banks', 'Banks_AB')  # 2 banks

# Add a pause to allow grabber settings to take effect
time.sleep(0.1)

# Acquire images
run(grabber)

# pixelFormat = grabber.get_pixel_format()
