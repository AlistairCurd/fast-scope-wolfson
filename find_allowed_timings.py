"""Find the frame rates allowed at a given resolution."""

from egrabber import EGenTL, EGrabber, errors
import argparse
import numpy as np
import time
import sys
import set_grabber_properties


def fps_test(grabber, fps_min_test=1, fps_max_test=10000, fps_step=1):

    # Flags to control test output
    fps_min_allowed = None
    fps_max_allowed = None
    tested_beyond_max_test = False

    # Test fps settings for a minimum fps allowed
    for fps in np.arange(fps_min_test,
                         fps_max_test + fps_step,
                         fps_step
                         ):
        # print('FPS : {:f}'.format(fps))

        # From the lowest fps setting upwards,
        # if the fps setting can be applied...
        try:
            # Allow time to change setting
            time.sleep(0.002)
            grabber.remote.set('AcquisitionFrameRate', float(fps))
        except errors.GenTLException:
            continue
        # ... record it as the minimum allowed and stop
        fps_min_allowed = fps
        break

    # Test fps settings for a maximum fps allowed,
    # if a minimum allowed setting was reached
    if fps_min_allowed is not None:

        fps_max_allowed = fps_min_allowed

        # From one step after the minimum allowed fps setting upwards...
        for fps in np.arange(fps_min_allowed + fps_step,
                             fps_max_test + fps_step,
                             fps_step
                             ):
            # ...if the fps setting can be applied, update the max allowed fps
            try:
                # Allow time to change setting
                time.sleep(0.002)
                grabber.remote.set('AcquisitionFrameRate', float(fps))
            # otherwise stop the loop and mark that this has happened
            except errors.GenTLException:
                tested_beyond_max_test = True
                break

            fps_max_allowed = fps

    # PRINT RESULTS if extrema found
    if fps_min_allowed is not None:
        print('\nMinimum allowable FPS setting found: {}'
              .format(fps_min_allowed)
              )
    if fps_max_allowed is not None:
        print('Maximum allowable FPS setting found: {}'
              .format(fps_max_allowed)
              )

    # OUTPUT WARNINGS if min and max allowed were outside
    # the min and max of the test range.
    if fps_min_allowed is None:
        print('\nWarning: No allowable fps setting found '
              'within these settings. '
              'Reducing the minimum fps tested may help.'
              )
    if fps_min_allowed == fps_min_test:
        print('\nWarning: Minimum allowable fps setting found '
              'was the lowest tested. Lower fps settings may be allowable.'
              )
    if fps_min_allowed is not None and tested_beyond_max_test is False:
        print('\nWarning: Maximum allowable fps setting found '
              'was the highest tested. Higher fps settings may be allowable.'
              )


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
        description="Test for minimum and maximum frame rates"
        " at chosen ROI dimensions.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
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
                        help='Optional. Height of ROI in pixels.'
                        ' Must be <= {}.'.format(max_height)
                        )

    parser.add_argument('-b,', '--bit-depth',
                        dest='bit_depth',
                        type=int,
                        default=8,
                        help='Bit-depth of data per pixel.'
                        ' One of {}.'.format(allowed_bit_depths)
                        )

    parser.add_argument('--min-fps',
                        dest='fps_min_test',
                        type=float,
                        default=1.,
                        help='Minimum frame rate to test (frames per second).'
                        )

    parser.add_argument('--max-fps',
                        dest='fps_max_test',
                        type=float,
                        default=100000.,
                        help='Minimum frame rate to test (frames per second).'
                        )

    parser.add_argument('--step-fps',
                        dest='fps_step',
                        type=float,
                        default=1,
                        help='Increment to frame rate during test'
                        ' (frames per second).'
                        )

    args = parser.parse_args()

    # Check ROI width and height.
    # Print messages and exit if incompatible with camera.
    allowable_width_height = \
        set_grabber_properties.check_input_width_and_height(
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


def main():
    """Test eGrabber frame rates for whether they produce an error.
    Output minimum and maximum allowed frame rates.
    """
    # Get user settings
    cmd_args = get_cmd_inputs()

    # Display settings
    print('')
    print('Image width: ', cmd_args.roi_width)
    print('Image height: ', cmd_args.roi_height)
    print('Bit depth of pixel: ', cmd_args.bit_depth)
    print('Minimum FPS to test: ', cmd_args.fps_min_test)
    print('Maximum FPS to test: ', cmd_args.fps_max_test)
    print('FPS increment for test: ', cmd_args.fps_step)

    # Create grabber
    gentl = EGenTL()
    grabber = EGrabber(gentl)

    # Set up ROI
    set_grabber_properties.set_roi(grabber,
                                   width=cmd_args.roi_width,
                                   height=cmd_args.roi_height
                                   )

    # Set bit-depth
    if cmd_args.bit_depth == 8:
        grabber.remote.set('PixelFormat', 'Mono8')
    if cmd_args.bit_depth == 12:
        grabber.remote.set('PixelFormat', 'Mono12')

    # Set up grabber stream for unscrambled images
    set_grabber_properties.unscramble_phantom_S710_output(
        grabber, cmd_args.roi_width, bit_depth=cmd_args.bit_depth
        )

    # Test allowed frame rates
    fps_test(grabber,
             fps_min_test=cmd_args.fps_min_test,
             fps_max_test=cmd_args.fps_max_test,
             fps_step=cmd_args.fps_step)


if __name__ == '__main__':
    main()
