"""IO functions"""

import argparse
import cv2
import sys
# import time
from pathlib import Path

import h5py

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


def store_hdf5(begin_filling_queue,
               input_queue,
               sequence_shape,
               images_per_buffer,
               output_path,
               counter_queue):
    """Make an HDF5 file and populate the dataset.
    Designed to be used by overlapping parallel processes.

    One process will receive a counter,
    then make a counter available to other processes.

    Each process will create an HDF5 file ready to store numpy image arrays.
    The processes will wait to receive a signal to receive data from
    an input queue.

    When a process receives this signal, it will fill up the dataset for the
    HDF5 file with images from multipart buffers.
    When finished, it will send a signal to another process to start
    receiving images, and write the data to disk.

    Args:
        being_filling_queue (multiprocessing Queue):
            Queue where a signal to begin filling and
            information for the filename can arrive.
            Prevents jumbling data up in different prarallel processes.
        input_queue (multiprocessing Queue):
            Queue where data to store arrives.
        sequence_shape (tuple, int):
            Shape (n_frames, height, width) of the image sequence to store.
        images_per_buffer (int):
            Number of images arriving per buffer.
        output_path (pathlib Path):
            Directory to save images to.
        counter_queue (multiprocessing Queue):
            Queue where a counter to include in the filename or
            an instruction to stop arrives.
    """
    all_finished = False
    sequence_length = list(sequence_shape[0])
    max_buffers_per_file = sequence_length / images_per_buffer
    while not all_finished:

        # Receive counter for filename or stop signal
        counter = None
        while counter is None:
            if not counter_queue.empty():
                counter = counter_queue.get()
                if counter == 'stop':
                    all_finished = True
        # Go to the end of the function is stop signal received
        if all_finished is True:
            continue

        # Now we have the counter,
        # create file in advance (ideally) of receiving data
        with h5py.File(output_path.join(counter), 'w') as outfile:
            dataset = outfile.create_dataset(
                "images", shape=sequence_shape, dtype='i8'
                 )
        # Also pass an incremented counter to
        # another parallel process using this function
        counter = counter + 1
        counter_queue.put(counter)

        # Wait for the signal to receive data, and
        # Fill dataset until stop condition
        file_finished = False
        buffers_so_far = 0
        while not file_finished and buffers_so_far < max_buffers_per_file:
            if not begin_filling_queue.empty():
                # Get instruction to fill the dataset out of the queue,
                # so that a parallel call to this function waits
                # for a later instruction
                begin_filling_queue.get()
                # Fill the dataset up! (Or finish if instructed)
                queued_data = input_queue.get()
                if queued_data == 'endfile':
                    file_finished = True
                else:
                    dataset[buffers_so_far * images_per_buffer:
                            (buffers_so_far + 1) * images_per_buffer,
                            :,
                            :
                            ]
                    buffers_so_far = buffers_so_far + 1

        # Tell a parallel call to this function
        # that it can start filling its dataset
        begin_filling_queue.put('go')

        # Write data to disk
        outfile.close()


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
