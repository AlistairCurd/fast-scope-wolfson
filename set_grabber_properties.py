"""Functions for setting grabber properties
with EGrabber Coaxlink interface"""

import sys
import time

from math import ceil

# import numpy as np

from egrabber import EGenTL, EGrabber
from egrabber import GenTLException


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


def check_exposure(fps, exp_time=None):
    """Check exposure time is compatible with fps,
    or set exposure time close to the limit for the fps setting.

    Exit with a message if the exposure time is too high for the fps.

    Makes sure that exposure time is
    at least 0.5 to 1.5 us less than the buffer cycling period.

    Args:
        fps (float):
            Frame rate (frames per second)
        exp_time (int, default 0):
            Proposed exposure time (microseconds)

    Returns:
        n_frames (int):
            Number of frames to acquire
        fps (float):
            Frame rate (frames per second)
        exp_time (int):
            An allowable exposure time (microseconds). Set close to the frame
            cycling time if none
    """
    # Set exposure time if not present
    if exp_time is None:
        exp_time = 1e6 / fps - 0.45

    # Exit gracefully if exposure time is >= 1 / frame rate
    elif exp_time > 1e6 / fps - 0.45:
        print('\n'
              '*** Please choose an \n'
              'exposure time (us) <= 1e6 / fps - 0.45'
              '\nand start again.'
              )
        sys.exit()
    else:
        pass

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


def unscramble_phantom_S710_output(grabbers,
                                   roi_width,
                                   roi_height,
                                   bit_depth=8,
                                   ):
    """Set grabber remote and stream to produce unscrambled images
    from the Phantom S710 middle-outwards reading sequence.

    May need editing for using all four banks. This is initially written
    to use two banks.

    Args:
        grabbers (list of EGrabber objects,
                  length = number of benks in use):
            List of frame grabber objects to set up for acquisition.
        roi_width (int)
        roi_height (int)
        bit_depth (int)
    """
    # Set up the streams to unscramble the middle-outwards reading sequence
    # and ready to combine appropriately
    for g, grabber in enumerate(grabbers):

        grabber.stream.set('RemoteHeight', roi_height)

        # Unscrambling
        grabber.stream.set('StripeArrangement', 'Geometry_1X_2YM')

        # LineWidth and LinePitch are in bytes.

        # Unpacking: 2 bytes for 12-bit acquisition
        # (like p172 of Coaxlink handbook)
        # grabber.stream.set(
        #    'LineWidth', roi_width * int(np.ceil(bit_depth / 8)))

        # No unpacking:
        grabber.stream.set('LineWidth', roi_width * bit_depth / 8)
        grabber.stream.set('LinePitch', roi_width * bit_depth / 8)

        grabber.stream.set('StripeHeight', 8)
        grabber.stream.set('StripePitch', 8 * len(grabbers))
        grabber.stream.set('BlockHeight', 8)
        grabber.stream.set('StripeOffset', 8 * g)

    # Adding a pause sometimes helps to allow grabber settings to take effect
    time.sleep(0.1)


def create_and_configure_grabbers(grabber_settings):
    """Create Egrabber instance.

    Note that changing the Remote setting for one bank changes
    it for all banks (checked it GenICam Browser).

    Args:
        grabber_settings, has attributes:
            bit_depth, roi_width, roi_height, fps, exp_time
    Returns:
        grabber (Egrabber object)
    """
    # Create and identify grabbers
    gentl = EGenTL()
    grabbers = []
    for device in range(4):  # Upto max number of "cameras"
        try:
            grabbers.append(EGrabber(gentl, 0, device))
        except GenTLException:
            break

    print('\n{} frame-grabbers (camera banks) found.'.format(len(grabbers)))
    # During DEVELOPMENT
    print('Acquiring with only one, at the moment...')

    # "Remote" (camera) settings
    # Set up to use the number of banks connected
    if len(grabbers) == 0:
        print('No camera banks found.\nExiting...\n')
        sys.exit()
    if len(grabbers) == 4:
        grabbers[0].remote.set('Banks', 'Banks_ABCD')  # 4 banks
    elif len(grabbers) == 2:
        grabbers[0].remote.set('Banks', 'Banks_AB')  # 2 banks
    elif len(grabbers) == 1:
        grabbers[0].remote.set('Banks', 'Banks_A')  # 1 banks
    else:
        print('{} camera banks found.').format(len(grabbers))
        print('Not sure this will work.\nExiting...\n')

    # Set up ROI for Remote, taking account of the no. banks in use
    set_roi(grabbers[0],
            width=grabber_settings.roi_width,
            height=grabber_settings.roi_height / len(grabbers)
            )

    # Bit-depth of Remote
    if grabber_settings.bit_depth == 8:
        grabbers[0].remote.set('PixelFormat', 'Mono8')
    if grabber_settings.bit_depth == 12:
        grabbers[0].remote.set('PixelFormat', 'Mono12')

    # Set up streams to contribute correctly to full image
    for grabber in grabbers:

        # To  make use of the banks acquiring separate lines
        grabber.stream.set('ImageFormatSource', 'DataStream')

        # Set bit-depth
        if grabber_settings.bit_depth == 8:
            # grabber.remote.set('PixelFormat', 'Mono8')
            grabber.stream.set('RemotePixelFormat', 'Mono8')
        if grabber_settings.bit_depth == 12:
            # In stream setting, Mono12 is unpacked, Mono12p is packed.
            # Packing may involved using the UnpackingMode setting rather
            # than choosing Mono12p, though.
            grabber.stream.set('RemotePixelFormat', 'Mono12')
            grabber.stream.set('UnpackingMode', 'Off')

    # Unscramble from the grabbers (banks),
    # ready to combine into whole images
    # time.sleep(0.5)  # Allow ImageFormatSource to set
    unscramble_phantom_S710_output(grabbers,
                                   grabber_settings.roi_width,
                                   grabber_settings.roi_height,
                                   bit_depth=grabber_settings.bit_depth
                                   )

    # Configure fps and exposure time
    time.sleep(0.5)  # Allow ROI to set
    grabbers[0].remote.set('AcquisitionFrameRate', grabber_settings.fps)
    # time.sleep(0.25)  # Allow fps to set first
    exp_time_set = False
    while exp_time_set is False:
        try:
            grabbers[0].remote.set('ExposureTime', grabber_settings.exp_time)
            exp_time_set = True
        except GenTLException:
            pass

    return grabbers


def pre_allocate_multipart_buffers(grabber,
                                   images_per_buffer=100,
                                   duration_allocated_buffers=0.1,
                                   verbose=False
                                   ):
    """Pre-allocate buffers rapidly,
    such that there is not a large delay before the first image
    for low frame rates.

    Changes the input number of images per buffer to 1 if
    only one image per multi-part buffer would be needed for the frame rate.

    Args:
        grabber (Egrabber object):
            Frame grabber object to give a buffer allocation
        images_per_buffer (int):
            Number of images for a multipart buffer to contain (can also be 1).
        fps (float):
            Frames per second in the acquisition
        duration_allocated (float):
            The extent in time that the multipart buffer will cover (seconds).
        verbose (Bool):
            Whether to output information on
            the timing of the allocation procedure.

    Returns:
        grabber (Egrabber object):
            Framegrabber now given the pre-allocated buffer.
        images_per_buffer (int):
            Number of images for a multipart buffer to contain.
            Set to 1 if only one multi-part buffer was needed for
            the time extent specified.
    """
    # Try a length of time for allocated buffers to extend over -
    # Need more buffers in the pre-allocation for fast frame rate,
    # but these take too long to allocate for larger fields allowable at
    # lower frame rates
    duration_one_image = \
        1 / grabber.remote.get('AcquisitionFrameRate')  # seconds
    duration_one_buffer = duration_one_image * images_per_buffer
    num_buffers_to_alloc = ceil(duration_allocated_buffers
                                / duration_one_buffer
                                )
    # For slower frame rates, do not use the multi-part buffer,
    # so that an image from the first buffer is displayed sooner
    if num_buffers_to_alloc == 1:
        images_per_buffer = 1
        num_buffers_to_alloc = 100

    # Allocate
    t_alloc_start = time.time()
    grabber.stream.set('BufferPartCount', images_per_buffer)
    grabber.realloc_buffers(num_buffers_to_alloc)
    if verbose:
        print('Buffer allocation took {} s.'
              .format(time.time() - t_alloc_start)
              )

    return grabber, images_per_buffer
