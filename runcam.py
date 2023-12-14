"""Acquire N frames at frame rate R and exposure time X"""


# import cv2
import ctypes as ct
import sys
import time

# from math import ceil
from multiprocessing import Queue, Process

# import numpy as np

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
    output_path_parent = set_output_path()
    print('\nOutput will be saved in {}'.format(output_path_parent))
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
                                    cmd_args.roi_width,
                                    cmd_args.bit_depth
                                    )
                              )
    display_process.start()

    # Pre-allocate multi-part buffers and start
    print('\nAllocating buffers...')
    grabber, images_per_buffer = pre_allocate_multipart_buffers(
        grabber,
        images_per_buffer=200,
        duration_allocated_buffers=0.1,
        verbose=False
        )
    grabber.start()

    # Initialise list of buffer pointer addresses
    # Useful if retaining frames in memory to access later
    # ptr_addresses = []

    # List for measuring speed
    timestamps = []
    # In microseconds, for buffer timestamps, seconds for Python time
    live_view_dt = 0.25
    live_view_count = 1

    acquire = True
    already_saving = False

    buffer_count = 0
#    storage_size = 0
    image_size = cmd_args.roi_height * cmd_args.roi_width

    # height = cmd_args.roi_height
    # width = cmd_args.roi_width

    # Reading + unpacking options for 12-bit data
    # 10 to 14-bit buffer is by default unpacked into 16 bits
    # by the Coaxlink frame grabber,
    # aligned to the least significant bit
    buffer_dtype = ct.c_uint8

    # For storing 12-bit as 8-bit:
    if cmd_args.bit_depth == 12:
        if cmd_args.roi_height % 2 != 0 and cmd_args.roi_height % 2 != 0:
            print('Height and width of ROI must be even numbered.'
                  '\nTry again.')
            sys.exit()
    image_size = int(image_size * cmd_args.bit_depth / 8)

    buffer_size = \
        images_per_buffer * image_size

#    if cmd_args.bit_depth == 8:
#        buffer_dtype = ct.c_ubyte
#    elif cmd_args.bit_depth > 8 and cmd_args.bit_depth <= 16:
#        buffer_dtype = ct.c_uint16
#        grabber.stream.set('UnpackingMode', 'Off')
#    else:
#        print('Bit depth {} not usable in display process.'
#              .format(cmd_args.bit_depth)
#              )
#        sys.exit()

    output_filename_stem = 'images_{}bit_'.format(cmd_args.bit_depth)
    if cmd_args.bit_depth > 8 and cmd_args.bit_depth <= 16:
        output_filename_stem = \
            output_filename_stem + 'readas16bit_'

    output_number = 0

    print('\nAcquiring data...')
    print('\nPress \'t\' to terminate,'
          '\n\'s\' to save data,'
          '\n\'p\' for preview mode (no saving)...'
          '\n(If you have selected another window in the meantime,'
          ' click on the display window first.)'
          )
    print('\nTo zoom, press + or -.')

    # t_stop = t_start + 10
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
                        output_filename = \
                            output_filename_stem + repr(output_number) + '_'
                        output_path = output_path_parent / output_filename
                        output_file = open(output_path, 'wb')
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

                        # Rename to add more info on contents
                        final_filename = \
                            output_filename + '{}images_H{}_W{}'.format(
                                buffer_count * images_per_buffer,
                                cmd_args.roi_height,
                                cmd_args.roi_width
                                )
                        output_path.rename(output_path_parent / final_filename)

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

                        # Rename to add more info on contents
                        final_filename = \
                            output_filename + '{}images_H{}_W{}'.format(
                                buffer_count * images_per_buffer,
                                cmd_args.roi_height,
                                cmd_args.roi_width
                                )
                        output_path.rename(output_path_parent / final_filename)

                    already_saving = False
                    acquire = False
                    continue

            buffer_pointer = buffer.get_info(BUFFER_INFO_BASE,
                                             INFO_DATATYPE_PTR
                                             )

            buffer_contents = ct.cast(
                buffer_pointer, ct.POINTER(buffer_dtype * buffer_size)
                ).contents
#            buffer_contents = \
#                (buffer_dtype * buffer_size).from_address(buffer_pointer)

            # Add to stack to save if saving initiated
            if already_saving:
                buffer_count = buffer_count + 1
                output_file.write(buffer_contents)
                # For saving in chunks - slows acquisition down very slightly
                # at 86k fps (highest frmae rate tested)
#                storage_size = storage_size + buffer_size
#                if storage_size > 1e10:
#                    output_file.close()
#                    output_number = output_number + 1
#                    storage_size = 0
#                    output_file = open(
#                        output_path / (output_filename
#                                       + repr(output_number)
#                                       ), 'wb'
#                        )

            # Display images in parallel process via queue
            if time.time() - t_start > \
                    live_view_count * live_view_dt:
                image_data = buffer_contents[0:image_size]
                # display_queue.put(123)
                display_queue.put(image_data)
                live_view_count = live_view_count + 1

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
