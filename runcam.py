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

from input_output import display_from_buffer_queue_multiprocess
from input_output import display_timings
from input_output import get_cmd_inputs
from input_output import set_output_path, display_grabber_settings
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
        verbose=False
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
    live_view_dt = 0.5

    live_view_count = 1

    print('\nAcquiring data...')
    print('\nPress \'t\' to terminate,'
          '\n\'s\' to save data,'
          '\n\'p\' for preview mode (no saving)...'
          '\n(If you have selected another window in the meantime,'
          ' click on the display window first.)'
          )
    print('\nTo zoom, press + or -.')

    acquire = True
    already_saving = False
    storage_size = 0
    buffer_size = \
        images_per_buffer * cmd_args.roi_height * cmd_args.roi_width
    image_size = cmd_args.roi_height * cmd_args.roi_width
    # height = cmd_args.roi_height
    # width = cmd_args.roi_width
    # t_stop = t_start + 10

    output_filename = 'images_bytes_'
    output_number = 0

    t_start = time.time()
    # while t < t_stop:
    while acquire:
        with Buffer(grabber) as buffer:
            # Check for keypress to decide whether to start saving,
            # stop saving or terminate
            # Take appropriate actions in response
            if not instruct_queue.empty():
                # Giving 'save', 'preview' or 'termintate'
                save_instruction = instruct_queue.get()

                if save_instruction == 'save':
                    if not already_saving:
                        output_file = open(
                            output_path / (output_filename
                                           + repr(output_number)
                                           ), 'wb'
                            )
                        buffer_count = 0
                        timestamps = [buffer.get_info(cmd=3, info_datatype=8)]

                        already_saving = True

                elif save_instruction == 'preview':
                    # If saving had been in progress,
                    # there will be an entry in timestamps[]
                    # Include the last timestamp and display timings
                    if len(timestamps) == 1:
                        timestamp = buffer.get_info(cmd=3, info_datatype=8)
                        timestamps.append(timestamp)
                        print('\nTimings of saved file:')
                        display_timings(timestamps,
                                        buffer_count,
                                        images_per_buffer
                                        )

                        output_file.close()
                        output_number = output_number + 1
                        already_saving = False

                elif save_instruction == 'terminate':
                    # If saving had been in progress,
                    # there will be an entry in timestamps[]
                    # Include the last timestamp and display timings
                    if len(timestamps) == 1:
                        timestamp = buffer.get_info(cmd=3, info_datatype=8)
                        timestamps.append(timestamp)
                        display_timings(timestamps,
                                        buffer_count,
                                        images_per_buffer
                                        )

                        output_file.close()

                    already_saving = False
                    acquire = False
                    continue

            buffer_pointer = buffer.get_info(BUFFER_INFO_BASE,
                                             INFO_DATATYPE_PTR
                                             )

            # IS THIS RIGHT FOR 12-BIT?
            buffer_contents = ct.cast(
                buffer_pointer, ct.POINTER(ct.c_ubyte * buffer_size)
                ).contents

            # Add to stack to save if saving initiated
            if already_saving:
                buffer_count = buffer_count + 1
                output_file.write(buffer_contents)
                storage_size = storage_size + buffer_size

            # Display images in parallel process via queue
            if time.time() - t_start > \
                    live_view_count * live_view_dt:
                image_data = buffer_contents[0:image_size]
                display_queue.put(image_data)
                live_view_count = live_view_count + 1

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
#    if display_process.exitcode is None:
#        display_queue.put(None)
#        time.sleep(0.1)
#    while not display_queue.empty():
#        display_queue.get()
#        time.sleep(0.1)

    # if save_process.exitcode is None:
    #    save_queue.put(None)

    # Make sure other queues are empty
#    if not instruct_queue.empty():
#        instruct_queue.get()
#    print('{:.1f} s after closing instruct_queue'
#          .format(time.time() - t0)
#          )


if __name__ == '__main__':
    main()
