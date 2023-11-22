"""Acquire N frames at frame rate R and exposure time X"""

# import sys
# import cv2
# import math
import ctypes as ct
import time
# import numpy as np
from math import floor
from multiprocessing import Queue, Process

from egrabber import Buffer
from egrabber import BUFFER_INFO_BASE, INFO_DATATYPE_PTR

from input_output import set_output_path, display_grabber_settings
# from input_output import save_from_queue_multiprocess
from input_output import display_from_queue_multiprocess
from input_output import get_cmd_inputs
from set_grabber_properties import check_exposure
from set_grabber_properties import create_and_configure_grabber
from set_grabber_properties import pre_allocate_multipart_buffers
from convert_display_data import mono8_to_ndarray


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

    # Create and configure grabber
    print('\nSetting up grabber...')
    grabber = create_and_configure_grabber(cmd_args)

    # Create queues for
    # saving images from buffers,
    # displaying images,
    # and user instructions
    # And start parallel saving and displaying processes

    # print('\nPreparing parallel saving and display processes...')
    instruct_queue = Queue()  # Instructions as to how acquisition proceeds
#    save_queue = Queue()  # Image stacks to save
    display_queue = Queue()  # Images to display
#    save_signal_queue = Queue()  # Decision to stop building stack and save

#    save_process = Process(target=save_from_queue_multiprocess,
#                           args=(save_queue, output_path)
#                           )
#    save_process.start()

    display_process = Process(target=display_from_queue_multiprocess,
                              args=(display_queue, instruct_queue)
                              )
    display_process.start()

    # Pre-allocate multi-part buffers and start
    print('\nAllocating buffers...')
    grabber, images_per_buffer = pre_allocate_multipart_buffers(
        grabber,
        images_per_buffer=100,
        duration_allocated_buffers=0.1,
        verbose=True
        )
    grabber.start()

    # List for measuring speed
    timestamps = []

    # Initialise list of buffer pointer addresses
    # Useful if retaining frames in memory to access later
    # ptr_addresses = []

    # Acquire data!
    buffer_count = 0
    live_view_dt = 0.2 * 1e6  # in microseconds, for buffer timestamps
    live_view_count = 1

    print('\nAcquiring data...')
    print('\nPress \'t\' to terminate,'
          '\n\'s\' to save data,'
          '\n\'p\' for preview mode (no saving)...'
          '\n(If you have selected another window in the meantime,'
          ' click on the display window first.)'
          )

    acquire = 'acquire'
    save_instruction = 'preview'
    t_start = time.time()
    # t_stop = t_start + 10

    # while t < t_stop:
    while acquire == 'acquire':
        with Buffer(grabber) as buffer:
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

            # Check for keypress to decide whether to start saving
            if not instruct_queue.empty():
                # Giving 'save' or 'preview'
                save_instruction = instruct_queue.get()

            # Add to stack to save if saving initiated
            if save_instruction == 'save':
                # build_stack_queue.put([numpy_images, buffer_count])

            # Display images in parallel process via queue
            if timestamps[-1] - timestamps[0] > \
                    live_view_count * live_view_dt:
                display_queue.put(numpy_images[0])
                live_view_count = live_view_count + 1

            # Stop on terminate signal in display process
            if display_process.exitcode == 0:
                acquire = 'terminate'
    t_end = time.time()

    if len(timestamps) > 0:
        timestamp_range = timestamps[-1] - timestamps[0]
        print('\nTimestamp at buffer 0: {} us'.format(timestamps[0]))
        print('Timestamp at buffer {}: {} us'
              .format(len(timestamps) - 1, timestamps[-1])
              )
        print('Time between first and list timestamps: {} us'.format(
                timestamp_range
                )
              )
        print('Time per buffer acquisition: {:.1f} us'
              .format(timestamp_range / (buffer_count - 1))
              )
        print('Acquired {} frames per buffer'.format(images_per_buffer))
        print('Time per frame: {:.3f} us'
              .format(timestamp_range
                      / ((buffer_count - 1) * images_per_buffer)
                      )
              )

    print('Acquired {} frames in total over {:.1f} s'
          ' (timepoints outside acquisition loop).'
          .format(buffer_count * images_per_buffer, t_end - t_start)
          )

    # Stop processes and empty queues if necessary
    if display_process.exitcode is None:
        display_queue.put(None)
        time.sleep(0.1)
    while not display_queue.empty():
        display_queue.get()
        time.sleep(0.1)

    # Stop output processes
    print('\nStill writing data to disk...')

    t0 = time.time()

    # if save_process.exitcode is None:
    #    save_queue.put(None)

    # Make sure other queues are empty
    if not instruct_queue.empty():
        instruct_queue.get()
    print('{:.1f} s after closing instruct_queue'
          .format(time.time() - t0)
          )

#    while not counter_queue.empty():
#        counter_queue.get()
#        time.sleep(0.1)
#    while not stop_queue.empty():
#        stop_queue.get()
#        time.sleep(0.1)
#    if not save_signal_queue.empty():
#        save_signal_queue.get()

#    while save_process.exitcode is None:
#        pass

    print('\nDone.')
    print('{:.1f} s when done.'
          .format(time.time() - t0)
          )


if __name__ == '__main__':
    main()
