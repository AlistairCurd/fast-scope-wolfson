"""IO functions"""

import argparse
import cv2
import sys
from pathlib import Path

import numpy as np

from set_grabber_properties import check_input_width_and_height


def get_cmd_inputs(allowed_roi_widths=[128, 256, 384, 512, 640, 768, 896,
                                       1024, 1152, 1280
                                       ],
                   max_height=400,
                   allowed_bit_depths=[8, 12, 16]
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

#    parser.add_argument('-n', '--numframes',
#                        dest='n_frames',
#                        type=int,
#                        default=10,
#                        help='Number of frames to acquire.'
#                        )

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
                        ' One of {}.'
                        .format(allowed_bit_depths)
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

    return output_path


def save_from_queue_multiprocess(savequeue, output_path):
    """Save arrays arriving in a multiprocessing queue.

    Args:
        savequeue (multiprocessing Queue object):
            A queue to query for a data entry of (numpy_images, buffer number),
            where numpy_images is a 2D * time array of images.
            If None appears in the queue, the function will finish,
            otherwise it will keep looping.
        output_path (pathlib Path):
            Directory to save images to.
    """
    finished = False
    while finished is False:
        if not savequeue.empty():
            # print('I\'m here!')
            queued_item = savequeue.get()
            if queued_item is None:
                finished = True
            else:
                # buffer_pointer, buffer_count = queued_item
                numpy_images, buffer_count = queued_item
                # print('Queued shape to save: {}'.format(numpy_images.shape))
                numpy_images.tofile(
                    output_path.joinpath('{}'.format(buffer_count))
                    )


def display_from_queue_multiprocess(displayqueue, instructqueue):
    """Display an image arriving in a multiprocessing queue.

    Args:
        displayqueue (multiprocessing Queue object):
            A queue to query for an image.
            If None appears in the queue, the function will finish,
            otherwise it will keep looping.
        instructqueue(multiprocessing Queue object):
            A queue to send instructions to for how the acquisition proceeds.
    """
    finished = False
    while finished is False:
        if not displayqueue.empty():
            queued_item = displayqueue.get()
            if queued_item is None:
                finished = True
            else:
                image = queued_item
                # print('Queued shape to display: {}'.format(image.shape))
                cv2.imshow('Press \'t\' to terminate,'
                           ' \'s\' to save data,'
                           ' \'p\' for preview mode (no saving).',
                           image
                           )

                # if cv2.waitKey(1) >= 0:
                keypress = cv2.waitKey(1)

                if keypress == ord('t'):
                    instructqueue.put('terminate')
                    print('\nAcquisition terminated.')
                    finished = True
                elif keypress == ord('s'):
                    instructqueue.put('save')
                    print('\nSaving images...')
                elif keypress == ord('p'):
                    instructqueue.put('preview')
                    print('\nIn preview mode, not saving data...')

    # Now finished is true, close display
    cv2.destroyAllWindows()


def display_from_buffer_queue_multiprocess(displayqueue,
                                           instructqueue,
                                           height,
                                           width,
                                           bitdepth):
    """Display an image arriving in a multiprocessing queue.

    Args:
        displayqueue (multiprocessing Queue object):
            A queue to query for an image.
            If None appears in the queue, the function will finish,
            otherwise it will keep looping.
        instructqueue(multiprocessing Queue object):
            A queue to send instructions to for how the acquisition proceeds.
        height (int):
            Height of the image (pixels).
        width (int):
            Width of the image (pixels).
    """
    finished = False
    scale_factor = 1

    if bitdepth == 8:
        image_dtype = np.uint8
    elif bitdepth > 8 and bitdepth <= 16:
        image_dtype = np.uint16
        scale_values_to_8bit = (2 ** 8 - 1) / (2 ** bitdepth - 1)
    else:
        print('Bit depth {} not usable in display process.'
              .format(bitdepth)
              )
        sys.exit()

    while finished is False:
        if not displayqueue.empty():
            queued_item = displayqueue.get()
            if queued_item is None:
                finished = True
            else:
                image_data = np.asarray(queued_item, dtype=image_dtype)
                image_data = image_data.reshape(height, width)
                # Scale pixel values to 8-bit
                if bitdepth != 8:
                    image_data = np.round(
                        image_data * scale_values_to_8bit
                        ).astype(np.uint8)
                # Scale image if zoom instruction received
                if scale_factor == 1:
                    pass
                else:
                    image_data = cv2.resize(image_data, dsize=None,
                                            fx=scale_factor, fy=scale_factor,
                                            interpolation=cv2.INTER_NEAREST
                                            )
                # print('Queued shape to display: {}'.format(image.shape))

                # Dummy image data
                # image_data = np.array([[10, 10], [10, 10]], dtype=np.uint8)

                cv2.imshow('Press \'t\' to terminate,'
                           ' \'s\' to save data,'
                           ' \'p\' for preview mode (no saving).',
                           image_data
                           )

                # if cv2.waitKey(1) >= 0:
                keypress = cv2.pollKey()

                if keypress == -1:  # No keypress
                    pass

                # Acquisition mode instructions
                elif keypress == ord('t'):
                    instructqueue.put('terminate')
                    print('\nAcquisition terminated.')
                    finished = True  # Will leave while loop
                elif keypress == ord('s'):
                    instructqueue.put('save')
                    print('\nSaving images...')
                elif keypress == ord('p'):
                    instructqueue.put('preview')
                    print('\nIn preview mode, not saving data...')

                # Zoom instructions
                elif keypress == ord('+'):
                    scale_factor = scale_factor * 2
                elif keypress == ord('-'):
                    scale_factor = scale_factor / 2

    # Now finished is true, close display
    cv2.destroyAllWindows()


def display_grabber_settings(grabber_settings):
    """Print grabber settings to screen.

    Args:
        grabber_settings (object):
            An object containing the settings to display.
    """
    if hasattr(grabber_settings, 'n_frames'):
        print('\nNumber of frames : {}'.format(grabber_settings.n_frames))
    print('Frames per second : {:.1f}'.format(grabber_settings.fps))
    print('Cycling time : {:.3f}'.format(1e6 / grabber_settings.fps), 'us')
    print('Exposure time :', grabber_settings.exp_time, 'us')
    print('Image width: ', grabber_settings.roi_width)
    print('Image height: ', grabber_settings.roi_height)
    print('Bit depth of pixel: ', grabber_settings.bit_depth)


def display_timings(timestamps, buffer_count, images_per_buffer):
    """Display information about acquisition timings.

    Args:
        timestamps (int):
            Timestamps in microseconds of acquired buffers.
            Should contain at least the timestamps
            of the first and last buffers.
        buffer_count (int):
            The number of buffers acquired in the sequence.
        images_per_buffer (int):
            The number of images acquired per buffer.
    """
    timestamp_range = timestamps[-1] - timestamps[0]
    print('\nTimestamp at buffer 1: {} us'.format(timestamps[0]))
    print('Timestamp at buffer {}: {} us'
          .format(buffer_count, timestamps[-1])
          )
    print('Time between first and last timestamps: {} us'
          .format(timestamp_range)
          )
    # Use buffer_count - 1 as divisor to calculate timings,
    # as we have first and last timestamps, no timestamp before acquiring
    # the first buffer
    print('Time per buffer acquisition: {:.1f} us'
          .format(timestamp_range / (buffer_count - 1))
          )
    print('Acquired {} frames per buffer'.format(images_per_buffer))
    print('Time per frame: {:.3f} us'
          .format(timestamp_range
                  / ((buffer_count - 1) * images_per_buffer)
                  )
          )

    print('Acquired {} frames in total over {:.1f} s.'
          .format(buffer_count * images_per_buffer,
                  timestamp_range * (1 + 1 / (buffer_count - 1)) / 1e6
                  )
          )
