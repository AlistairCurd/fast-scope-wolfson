"""Acquire N frames at frame rate R and exposure time X"""

# import sys
# import cv2
# import math
import ctypes as ct
import time
# import numpy as np
# from math import floor
from multiprocessing import Queue, Process

from egrabber import Buffer
from egrabber import BUFFER_INFO_BASE, INFO_DATATYPE_PTR

from input_output import set_output_path, display_grabber_settings
from input_output import display_from_buffer_queue_multiprocess
from input_output import get_cmd_inputs
from set_grabber_properties import check_exposure
from set_grabber_properties import create_and_configure_grabber
from set_grabber_properties import pre_allocate_multipart_buffers


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
    # displaying images from buffers
    # and user instructions
    # And start parallel displaying processes
    instruct_queue = Queue()  # Instructions as to how acquisition proceeds

    display_queue = Queue()  # Images to display
    display_process = Process(target=display_from_buffer_queue_multiprocess,
                              args=(display_queue,
                                    instruct_queue,
                                    cmd_args.roi_height,
                                    cmd_args.roi_width
                                    )
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

    # In microseconds, for buffer timestamps, seconds for Python time
    live_view_dt = 0.2

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
    storage_size = 0
    buffer_size = \
        images_per_buffer * cmd_args.roi_height * cmd_args.roi_width
    image_size = cmd_args.roi_height * cmd_args.roi_width
    # height = cmd_args.roi_height
    # width = cmd_args.roi_width
    # t_stop = t_start + 10

    # while t < t_stop:
    output_file = open(output_path / 'images_bytes', 'wb')
    while acquire == 'acquire':
        with Buffer(grabber) as buffer:
            buffer_pointer = buffer.get_info(BUFFER_INFO_BASE,
                                             INFO_DATATYPE_PTR
                                             )
            if len(timestamps) == 0:
                timestamp = buffer.get_info(cmd=3, info_datatype=8)
                timestamps.append(timestamp)
            buffer_count = buffer_count + 1

            # IS THIS RIGHT FOR 12-BIT?
            buffer_contents = ct.cast(
                buffer_pointer, ct.POINTER(ct.c_ubyte * buffer_size)
                ).contents

            # Check for keypress to decide whether to start saving
            if not instruct_queue.empty():
                # Giving 'save' or 'preview'
                save_instruction = instruct_queue.get()

            # Add to stack to save if saving initiated
            if save_instruction == 'save':
                output_file.write(buffer_contents)
                storage_size = storage_size + buffer_size

            # Display images in parallel process via queue
            if time.time() - t_start > \
                    live_view_count * live_view_dt:
                image_data = buffer_contents[0:image_size]
                display_queue.put(image_data)
                live_view_count = live_view_count + 1

            # Stop on terminate signal in display process
            if display_process.exitcode == 0:
                acquire = 'terminate'
                timestamp = buffer.get_info(cmd=3, info_datatype=8)
                timestamps.append(buffer.get_info(cmd=3, info_datatype=8))
                t_end = time.time()

    if len(timestamps) > 0:

        timestamp_range = timestamps[-1] - timestamps[0]
        print('\nTimestamp at buffer 1: {} us'.format(timestamps[0]))
        print('Timestamp at buffer {}: {} us'
              .format(buffer_count, timestamps[-1])
              )
        print('Time between first and last timestamps: {} us'.format(
                timestamp_range
                )
              )
        # Use buffer_count - 1 as divisor to calculate timings,
        # as we have first and last timestamps, no timestamp before acquiring
        # the first buffer
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

    print('Closing images bytes output file...')
    output_file.close()
#    print('Reading and converting image bytes to image stack...')
    # Convert saved byte list to image stack
#    bytes_path = output_path / 'images_bytes'
#    with open(bytes_path, 'rb') as file_to_convert:
#        image_data = file_to_convert.read()
#    image_data = np.frombuffer(image_data, dtype=np.uint8)
#    image_data = image_data.reshape((
#        int(storage_size / cmd_args.roi_height / cmd_args.roi_width),
#        cmd_args.roi_height,
#        cmd_args.roi_width
#        ))
    # Delete save byte list and save image stack
#    print('Deleting raw bytes file...')
#    bytes_path.unlink()
#    print('Saving image stack...')
#    np.save(output_path / 'image_stack.npy', image_data)

    # Stop processes and empty queues if necessary
    if display_process.exitcode is None:
        display_queue.put(None)
        time.sleep(0.1)
    while not display_queue.empty():
        display_queue.get()
        time.sleep(0.1)

    # Stop output processes
    # print('\nStill writing data to disk...')

    t0 = time.time()

    # if save_process.exitcode is None:
    #    save_queue.put(None)

    # Make sure other queues are empty
    if not instruct_queue.empty():
        instruct_queue.get()
    print('{:.1f} s after closing instruct_queue'
          .format(time.time() - t0)
          )

    print('\nDone.')
    print('{:.1f} s when done.'
          .format(time.time() - t0)
          )


if __name__ == '__main__':
    main()
