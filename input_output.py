"""IO functions"""

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


def save_from_queue_multiprocess(savequeue):
    """Look for data to save from a multiprocessing queue.

    Args:
        savequeue (multiprocessing Queue object):
            A queue to query for data entries.
            If 'stop' is found, the function will finish,
            otherwise it will keep looping.
    """
    while True:
        if not savequeue.empty():
            queued_item = savequeue.get()
            if queued_item == 'stop':
                break
            else:
                pass


def display_grabber_settings(grabber_settings):
    """Print grabber settings to screen.

    Args:
        grabber_settings (object):
            An object containing the settings to display.
    """
    print('\nNumber of frames : {}'.format(grabber_settings.n_frames))
    print('Frames per second : {:.1f}'.format(grabber_settings.fps))
    print('Cycling time : {:.1f}'.format(1e6 / grabber_settings.fps), 'us')
    print('Exposure time :', grabber_settings, 'us')
    print('Image width: ', grabber_settings.roi_width)
    print('Image height: ', grabber_settings.roi_height)
    print('Bit depth of pixel: ', grabber_settings.bit_depth)
