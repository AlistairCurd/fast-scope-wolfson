"""Find the frame rates allowed at a given resolution."""

from egrabber import EGenTL, EGrabber, errors
import argparse
import sys


# Create grabber
gentl = EGenTL()
grabber = EGrabber(gentl)

print('\nGrabber created.')


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
                        default=10,
                        help='Required. Number of frames to acquire.'
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
