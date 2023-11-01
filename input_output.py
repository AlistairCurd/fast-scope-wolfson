"""IO functions"""

import cv2
# import numpy as np
from pathlib import Path


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
                # print(numpy_image[10, 10, 10])
                numpy_images.tofile(
                    output_path.joinpath('{}'.format(buffer_count))
                    )


def display_from_queue_multiprocess(displayqueue):
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
                cv2.imshow(text, image)
                if cv2.waitKey(1) >= 0:
                    finished = True


def display_grabber_settings(grabber_settings):
    """Print grabber settings to screen.

    Args:
        grabber_settings (object):
            An object containing the settings to display.
    """
    print('\nNumber of frames : {}'.format(grabber_settings.n_frames))
    print('Frames per second : {:.1f}'.format(grabber_settings.fps))
    print('Cycling time : {:.1f}'.format(1e6 / grabber_settings.fps), 'us')
    print('Exposure time :', grabber_settings.exp_time, 'us')
    print('Image width: ', grabber_settings.roi_width)
    print('Image height: ', grabber_settings.roi_height)
    print('Bit depth of pixel: ', grabber_settings.bit_depth)
