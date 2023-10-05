"""Acquire N frames at frame rate R and exposure time X"""

from egrabber import *
from pathlib import Path
import time


def set_output_dir(output_parent_dir='.',
                   output_dir='phantom-images'
                   ):
    """Set and create the output directory for images.
    
    Args:
        output_parent_dir (string):
            Path to the parent directory for an output directory.
        output_dir (string):
            Name of the output directory.
    """
    output_dir = Path(output_parent_dir).joinpath(output_dir)
    output_dir.mkdir()
    
    return output_dir

def get_acq_settings(n_frames=5, fps=1000, exp_time=1000):
    """Get the acquisition settings.

    This will probably switch to arg_parse soon.

    Args:
        n_frames (int):
            Number of frames to acquire
        fps (float):
            Frame rate (frames per second)
        exp_time (exposure time):
            Exposure time (microseconds)
    """
    return n_frames, fps, exp_time

def unscramble_phantom_S710_output(grabber,
                                   pixelformat='Mono8',
                                   banks='Banks_AB'
                                   ):
    """Set grabber remote and stream to produce unscrambled images from the Phantom S710
    middle-outwards reading sequence.

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
              .format(pixelFormat)
              )
    else:
        # Set up the use o two banks - although one bank gives full resolution!
        grabber.remote.set('Banks', banks) # 2 banks

        # Set up stream to unscramble the middle-outwards reading sequence
        grabber.stream.set('StripeArrangement', 'Geometry_1X_2YM')
        grabber.stream.set('LineWidth', 1280) # LinePitch = 0 should be default and fine
        grabber.stream.set('StripeHeight', 1)
        grabber.stream.set('StripePitch', 1)
        grabber.stream.set('BlockHeight', 8)
        # StripeOffset = 0 should be default and fine

        # Add a pause to allow grabber settings to take effect
        # Try without, since running the other settings will take some time anyway.
        # time.sleep(0.1)


def main():
    # Set saving location
    output_dir = set_output_dir()

    # Get acquisition settings
    n_frames, fps, exp_time = get_acq_settings()

    # Create grabber
    gentl = EGenTL()
    grabber = EGrabber(gentl)

    # Set up grabber stream for unscrambled images
    unscramble_phantom_S710_output(grabber)

    # Acquire
    grabber.realloc_buffers(n_frames)
    grabber.start(n_frames)
    for frame in range(n_frames):
        buffer = Buffer(grabber)
        # THIS DOES NOT USE output_dir YET
        buffer.save_to_disk('.//phantom-images//{}.jpeg'.format(frame))
        buffer.push()


if __name__ == '__main__':
    main()
