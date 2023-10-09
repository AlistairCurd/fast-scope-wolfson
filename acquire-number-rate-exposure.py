"""Acquire N frames at frame rate R and exposure time X"""

from egrabber import EGenTL, EGrabber, Buffer
# from egrabber import *
from pathlib import Path
# import numpy as np
import argparse
import sys
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

#    try:
#        output_path.mkdir()
#    except FileExistsError:
#        print('\n'
#              '*** Please choose an output directory '
#              'that does not already exist and start again.'
#              )
#        sys.exit()

    return output_path


def check_and_set_exposure(fps, exp_time):
    """Check exposure time is compatible with fps,
    or set exposure time close to the limit for the fps setting.

    Exit with a message if the exposure time is too high for the fps.

    Makes sure that exposure time is
    at least 0.5 to 1.5 us less than the buffer cycling period.

    Args:
        fps (float, default 1000):
            Frame rate (frames per second)
        exp_time (int):
            Exposure time (microseconds)

    Returns:
        n_frames (int):
            Number of frames to acquire
        fps (float):
            Frame rate (frames per second)
        exp_time (int):
            Exposure time (microseconds)
    """
    # Set exposure time of not present
    if exp_time is None:
        exp_time = round(1e6 / fps - 1)  # For microseconds

    # Exit gracefully if exposure time is >= 1 / frame rate
    elif exp_time >= round(1e6 / fps - 1):
        print('\n'
              '*** Please choose an \n'
              'exposure time (us) <= round(1 / frames per second - 1) \n'
              'and start again.'
              )
        sys.exit()

    return exp_time


def get_cmd_inputs(allowed_roi_widths=[128, 256, 384, 512, 640, 768, 896,
                                       1024, 1152, 1280
                                       ],
                   max_height=400
                   ):
    """Get command prompt inputs for acquisition.

    Args:
        allowed_roi_widths (list):
            List of ROI widths that do not produce an error.
        max_height (int):
            Maximum ROI height allowed.

    Returns:
        args (argparse.Namespace object):
            Parsed arguments for downstream use.
    """
    parser = argparse.ArgumentParser()

    parser.add_argument('-n', '--numframes',
                        dest='n_frames',
                        type=int,
                        required=True,
                        help='Required. Number of frames to acquire.'
                        )

    parser.add_argument('--fps',
                        dest='fps',
                        type=float,
                        required=True,
                        help='Required. Frame rate (frames per second).'
                        )

    parser.add_argument('-x', '--exposure',
                        dest='exp_time',
                        type=int,
                        help='Optional. Exposure time (microseconds).'
                        ' Must be <= round(1e6 / fps - 1).'
                        )

    parser.add_argument('-W', '--width',
                        dest='roi_width',
                        type=int,
                        default=1280,
                        help='Optional. Width of ROI in pixels.'
                        ' Must be in [128, 256, 384, 512, 640, 768, 896,'
                        ' 1024, 1152, 1280].'
                        )

    # Change default if different number of output banks in use?
    parser.add_argument('-H', '--height',
                        dest='roi_height',
                        type=int,
                        default=400,
                        help='Optional. Height of ROI in pixels.'
                        ' Must be <= 400.'
                        )

    args = parser.parse_args()

    # Check whether height and width will be allowed
    stop = False

    if args.roi_height > max_height:
        print('\nPlease choose an ROI height <= 400 pixels.')
        stop = True

    if args.roi_width not in allowed_roi_widths:
        print('\nPlease choose one of these options for ROI width:'
              '\n128, 256, 384, 512, 640, 768, 896, 1024, 1152, 1280')
        stop = True

    if stop is True:
        sys.exit()

    return args


def main():
    # Get user settings
    user_settings = get_cmd_inputs()
    n_frames = user_settings.n_frames
    fps = user_settings.fps
    exp_time = user_settings.exp_time
    roi_width = user_settings.roi_width
    roi_height = user_settings.roi_height

    # Check exposure time against fps, adjust if necessary
    exp_time = check_and_set_exposure(fps, exp_time)

    # Display timings
    print('\nfps = {:.1f}'.format(fps))
    print('cycling time = {:.1f}'.format(1e6 / fps), 'us')
    print('exp_time =', exp_time, 'us')

    # Set up saving location
    output_path = set_output_path()
    print('\nOutput will be saved in {}'.format(output_path))

    # Create grabber
    gentl = EGenTL()
    grabber = EGrabber(gentl)

    # Set up ROI
    set_grabber_properties.set_roi(grabber, width=roi_width, height=roi_height)

    # Set up grabber stream for unscrambled images
    set_grabber_properties.unscramble_phantom_S710_output(grabber, roi_width)

    # Configure fps and exposure time
    grabber.remote.set('AcquisitionFrameRate', fps)
    time.sleep(0.001)  # Allow fps to set first
    grabber.remote.set('ExposureTime', exp_time)

    # Make a buffer ready for every frame and start
    grabber.realloc_buffers(n_frames)
    grabber.start(n_frames)

    # timestamps = []

    # Acquire image into buffer and save for every frame
    for frame in range(n_frames):
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
