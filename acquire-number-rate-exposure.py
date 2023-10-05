"""Acquire N frames at frame rate R and exposure time X"""

from egrabber import EGenTL, EGrabber, Buffer
# from egrabber import *
from pathlib import Path
# import numpy as np
import sys
# import time


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


def get_acq_settings(n_frames=100, fps=1000, exp_time=None):
    """Get the acquisition settings.

    This will probably switch to arg_parse soon.

    Makes sure that exposure time is
    at least 1us less than the buffer cycling period.

    
    
    Args:
        n_frames (int, default 100):
            Number of frames to acquire
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

    return n_frames, fps, exp_time


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


def main():
    # Get acquisition settings
    n_frames, fps, exp_time = get_acq_settings(n_frames=10,
                                               fps=1000
                                               )
    print('fps = {:.1f}'.format(fps))
    print('cycling time = {:.1f}'.format(1e6 / fps))
    print('exp_time =', exp_time)

    # Create grabber
    gentl = EGenTL()
    grabber = EGrabber(gentl)

    # Set up grabber stream for unscrambled images
    unscramble_phantom_S710_output(grabber)

    # Configure fps and exposure time
    grabber.remote.set('AcquisitionFrameRate', fps)
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
