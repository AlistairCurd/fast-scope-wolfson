"""Find the frame rates allowed at a given resolution."""

from egrabber import EGenTL, EGrabber, errors
import numpy as np
import time
# import sys
import set_grabber_properties


def fps_test(grabber, fps_min_test=1, fps_max_test=10000, fps_step=1):

    # Flags to control test output
    fps_min_allowed = None
    fps_max_allowed = None

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
        for fps in np.arange(fps_min_allowed + fps_step,
                             fps_max_test + fps_step,
                             fps_step
                             ):
            # print('FPS : {:f}'.format(fps))
            # From one step after the minimum allowed fps setting upwards,
            # if the fps setting cannot be applied...
            try:
                # Allow time to change setting
                time.sleep(0.002)
                grabber.remote.set('AcquisitionFrameRate', float(fps))
            except errors.GenTLException:
                # ... record the previous attempt
                # as the maximum allowed and stop
                fps_max_allowed = fps - fps_step
                break

    # If highest fps tested was allowable, set this as the
    # maximum allowable setting
    if fps == fps_max_test:
        fps_max_allowed = fps_max_test

    # PRINT RESULTS if extrema found
    if fps_min_allowed is not None:
        print('\nMinimum allowable FPS setting found : {}.'
              .format(fps_min_allowed)
              )
    if fps_max_allowed is not None:
        print('\nMaximum allowable FPS setting found : {}.'
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
    if fps_min_allowed is not None and fps_max_allowed is None:
        print('\nWarning: Maximum allowable fps setting found '
              'was the highest tested. Higher fps settings may be allowable.'
              )


def main():
    """Test frame rates for whether they produce an error.
    Output minimum and maximum allowed frame rates.

    Args:
        self (EGrabber object):
            Frame grabber object for acquisition.
        fps_min_test (float):
            Minimum frame rate to test.
        fps_max_test (float):
            Maximum frame rate to test.
        fps_step (float):
            Steps between the test fps settings.
    """
    # Get user settings
    user_settings = set_grabber_properties.get_cmd_inputs()
    roi_width = user_settings.roi_width
    roi_height = user_settings.roi_height

    # Create grabber
    gentl = EGenTL()
    grabber = EGrabber(gentl)

    # Set up ROI
    set_grabber_properties.set_roi(grabber, width=roi_width, height=roi_height)

    # Set up grabber stream for unscrambled images
    set_grabber_properties.unscramble_phantom_S710_output(grabber, roi_width)

    # Test allowed frame rates
    fps_test(grabber, fps_min_test=1, fps_max_test=100000, fps_step=1)


if __name__ == '__main__':
    main()
