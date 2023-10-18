"""Acquire N frames at frame rate R and exposure time X"""

from egrabber import EGenTL, EGrabber, Buffer
# from egrabber import *
from pathlib import Path
# import numpy as np
# import sys
import time
import set_grabber_properties


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

    # Set up saving location
    output_path = set_output_path()
    print('\nOutput will be saved in {}'.format(output_path))

    # Create grabber
    gentl = EGenTL()
    grabber = EGrabber(gentl)

    # Set up ROI
    set_grabber_properties.set_roi(grabber,
                                   width=cmd_args.roi_width,
                                   height=cmd_args.roi_height
                                   )

    # Set up grabber stream for unscrambled images
    set_grabber_properties.unscramble_phantom_S710_output(grabber,
                                                          cmd_args.roi_width
                                                          )

    # Configure fps and exposure time
    grabber.remote.set('AcquisitionFrameRate', cmd_args.fps)
    time.sleep(0.001)  # Allow fps to set first
    grabber.remote.set('ExposureTime', exp_time)

    # Make a buffer ready for every frame and start
    grabber.realloc_buffers(cmd_args.n_frames)
    grabber.start(cmd_args.n_frames)

    # timestamps = []

    # Acquire image into buffer and save for every frame
    for frame in range(cmd_args.n_frames):
        buffer = Buffer(grabber)
        # timestamps.append(buffer.get_info(cmd=3, info_datatype=8))
        # timestamp = buffer.get_info(cmd=3, info_datatype=8)
        # print('timestamp:', timestamp)
        buffer.save_to_disk(str(output_path.joinpath('{}.jpeg'.format(frame))))
        buffer.push()

    # for t in range(len(timestamps)):
        # print(timestamps[t])


if __name__ == '__main__':
    main()
