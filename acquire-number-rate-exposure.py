"""Acquire N frames at frame rate R and exposure time X"""

from egrabber import EGenTL, EGrabber, Buffer
from pathlib import Path
# import numpy as np
# import sys
import cv2
import math
import time
import set_grabber_properties
from convert_data import get_buffer_properties_as_8bit, mono8_to_ndarray


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


def main():
    # Get script arguments
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

    # Set up saving location and filename length
    output_path = set_output_path()
    print('\nOutput will be saved in {}'.format(output_path))
    len_frame_number = math.floor(math.log10(cmd_args.n_frames - 1)) + 1

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
    time.sleep(0.001)  # Allow fps to set first
    grabber.remote.set('ExposureTime', exp_time)

    # Make a buffer ready for every frame and start
    print('\nAllocating buffers...')
    # grabber.realloc_buffers(cmd_args.n_frames)
    grabber.realloc_buffers(1000)
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
    print('\nAcquiring data...')
    for frame in range(cmd_args.n_frames):
        buffer = Buffer(grabber)

        timestamps.append(buffer.get_info(cmd=3, info_datatype=8))
        # if cmd_args.bit_depth != 8:
        #     buffer.convert('Mono8')  # TRY HIGHER AGAIN FOR 12-BIT

        # IF CONVERTING ALL TO NUMPY AS WE GO
        # ptr_address, width, height, size = \
        #     get_buffer_properties_as_8bit(buffer)
        # ptr_addresses.append(ptr_address)
        # numpy_image = mono8_to_ndarray(ptr_address, width, height, size)

        # Preview after the preview frame time
        if timestamps[-1] - timestamps[0] > \
                preview_count * preview_frames_dt:
            # Remove this conversion to numpy if
            # already doing it for every frame
            buffer_props_8bit = get_buffer_properties_as_8bit(buffer)
            numpy_image = mono8_to_ndarray(*buffer_props_8bit)
            cv2.imshow('Preview', numpy_image)
            cv2.waitKey(1)
            preview_count = preview_count + 1

        buffer.save_to_disk(
            str(output_path.joinpath('{:0{length}d}.tiff'
                                     .format(frame, length=len_frame_number))
                )
            )

        # Allow recyling of the buffer allocation
        buffer.push()

    print('\nDone.')

    if len(timestamps) > 0:
        print('\nTime at frame 0: {} us'.format(timestamps[0]))
        print('Time at frame {}: {} us'.format(len(timestamps) - 1,
                                               timestamps[-1]
                                               )
              )
        print('Time elapsed = {} us'.format(timestamps[-1] - timestamps[0]))

    # OPTION IF RETAINING ALL FRAMES IM MEMORY ############
    # AND SAVING AS ONE FILE ##############################
    # Save the data at the pointers #
    # print('\nAssembling data to save...')
    # Initialise array to save
    # all_frames = np.zeros((cmd_args.n_frames,
    #                       cmd_args.roi_height,
    #                       cmd_args.roi_width
    #                       )
    #                      )

    # Populate with converted data from the pointers
    # for frame, ptr_address in enumerate(ptr_addresses):
    #    if frame % 1000 == 0:
    #        print('Frame {} of {}.'.format(frame, cmd_args.n_frames))
    #    all_frames[frame] = mono8_to_ndarray(ptr_address, width, height, size)

    # Save
    # output_path = output_path.joinpath(
    #   '{}frames_{}height_{}width_numpy_tofile'.format(cmd_args.n_frames,
    #                                                   cmd_args.roi_height,
    #                                                   cmd_args.roi_width
    #                                                   )
    #   )
    # print('\nSaving binary file at {}'.format(output_path))
    # print('...')
    # all_frames.tofile(output_path)


if __name__ == '__main__':
    main()
