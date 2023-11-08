"""Acquire N frames at frame rate R and exposure time X"""

# import sys
# import cv2
# import math
import time
# import ctypes as ct
# import numpy as np
from multiprocessing import Queue, Process
from egrabber import Buffer
from egrabber import BUFFER_INFO_BASE, INFO_DATATYPE_PTR
from set_grabber_properties import get_cmd_inputs, check_exposure
from set_grabber_properties import create_and_configure_grabber
from convert_display_data import mono8_to_ndarray
from input_output import set_output_path, display_grabber_settings
from input_output import save_from_queue_multiprocess
from input_output import display_from_queue_multiprocess


def main():
    # Get script arguments
    cmd_args = get_cmd_inputs()

    # Make sure exposure time setting will be less than cycling time
    # Choose if not given
    cmd_args.exp_time = check_exposure(cmd_args.fps, cmd_args.exp_time)

    # Display settings
    print('\nAcquisition settings:')
    display_grabber_settings(cmd_args)

    # Set up saving location and filename length
    output_path = set_output_path()
    print('\nOutput will be saved in {}'.format(output_path))
    # len_frame_number = math.floor(math.log10(cmd_args.n_frames - 1)) + 1

    # Create and configure grabber and buffer
    print('\nSetting up grabber...')
    grabber = create_and_configure_grabber(cmd_args)
    images_per_buffer = 100
    num_buffers = 100

    # Create queues for saving images from buffers and displaying
    # and start parallel saving and displaying processes
    print('\nPreparing parallel saving and display processes...')

    savequeue = Queue()
    num_save_processes = 16
    save_process_list = []
    for i in range(num_save_processes):
        save_process = Process(target=save_from_queue_multiprocess,
                               args=(savequeue, output_path)
                               )
        save_process_list.append(save_process)
        save_process.start()

    displayqueue = Queue()
    display_process = Process(target=display_from_queue_multiprocess,
                              args=(displayqueue,)
                              )
    display_process.start()

    # Make a buffer ready for every frame and start
    print('\nAllocating buffers...')
    # Set up multi-part buffer for speed
    t_alloc_start = time.time()
    grabber.stream.set('BufferPartCount', images_per_buffer)

    grabber.realloc_buffers(num_buffers)
    print('Buffer allocation took {} s.'.format(time.time() - t_alloc_start))
    grabber.start()

    # Measure speed
    timestamps = []

    # Initialise list of buffer pointer addresses
    # Useful if retaining frames in memory to access later
    # ptr_addresses = []

    # Acquire data!
    buffer_count = 0
    live_view_dt = 0.2 * 1e6  # in microseconds, for buffer timestamps
    live_view_count = 1
    t_start = time.time()
    t_stop = t_start + 20

    t = t_start
    print('\nAcquiring data...')
    while t < t_stop:
        with Buffer(grabber) as buffer:
            t = time.time()

            buffer_pointer = buffer.get_info(BUFFER_INFO_BASE,
                                             INFO_DATATYPE_PTR
                                             )
            timestamps.append(buffer.get_info(cmd=3, info_datatype=8))
            buffer_count = buffer_count + 1

            # Convert to array and queue for a  saving process
            numpy_images = mono8_to_ndarray(buffer_pointer,
                                            cmd_args.roi_width,
                                            cmd_args.roi_height,
                                            images_per_buffer
                                            )
            # print('Acquired shape: {}'.format(numpy_images.shape))
            savequeue.put([numpy_images, buffer_count])

            # Display images in parallel process via queue
            if timestamps[-1] - timestamps[0] > \
                    live_view_count * live_view_dt:
                displayqueue.put([numpy_images[0], 'Hello!'])
                live_view_count = live_view_count + 1

    # Stop display process
    displayqueue.put(None)

    # Stop save processes
    for proc in save_process_list:
        while proc.exitcode is None:
            savequeue.put(None)
            time.sleep(0.1)

    print('\nDone.')

    if len(timestamps) > 0:
        print('\nTime at buffer 0: {} us'.format(timestamps[0]))
        print('Time at buffer {}: {} us'.format(len(timestamps) - 1,
                                                timestamps[-1]
                                                )
              )
        print('Time elapsed = {} us'.format(timestamps[-1] - timestamps[0]))

    print('Acquired {} buffers over {} s.'
          .format(buffer_count, t - t_start))


if __name__ == '__main__':
    main()
