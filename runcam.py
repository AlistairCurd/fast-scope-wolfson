"""Acquire N frames at frame rate R and exposure time X"""


# import cv2
import ctypes as ct
import sys
import time

from math import ceil
from multiprocessing import Queue, Process

import numpy as np

from egrabber import Buffer
# from egrabber import BUFFER_INFO_BASE, INFO_DATATYPE_PTR

from convert_display_data import buffer_to_list

from input_output import display_from_buffer_queue_multiprocess
from input_output import display_timings
from input_output import get_cmd_inputs
from input_output import set_output_path, display_grabber_settings
from input_output import do_instruction
from set_grabber_properties import create_and_configure_grabbers


def main():
    # Get script arguments
    cmd_args = get_cmd_inputs()

    # Set up saving location and filename length
    output_path_parent = set_output_path()
    print('\nOutput will be saved in {}'.format(output_path_parent))
    # len_frame_countber = math.floor(math.log10(cmd_args.n_frames - 1)) + 1

    # Create and configure grabbers
    # print('\nSetting up grabbers...')
    camgrabber, egrabbers, images_per_buffer = \
        create_and_configure_grabbers(cmd_args)

    # Display settings
    print('\nAcquisition settings:')
    display_grabber_settings(cmd_args, egrabbers[0])

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

#    dummy_image_data = np.zeros(cmd_args.roi_height * cmd_args.roi_width)

    # Initialise list of buffer pointer addresses
    # Useful if retaining frames in memory to access later
    # ptr_addresses = []

    # List for measuring speed
    timestamps = []
    # In microseconds, for buffer timestamps, seconds for Python time

    live_view_dt = 0.25
    live_view_count = 1

    # # IMAGE SIZE AND BUFFER SIZE
    image_size = cmd_args.roi_height * cmd_args.roi_width

    # Reading + unpacking options for 12-bit data
    # 10 to 14-bit buffer is by default unpacked into 16 bits
    # by the Coaxlink frame grabber,
    # aligned to the least significant bit
    # buffer_dtype = ct.c_uint8

    # For storing 12-bit as 8-bit:
    if cmd_args.bit_depth == 12:
        if cmd_args.roi_height % 2 != 0 and cmd_args.roi_height % 2 != 0:
            print('Height and width of ROI must be even numbered.'
                  '\nTry again.')
            sys.exit()
    # image_size = int(image_size * cmd_args.bit_depth / 8)

    if cmd_args.bit_depth == 8:
        buffer_dtype = ct.c_ubyte
    elif cmd_args.bit_depth == 12:
        # 16-bit buffer elements for unpacking
        buffer_dtype = ct.c_uint16
        # ADD 8-bit in for PACKING 12-bit data
    else:
        print('Bit depth {} not usable in display process.'
              .format(cmd_args.bit_depth)
              )
        sys.exit()

    buffer_size = \
        images_per_buffer * image_size

    # Trigger and sequence length
    trig_level = cmd_args.trigger_level
    seq_len = cmd_args.seq_length
    triggered = False

    # Add bit depth and reading info to filename
    output_filename_stem = 'images_{}bit_'.format(cmd_args.bit_depth)
    if cmd_args.bit_depth == 12 and \
            egrabbers[0].stream.get('UnpackingMode') != 'Off':

        output_filename_stem = \
            output_filename_stem + 'readas16bit_'

    output_number = 0

    # START DISPLAY PROCESS AND ACQUISITION
    display_process.start()

#    for grabber in reversed(grabbers):
#        grabber.start()  # NOT FOR UNIFIED CAMERA
    camgrabber.start()

    print('\nAcquiring data...')
    print('\nPress \'t\' to terminate,'
          '\n\'s\' to save data,'
          '\n\'p\' for preview mode (no saving)...'
          '\n(If you have selected another window in the meantime,'
          ' click on the display window first.)'
          )
    print('\nTo zoom, press + or -.')

    # Set up to start acquisition without saving
    acquire = True
    enable_saving = False
    buffer_count = 0
    output_filename = '{}{}_H{}_W{}_'.format(
        output_filename_stem, output_number,
        cmd_args.roi_height, cmd_args.roi_width
        )
    output_path = output_path_parent / output_filename
    output_file = open(output_path, 'wb')

    # Trigger and sequence length
    trig_level = cmd_args.trigger_level
    seq_len = cmd_args.seq_length
    max_buffer_count = ceil(seq_len / images_per_buffer)
    triggered = False

    # t_stop = t_start + 10
    t_start = time.time()
    # while t < t_stop:
    while acquire:
        if not enable_saving:
            with Buffer(camgrabber) as buffer:
                buffer_contents = buffer_to_list(buffer,
                                                 buffer_dtype,
                                                 buffer_size
                                                 )

        # Saving is enabled from keypress, registered in
        # do_instruction() below
        if enable_saving:

            # Wait for trigger and activate above intensity threshold:
            if not triggered:
                with Buffer(camgrabber) as buffer:
                    buffer_contents = buffer_to_list(buffer,
                                                     buffer_dtype,
                                                     buffer_size
                                                     )
                    # print('max: {}'.format(max(buffer_contents)))
                    # This test fails when BufferPartCount is too low
                    # for the acquisition rate.
                    # Sometimes it does not crash but gives incorrect values
                    # - too high.
                    if np.max(buffer_contents) > trig_level:
                        triggered = True
                        output_filename = '{}{}_H{}_W{}_'.format(
                            output_filename_stem, output_number,
                            cmd_args.roi_height, cmd_args.roi_width
                            )
                        output_path = output_path_parent / output_filename
                        output_file = open(output_path, 'wb')

                        # Use this line to test for the triggering
                        # to saving time at the end
                        # timestamp_trig = buffer.get_info(cmd=3,
                        #                                  info_datatype=8)

                        # Set this up to use to display timings.
                        timestamps = []
                        timestamps.append(
                            buffer.get_info(cmd=3, info_datatype=8))

            # If triggered:
            else:
                for buffer_count in range(max_buffer_count):
                    with Buffer(camgrabber) as buffer:
                        buffer_contents = buffer_to_list(buffer,
                                                         buffer_dtype,
                                                         buffer_size
                                                         )

                        timestamp = buffer.get_info(cmd=3, info_datatype=8)
                        # Get first timestamp
                        if not buffer_count:
                            timestamps.append(timestamp)

                        # Write the data for the sequence length
                        # (if not interrupted)
                        # if frame_count < seq_len:
                        output_file.write(buffer_contents)

                        # Display images in parallel process via queue
                        # within loop
                        if time.time() - t_start > \
                                live_view_count * live_view_dt:
                            # Use first frame in buffer
                            display_queue.put(buffer_contents[0:image_size])
                            # display_queue.put(dummy_image_data)
                            live_view_count = live_view_count + 1

                        # Check for keypress to decide whether to enable
                        # saving (redundant here), go to preview mode
                        # or terminate, within loop
                        if not instruct_queue.empty():
                            enable_saving, triggered, acquire, \
                                buffer_count, output_number = \
                                do_instruction(
                                    instruct_queue.get(),
                                    buffer,
                                    egrabbers[0].stream.get('BufferPartCount'),
                                    # buffer_count + 1
                                    # since starting at zero
                                    timestamps, buffer_count + 1,
                                    output_file, output_filename,
                                    output_path, output_number,
                                    enable_saving,
                                    triggered,
                                    acquire
                                    )
                            if not enable_saving:
                                break

                # If the loop is not broken and gets to the end
                # - so not stopped by a command which finishes off
                # the data writing:
                if enable_saving:
                    triggered = False
                    output_file.close()
                    final_filename = '{}{}images'.format(
                        output_filename, (buffer_count + 1) * images_per_buffer
                        )
                    output_path.rename(output_path_parent / final_filename)
                    output_number = output_number + 1
                    # Get the last timestamp
                    timestamps.append(timestamp)
                    # print(timestamps[0])
                    display_timings(timestamps[1:],
                                    buffer_count + 1,
                                    images_per_buffer)

        # Display images in parallel process via queue
        if time.time() - t_start > \
                live_view_count * live_view_dt:
            # Use first frame in buffer
            display_queue.put(buffer_contents[0:image_size])
            # display_queue.put(dummy_image_data)
            live_view_count = live_view_count + 1

        # Check for keypress to decide whether to enable saving,
        # go to preview mode or terminate
        if not instruct_queue.empty():
            enable_saving, triggered, acquire, buffer_count, output_number = \
                do_instruction(instruct_queue.get(),
                               buffer, images_per_buffer,
                               timestamps, buffer_count,
                               output_file,
                               output_filename, output_path, output_number,
                               enable_saving,
                               triggered,
                               acquire
                               )

    # Stop processes and empty queues if necessary
    if display_process.exitcode is None:
        display_queue.put(None)
        time.sleep(0.1)
    while not display_queue.empty():
        display_queue.get()
        time.sleep(0.1)

    # Make sure other queues are empty
    if not instruct_queue.empty():
        instruct_queue.get()

    # Remove last file if no data was saved in it
    # (the only file if no data is saved at all
    [p.unlink() for p in output_path_parent.iterdir() if p.name[-1] == '_']

    # Remove output folder if no data was saved at all
    if not any(output_path_parent.iterdir()):
        output_path_parent.rmdir()

    # Can use this with uncommenting timestamp_trig above to test
    # time between trigger and end of first buffer.
#    if timestamps:
#        print(timestamp_trig)


if __name__ == '__main__':
    main()
