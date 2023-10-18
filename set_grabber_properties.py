"""Functions for setting grabber properties
with EGrabber Coaxlink interface"""

import argparse
import sys


def get_cmd_inputs(allowed_roi_widths=[128, 256, 384, 512, 640, 768, 896,
                                       1024, 1152, 1280
                                       ],
                   max_height=400,
                   allowed_bit_depths=[8, 12]
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
    # Include defaults in help text
    parser = argparse.ArgumentParser(
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
        )

    parser.add_argument('-n', '--numframes',
                        dest='n_frames',
                        type=int,
                        default=10,
                        help='Number of frames to acquire.'
                        )

    parser.add_argument('--fps',
                        dest='fps',
                        type=float,
                        default=1000,
                        help='Frame rate (frames per second).'
                        )

    parser.add_argument('-x', '--exposure',
                        dest='exp_time',
                        type=int,
                        help='Exposure time (microseconds).'
                        ' Must be <= round(1e6 / fps - 1).'
                        ' Set to this by default.'
                        )

    parser.add_argument('-W', '--width',
                        dest='roi_width',
                        type=int,
                        default=1280,
                        help='Width of ROI in pixels.'
                        ' Must be in {}.'.format(allowed_roi_widths)
                        )

    # Change default if different number of output banks in use?
    parser.add_argument('-H', '--height',
                        dest='roi_height',
                        type=int,
                        default=400,
                        help='Height of ROI in pixels.'
                        ' Must be <= {}.'.format(max_height)
                        )

    parser.add_argument('-b,', '--bit-depth',
                        dest='bit_depth',
                        type=int,
                        default=8,
                        help='Bit-depth of data per pixel.'
                        ' One of {}.'.format(allowed_bit_depths)
                        )

    args = parser.parse_args()

    # Check ROI width and height.
    # Print messages and exit if incompatible with camera.
    allowable_width_height = check_input_width_and_height(
        args.roi_width, args.roi_height,
        allowed_roi_widths, max_height
        )

    if allowable_width_height is False:
        sys.exit()

    # Check bit-depth
    if args.bit_depth not in allowed_bit_depths:
        print('\nNope. Bit depth must be one of {}.'
              .format(allowed_bit_depths))
        sys.exit()

    return args


def check_input_width_and_height(
        width_to_set,
        height_to_set,
        allowed_roi_widths=[128, 256, 384, 512, 640,
                            768, 896, 1024, 1152, 1280
                            ],
        max_height=400
        ):
    """Check that width and height settings are ok for the camera.

    Args:
        allowed_roi_widths (list):
            List of ROI widths that do not produce an error.
        max_height (int):
            Maximum ROI height allowed.

    Returns:
        allowable (bool):
            Assessment of whether the width and height settings are allowed.
    """
    allowable = True

    if height_to_set > max_height:
        print('\nNope. Please choose an ROI height <= {} pixels.'
              .format(max_height)
              )
        allowable = False

    if width_to_set not in allowed_roi_widths:
        print('\nNope. Please choose one of these options for ROI width:\n{}'
              .format(allowed_roi_widths)
              )
        allowable = False

    return allowable


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
    # Set exposure time if not present
    if exp_time is None:
        exp_time = round(1e6 / fps - 1)  # For microseconds

    # Exit gracefully if exposure time is >= 1 / frame rate
    elif exp_time > round(1e6 / fps - 1):
        print('\n'
              '*** Please choose an \n'
              'exposure time (us) <= round(1 / frames per second - 1) \n'
              'and start again.'
              )
        sys.exit()

    return exp_time


def set_roi(grabber, x_offset=None, y_offset=None, width=None, height=None):
    """Set the region within the chip to be acquired. Not sure yet
    whether offsets can be set.

    Args:
        grabber (EGrabber object):
            Frame grabber object to set up for acquisition
        x_offset, y_offset (int):
            Pixel location of left and top edges of ROI
        width, height (int):
            Width and height of ROI in pixels
    """
    if width is not None:
        grabber.remote.set('Width', width)
    if height is not None:
        grabber.remote.set('Height', height)


def unscramble_phantom_S710_output(grabber,
                                   roi_width,
                                   bit_depth=8,
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
    # Set up the use two banks - although one bank gives full resolution!
    grabber.remote.set('Banks', banks)  # 2 banks

    # Set up stream to unscramble the middle-outwards reading sequence
    grabber.stream.set('StripeArrangement', 'Geometry_1X_2YM')

    # LineWidth might change with bit-depth
    grabber.stream.set('LineWidth', roi_width)

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
