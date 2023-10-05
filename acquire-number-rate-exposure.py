"""Acquire N frames at frame rate R and exposure time X"""

from egrabber import EGenTL, EGrabber, Buffer
# from egrabber import *
from pathlib import Path
# import numpy as np
import argparse
import sys
import time


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

    try:
        output_path.mkdir()
    except FileExistsError:
        print('\n'
              '*** Please choose an output directory '
              'that does not already exist and start again.'
              )
        sys.exit()

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


def unscramble_phantom_S710_output(grabber,
                                   pixelformat='Mono8',
                                   banks='Banks_AB'
                                   ):
    """Set grabber remote and stream to produce unscrambled images
    from the Phantom S710 middle-outwards reading sequence.

    May need editing for using all four banks. This is initially written
    to use two banks.

    Args:
        grabber (EGrabber object):
            Frame grabber object to set up for acquisition
        pixelformat (string):
            Grabber pixel format setting
        banks (string):
            Grabber banks setting
    """
    if pixelformat != 'Mono8':
        print('Unsupported {} pixel format.'
              'This sample works with Mono8 pixel format only.'
              .format(pixelformat)
              )
    else:
        # Set up the use two banks - although one bank gives full resolution!
        grabber.remote.set('Banks', banks)  # 2 banks

        # Set up stream to unscramble the middle-outwards reading sequence
        grabber.stream.set('StripeArrangement', 'Geometry_1X_2YM')
        grabber.stream.set('LineWidth', 1280)
        # LinePitch = 0 should be default and fine
        grabber.stream.set('StripeHeight', 1)
        grabber.stream.set('StripePitch', 1)
        grabber.stream.set('BlockHeight', 8)
        # StripeOffset = 0 should be default and fine

        # Adding a pause helped in a previous script
        # to allow grabber settings to take effect
        # Works without at the moment, since running the other settings
        # takes some time anyway.
        # time.sleep(0.1)


def get_cmd_inputs():
    """Get command prompt inputs for acquisition."""
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
                        ' Must be < round(1e6 / fps - 1).'
                        )

    args = parser.parse_args()

    return args


def main():
    # Get user settings
    user_settings = get_cmd_inputs()
    n_frames = user_settings.n_frames
    fps = user_settings.fps
    exp_time = user_settings.exp_time

    # Check and set exposure time against fps
    exp_time = check_and_set_exposure(fps, exp_time)

    # Display timings
    print('fps = {:.1f}'.format(fps))
    print('cycling time = {:.1f}'.format(1e6 / fps), 'us')
    print('exp_time =', exp_time, 'us')

    # Create grabber
    gentl = EGenTL()
    grabber = EGrabber(gentl)

    # Set up grabber stream for unscrambled images
    unscramble_phantom_S710_output(grabber)

    # Configure fps and exposure time
    grabber.remote.set('AcquisitionFrameRate', fps)
    time.sleep(0.001)  # Allow fps to set first
    grabber.remote.set('ExposureTime', exp_time)

    # Make a buffer ready for every frame and start
    grabber.realloc_buffers(n_frames)
    grabber.start(n_frames)

    # Set up saving location
    output_path = set_output_path()

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
