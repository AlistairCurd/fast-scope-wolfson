"""Acquire N frames at frame rate R and exposure time X"""

from egrabber import EGenTL, EGrabber, Buffer
# import numpy as np
# import sys
# import cv2
# import math
import time
import set_grabber_properties
# from convert_display_data import display_8bit_numpy_opencv
from input_output import set_output_path


def main():
    # Get script arguments
    cmd_args = set_grabber_properties.get_cmd_inputs()

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

    # Make a buffer ready for every frame and start
    print('\nAllocating buffers...')

    # Multi-part buffer for speed
    t_alloc_start = time.time()
    # parts_per_buffer = 100
    # grabber.stream.set('BufferPartCount', parts_per_buffer)
    num_buffers = 860
    grabber.realloc_buffers(num_buffers)
    print('Buffer allocation took {} s.'.format(time.time() - t_alloc_start))

    grabber.start()

    # Measure speed
    timestamps = []

    # Set frame time for live preview
    preview_frames_dt = 0.2 * 1e6  # microseconds
    preview_count = 1

    # Initialise list of buffer pointer addresses
    # Useful if retaining frames in memory to access later
    # ptr_addresses = []

    # Acquire data!
    buffer_count = 0
    t_start = time.time()
    t_stop = t_start + 10
    t = t_start
    print('\nAcquiring data...')
    while t < t_stop:
        with Buffer(grabber) as buffer:
            timestamps.append(buffer.get_info(cmd=3, info_datatype=8))
            buffer_count = buffer_count + 1
            t = time.time()

        # if cmd_args.bit_depth != 8:
        #     buffer.convert('Mono8')  # TRY HIGHER AGAIN FOR 12-BIT

        # Preview after the preview frame time
        # if timestamps[-1] - timestamps[0] > \
        #        preview_count * preview_frames_dt:
        #    # Convert to numpy and display
        #    display_8bit_numpy_opencv(buffer)
        #    preview_count = preview_count + 1

        # buffer.save_to_disk(
        #    str(output_path.joinpath('{:0{length}d}.tiff'
        #                             .format(frame, length=len_frame_number))
        #        )
        #    )

        # Allow recyling of the buffer allocation
        # buffer.push()

    print('\nDone.')

    if len(timestamps) > 0:
        print('\nTime at frame 0: {} us'.format(timestamps[0]))
        print('Time at frame {}: {} us'.format(len(timestamps) - 1,
                                               timestamps[-1]
                                               )
              )
        print('Time elapsed = {} us'.format(timestamps[-1] - timestamps[0]))

    print('Acquired {} buffers over {} s.'
          .format(buffer_count, t - t_start))


if __name__ == '__main__':
    main()
