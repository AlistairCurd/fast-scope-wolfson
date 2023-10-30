"""Acquire N frames at frame rate R and exposure time X"""

from egrabber import EGenTL, EGrabber, Buffer
from egrabber import *
from pathlib import Path
# import numpy as np
# import sys
import cv2
import math
import time
from multiprocessing import Process, Queue, freeze_support
import set_grabber_properties
from convert_display_data import display_8bit_numpy_opencv_from_ptr
from convert_display_data import get_buffer_properties_as_8bit
# from convert_display_data import mono8_to_ndarray


def set_output_path(output_parent_dir='C://Temp',
                    output_dir='phantom-images'
                    ):
    """Set and create the output directory for images.

    Fails if directory already exists.

    Args:
        output_parent_dir (string):
            Path to the parent directory for an output directory.
        output_dir (string):
            Name of the output directory.

    Returns:
        output_path (Path object):
            Path to output directory
    """
    output_path = Path(output_parent_dir).joinpath(output_dir)

    # Modify the folder name if it exists, for now
    while output_path.exists():
        output_dir = output_dir + '_'
        output_path = Path(output_parent_dir).joinpath(output_dir)

    output_path.mkdir()

    return output_path


def save_from_queue(savequeue, n_frames, output_path):
    """Receive data when it arrives in savequeue and save each time.
    Stop when a signal arrives in the stopqueue.

    Args:
        savequeue, stopqueue (Multiprocessing Queue objects):
            savequeue should contain one numpy array at a time
        n_frames (int):
            Length of acquisition sequence.
        output_path (Pathlib objuect):
            Path to the directoary in which to save the datafiles
    """
    # len_frame_number = math.floor(math.log10(n_frames - 1)) + 1
    while True:
        if not savequeue.empty():
            queue_entry = savequeue.get()
            if queue_entry == 'stop':
                break
            else:
                numpy_data, frame_number = queue_entry
                # numpy_data.tofile(
                #    output_path.joinpath(
                #        '{:0{length}d}.tiff'.format(frame_number,
                #                                    length=len_frame_number
                #                                    )
                #        )
                #    )
    return


def main():
    # Get script arguments
    cmd_args = set_grabber_properties.get_cmd_inputs()
    roi_size = cmd_args.roi_width * cmd_args.roi_height

    # Make sure exposure time setting will be less than cycling time
    # Choose if not given
    exp_time = set_grabber_properties.check_exposure(cmd_args.fps,
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

    # Set up saving location and filename length
    output_path = set_output_path()
    print('\nOutput will be saved in {}'.format(output_path))
    # len_frame_number = math.floor(math.log10(cmd_args.n_frames - 1)) + 1

    # Create grabber
    gentl = EGenTL()
    grabber = EGrabber(gentl)

    # Set bit-depth
    if cmd_args.bit_depth == 8:
        grabber.remote.set('PixelFormat', 'Mono8')
    if cmd_args.bit_depth == 12:
        grabber.remote.set('PixelFormat', 'Mono12')

    # Set up grabber stream for unscrambled images,
    # including the right banks
    set_grabber_properties.unscramble_phantom_S710_output(
        grabber, cmd_args.roi_width, bit_depth=cmd_args.bit_depth
        )

    # Set up ROI
    set_grabber_properties.set_roi(grabber,
                                   width=cmd_args.roi_width,
                                   height=cmd_args.roi_height
                                   )

    # Configure fps and exposure time
    grabber.remote.set('AcquisitionFrameRate', cmd_args.fps)
    time.sleep(0.25)  # Allow fps to set first
    grabber.remote.set('ExposureTime', exp_time)

    # Measure speed
    # timestamps = []
#    preview_timestamps = []
#    preview_times = []

    # Set frame time for live preview
    # preview_frames_dt = 0.2  # seconds
    preview_frames_dt = 0.2 * 1e6  # microseconds
    preview_count = 1

    # Initialise list of buffer pointer addresses
    # Useful if retaining frames in memory to access later
    # ptr_addresses = []

    # Create and start parallel processes for displaying images,
    # with queues for receiving data
    # savequeue = Queue()
    # Activate imagequeue so that it takes less time to put real data in.
    # savequeue.put('firstinput')
    # savequeue.get()
    # number_of_processes = 16

    # processes = [0, 0]
    # processes = []
    # for i in range(number_of_processes):
        # Process(target=save_from_queue, args=(savequeue,
        #                                          cmd_args.n_frames,
        #                                          output_path,
        #                                          stopqueue,
        #                                          )
        #        ).start()
        # p = Process(target=save_from_queue, args=(savequeue,
        #                                          cmd_args.n_frames,
        #                                          output_path,
        #                                          )
        #            )
        # processes.append(p)
        # p.start()

    # Pre-allocate buffer area and start
    print('\nAllocating buffers...')
    # grabber.realloc_buffers(cmd_args.n_frames)
    pre_buffer_alloc = time.time()
    grabber.stream.set('BufferPartCount', 100)  # Images ready per buffer
    grabber.realloc_buffers(int(cmd_args.fps / 100))
    print('Time to allocate buffer: {}'
          .format(time.time() - pre_buffer_alloc)
          )
    # Try one second's worth of buffer
    # grabber.realloc_buffers(int(cmd_args.fps))
    grabber.start()

    # Create buffer and get properties
    buffer = Buffer(grabber)

    buffer_props_8bit = get_buffer_properties_as_8bit(buffer)

    # print('Initial buffer props: ', buffer_props_8bit, '\n')
    buffer.push()

    # Acquire data!
    print('\nAcquiring data...')
    # last_frame = cmd_args.n_frames - 1
    # for frame in range(cmd_args.n_frames):
    # frame = 0

    buffer_num = 0
    t_start = time.time()
    t_show = t_start + 0.25
    t_report = t_start + 2
    t_stop = t_start + 5
    t_start = time.time()
    t = t_start
    while t < t_stop:
        with Buffer(grabber, timeout=1000) as buffer:

            t = time.time()

            bufferPtr = buffer.get_info(BUFFER_INFO_BASE, INFO_DATATYPE_PTR)
            # imageSize = buffer.get_info(BUFFER_INFO_CUSTOM_PART_SIZE, INFO_DATATYPE_SIZET)
            delivered = buffer.get_info(BUFFER_INFO_CUSTOM_NUM_DELIVERED_PARTS, INFO_DATATYPE_SIZET)
            processed = 0
            while processed < delivered:
                if t > t_show:
                    imagePtr = bufferPtr + processed * roi_size  # * imageSize
                    # processImage(imagePtr, w, h, imageSize)
                    # display_8bit_numpy_opencv_from_ptr(imagePtr,
                    #                                   cmd_args.roi_width,
                    #                                   cmd_args.roi_height,
                    #                                   imageSize)

                # if t > t_report:
                #    fr = grabber.stream.get('StatisticsFrameRate')
                #    print('Acquiring at {} fps.'.format(int(fr)))
                #    t_report = t_report + 2

                processed = processed + 1

            # buffer.save_to_disk(
            #    str(output_path.joinpath('{}.tiff'
            #                             .format(buffer_num
            #                                     )
            #                             )
            #        )
            #    )

            buffer_num = buffer_num + 1

            # t_fin = time.time()

        #    cv2.imshow('Preview', numpy_image)
        #    cv2.waitKey(1)

        # buffer.push()

        # if cmd_args.bit_depth != 8:
        #     buffer.convert('Mono8')  # TRY HIGHER AGAIN FOR 12-BIT

        # savequeue.put([numpy_image, frame])

        # buffer.save_to_disk(
        #    str(output_path.joinpath('{:0{length}d}.tiff'
        #                             .format(frame, length=len_frame_number))
        #        )
        #    )

        # displayqueue.get()

        # Allow recyling of the buffer allocation
        # buffer.push()

    # Allow parallel save Processes to end with stop signal
    # Pause is needed for all processes to get one of these!
    # for i in range(number_of_processes):
    #    stopqueue.put('stop')
    #    time.sleep(0.1)

    # for p in processes:
    #    while p.exitcode is None:
    #        savequeue.put('stop')
    #        print(p.exitcode)
    #        time.sleep(0.1)

    # print('Saved')

    # FINISHED ACQUIRING!
    print('\nDone.')

    # if len(timestamps) > 0:
        # print('\nTime at frame 0: {} us'.format(timestamps[0]))
        # print('Time at frame {}: {} us'.format(len(timestamps) - 1,
        #                                       timestamps[-1]
        #                                       )
        #      )
        # print('Time elapsed = {} us'.format(timestamps[-1] - timestamps[0]))
    # else:
    #    print('No timestamps')

    # print('Time elapsed = {} us'.format(timestamp_end - timestamp_start))
    print('{} buffers acquired.'.format(buffer_num))
    # print('Time elapsed = {} s'.format(t_fin - t_start))

#    print('Preview d_timestamps:', preview_timestamps)
#    print('Preview d_t:', preview_times)


if __name__ == '__main__':
    freeze_support()
    main()
