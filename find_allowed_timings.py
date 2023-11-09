"""Find the frame rates allowed at a given resolution."""

from egrabber import EGenTL, EGrabber, errors
import numpy as np
import time

import set_grabber_properties
from input_output import get_cmd_inputs


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
