"""Find the frame rates allowed at a given resolution."""

from egrabber import EGenTL, EGrabber, errors
import sys
import numpy as np
import set_grabber_properties


def fps_test(grabber, fps_min_test=1, fps_max_test=10000, fps_step=1):
    """Test frame rates for whether they produce an error.
    Output minimum and maximum allowed frame rates.
    
    Args:
        grabber (EGrabber object):
            Frame grabber object for acquisition.
        fps_min_test (float):
            Minimum frame rate to test.
        fps_max_test (float):
            Maximum frames rate to test.
        fps_step (float):
            Steps between the test fps settings.
    """
    fps_min_allowed = 1

    arrived_at_min_fps = False
    arrived_at_max_fps = False

    for fps in np.arange(fps_min_test, fps_max_test, fps_step):
        while arrived_at_min_fps is False:
            try:
                grabber.remote.set('AquisitionFrameRate', fps)
            except errors.GenTLException:
                continue
            arrived_at_min_fps = True


def main():
    # Get user settings
    user_settings = set_grabber_properties.get_cmd_inputs()
    fps = user_settings.fps
    exp_time = user_settings.exp_time

    # Make sure exposure time is less than cycling time
    # Set if not given
    exp_time = set_grabber_properties.check_and_set_exposure(fps, exp_time)

    # Create grabber
    gentl = EGenTL()
    grabber = EGrabber(gentl)
