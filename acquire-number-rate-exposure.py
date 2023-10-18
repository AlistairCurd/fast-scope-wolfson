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

#    try:
#        output_path.mkdir()
#    except FileExistsError:
#        print('\n'
#              '*** Please choose an output directory '
#              'that does not already exist and start again.'
#              )
#        sys.exit()

    return output_path


def main():
    # Get user settings
    user_settings = set_grabber_properties.get_cmd_inputs()
    n_frames = user_settings.n_frames
    fps = user_settings.fps
    exp_time = user_settings.exp_time
    roi_width = user_settings.roi_width
    roi_height = user_settings.roi_height

    # Make sure exposure time is less than cycling time
    # Set if not given
    exp_time = set_grabber_properties.check_and_set_exposure(fps, exp_time)

    # Display settings

    print('\nNumber of frames : {}'.format(n_frames))
    print('Frames per second : {:.1f}'.format(fps))
    print('Cycling time : {:.1f}'.format(1e6 / fps), 'us')
    print('Exposure time :', exp_time, 'us')
    print('Image width: ', roi_width)
    print('Image height: ', roi_height)

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
