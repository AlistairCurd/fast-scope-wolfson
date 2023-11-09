"""IO functions"""

import argparse
import cv2
import sys
from pathlib import Path

from set_grabber_properties import check_input_width_and_height


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
    """
    finished = False
    while finished is False:
        if not savequeue.empty():
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
    """
    finished = False
    while finished is False:
        if not displayqueue.empty():
            queued_item = displayqueue.get()
            if queued_item is None:
                finished = True
            else:
                image, text = queued_item
                # print('Queued shape to display: {}'.format(image.shape))
                cv2.imshow('Press \'t\' to terminate,'
                           ' \'s\' to save data,'
                           ' \'p\' for preview mode (no saving).',
                           image
                           )

                # if cv2.waitKey(1) >= 0:
                keypress = cv2.waitKey(1)

                if keypress == ord('t'):
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


def display_grabber_settings(grabber_settings):
    """Print grabber settings to screen.

    Args:
        grabber_settings (object):
            An object containing the settings to display.
    """
    print('\nNumber of frames : {}'.format(grabber_settings.n_frames))
    print('Frames per second : {:.1f}'.format(grabber_settings.fps))
    print('Cycling time : {:.3f}'.format(1e6 / grabber_settings.fps), 'us')
    print('Exposure time :', grabber_settings.exp_time, 'us')
    print('Image width: ', grabber_settings.roi_width)
    print('Image height: ', grabber_settings.roi_height)
    print('Bit depth of pixel: ', grabber_settings.bit_depth)
