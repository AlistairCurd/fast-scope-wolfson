"""IO functions"""

import argparse
import cv2
import sys

# from math import ceil
from math import floor
from pathlib import Path

import numpy as np

# from convert_display_data import readas16bit_uint12packed_in8bitlist
from set_grabber_properties import check_input_width_and_height


def plural(n):
    """Return 's' if integer input 'n' != 1.
    Return '' otherwise.
    """
    if n != 1:
        return 's'
    else:
        return ''


def get_cmd_inputs(allowed_roi_widths=[128, 256, 384, 512, 640, 768, 896,
                                       1024, 1152, 1280
                                       ],
                   max_height=800,
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

    parser.add_argument('--fps',
                        dest='fps',
                        type=float,
                        default=1000,
                        help='Frame rate (frames per second).'
                        ' The actual FPS will be slightly lower,'
                        ' because of a latency of about 330 ms'
                        ' in the framegrabber.'
                        )

#    parser.add_argument('-x', '--exposure',
#                        dest='exp_time',
#                        type=int,
#                        help='Exposure time (microseconds).'
#                        ' Must be an integer <= floor(1e6 / fps - 0.001).'
#                        ' Set to this by default.'
#                        )

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

    parser.add_argument('-t', '--trigger-level',
                        dest='trigger_level',
                        type=int,
                        default=0,
                        help='Pixel level at which to trigger saving.'
                        )

    parser.add_argument('-l', '--seq-length',
                        dest='seq_length',
                        type=int,
                        default=1e15,
                        help='Maximum sequence length to save (frames), '
                        'for use with triggered sequences.'
                        )

    parser.add_argument('--buffer-time',
                        dest='max_buffer_timing_ms',
                        type=float,
                        default=2.5,
                        help='Maximum duration (ms) for the multipart buffer.'
                        ' Larger numbers help with frame rate, smaller numbers'
                        ' provide a shorter time between'
                        ' trigger and acquisition, for when that is important.'
                        ' The actual buffer timings may be slightly higher,'
                        ' because a latency in the frame grabber means that'
                        ' the frames are slightly longer in reality'
                        ' that the timings set by the user.'
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

    # Display actual sequence length (whole number of buffers),
    # and check at least two buffers will be saved,
    # to include one additional buffer after the intensity trigger
    frame_time_ms = 1 / args.fps * 1000
    seq_length_ms = frame_time_ms * args.seq_length
    # num_buffers = ceil(seq_length_ms / args.max_buffer_timing_ms)
    # print('\nRequested {:d} frames = {:.5f} ms'
    #      ' <= {:d} whole buffer{} ({:.5f} ms)'
    #      .format(args.seq_length, seq_length_ms,
    #              num_buffers, plural(num_buffers),
    #              num_buffers * args.max_buffer_timing_ms)
    #      )

    if seq_length_ms > args.max_buffer_timing_ms:
        # args.seq_length = int(round(args.max_buffer_timing_ms
        #                            / frame_time_ms * num_buffers)
        #                      )
        # print('Will acquire whole number of buffers:'
        #      ' {:d} frames.'.format(args.seq_length)
        #      )
        print('\nActual saved sequence will be a whole number of'
              ' multipart buffers:')
        print('a multiple of {:d} frames'
              ' at this FPS and buffer timing.'
              .format(int(round(args.max_buffer_timing_ms / frame_time_ms)))
              )

    else:  # Make sure that at least two multipart buffers are acquired.
        print('\nRequested sequence length is less than one multipart buffer'
              ' at this buffer timing ({} ms).'.format(
                  args.max_buffer_timing_ms)
              )
        # Set new seq_length if neccesary
        args.seq_length = \
            int(round(args.max_buffer_timing_ms * 2 / frame_time_ms))
        print('Increasing sequence length to two whole buffers ='
              ' {:d} frames'.format(args.seq_length)
              )

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
        image_data_dtype = np.uint8
    elif bitdepth == 12:
        # image_data_dtype = np.uint8  # Packed
        image_data_dtype = np.uint16  # Unpacked

    else:
        print('Bit depth {} not usable in display process.'
              .format(bitdepth)
              )
        sys.exit()

    scale_values_to_8bit = (2 ** 8 - 1) / (2 ** bitdepth - 1)

    while finished is False:
        if not displayqueue.empty():
            queued_item = displayqueue.get()
            if queued_item is None:
                finished = True
            else:
                image_data = np.asarray(queued_item, dtype=image_data_dtype)
                # Read 12-bit pixel values (scaled to 8-bit)
                if bitdepth == 12:
                    # For packed:
                    # image_data = \
                    #    readas16bit_uint12packed_in8bitlist(image_data)
                    # Scale values to 8-bit
                    image_data = np.round(
                        image_data * scale_values_to_8bit
                        ).astype(np.uint8)
                image_data = image_data.reshape(height, width)

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
                    finished = True  # Will leave while loop
                elif keypress == ord('s'):
                    instructqueue.put('save')
                    print('\nSaving enabled...')
                elif keypress == ord('p'):
                    instructqueue.put('preview')

                # Zoom instructions
                elif keypress == ord('+'):
                    scale_factor = scale_factor * 2
                elif keypress == ord('-'):
                    scale_factor = scale_factor / 2

    # Now finished is true, close display
    cv2.destroyAllWindows()


def display_grabber_settings(grabber_settings, egrabber):
    """Print grabber settings to screen.

    Args:
        grabber_settings (object):
            An object containing the settings to display.
        egrabber (EGrabber):
            An egrabber initialised for one bank of the camera.
    """
    print('Frames per second : {:.1f}'.format(grabber_settings.fps))
    print('Cycling time : {:.3f}'.format(1e6 / grabber_settings.fps), 'us')
    print('Exposure time :', egrabber.remote.get('ExposureTime'), 'us')
    print('Image width: ', grabber_settings.roi_width)
    print('Image height: ', grabber_settings.roi_height)
    print('Bit depth of pixel: ', grabber_settings.bit_depth)


def do_instruction(save_instruction,
                   images_per_buffer,
                   timestamps, buffer_count,
                   output_file,
                   output_filename, output_path, output_number,
                   enable_saving,
                   triggered,
                   acquire
                   ):
    """Check for user input and respond.
    """
    if save_instruction == 'save':
        if not enable_saving:
            enable_saving = True
            triggered = False

    elif save_instruction == 'preview':
        # If saving had been in progress,
        # there will be an entry in timestamps[]
        # Include the last timestamp and display timings
        if not output_file.closed:
            output_file.close()

        # Display timings and add to filename
        if len(timestamps) == 2:
            average_frame_time = display_timings(timestamps,
                                                 buffer_count,
                                                 images_per_buffer
                                                 )

            final_filename = add_to_filename(
                output_filename,
                buffer_count * images_per_buffer,
                average_frame_time
                )

            output_path.rename(
                output_path.parent / final_filename)

            output_number = output_number + 1

        print('\nIn preview mode, not saving data...')

        enable_saving = False
        triggered = False

    elif save_instruction == 'terminate':
        # If saving had been in progress,
        # there will be an entry in timestamps[]
        # Include the last timestamp and display timings
        if not output_file.closed:
            output_file.close()

        # Display timings and add to filename
        if len(timestamps) == 2:
            average_frame_time = display_timings(timestamps,
                                                 buffer_count,
                                                 images_per_buffer
                                                 )

            final_filename = add_to_filename(
                output_filename,
                buffer_count * images_per_buffer,
                average_frame_time
                )

            output_path.rename(
                output_path.parent / final_filename)

        print('\nAcquisition terminated.')

        enable_saving = False
        acquire = False

    return enable_saving, triggered, acquire, buffer_count, output_number


def display_timings(timestamps, buffer_count, images_per_buffer):
    """Display information about acquisition timings.

    This printing to screen does not seem to slow down the frames.

    Args:
        timestamps (list):
            Timestamps in microseconds of the first and last buffers
            in an acquisition.
        buffer_count (int):
            The number of buffers acquired in the sequence.
        images_per_buffer (int):
            The number of images acquired per buffer.

    Returns:
        average_frame_time (float or str):
            If more than one buffer in sequence:
                average measured frame cycling time, from buffer timestamps.
            If only one buffer in sequence:
                'NoTiming'
    """
    timestamp_range = timestamps[1] - timestamps[0]

    if buffer_count > 1:
        # print('\nTimestamp at buffer 1: {} us'.format(timestamps[0]))
        # print('Timestamp at buffer {}: {} us'
        #      .format(buffer_count, timestamps[-1])
        #      )
        # print('Time between first and last timestamps: {} us'
        #      .format(timestamp_range)
        #      )

        # Use buffer_count - 1 as divisor to estimate timings,
        # as we have first and last timestamps, no timestamp before acquiring
        # the first buffer
        print('\nData saved.')
        print('{} frames over {:.3f} s'
              .format(buffer_count * images_per_buffer,
                      timestamp_range * (1 + 1 / (buffer_count - 1)) / 1e6
                      )
              )
        # in us
        average_frame_time = \
            timestamp_range / ((buffer_count - 1) * images_per_buffer)
        print('Time per frame: {:.3f} us'
              .format(average_frame_time))
        # per s
        print('FPS: {:.1f}'.format(1 / (average_frame_time / 1e6)))
        print('Time per buffer acquisition: {:.1f} us ({:d} frames)'
              .format(timestamp_range / (buffer_count - 1),
                      images_per_buffer
                      )
              )
        # print('Acquired {} frames per buffer'.format(images_per_buffer))

    elif buffer_count == 1:
        print('\nOnly one buffer obtained, containing {} frames.'
              .format(images_per_buffer)
              )
        print('\nNo information available on acquisition rate.')
        average_frame_time = 'NoTiming'

    return average_frame_time


def add_to_filename(filename, number_of_images, frame_time):
    """Add useful information to an acquisition filename.

    Args:
        filename (str):
            The filename to lengthen.
        number_of_images (int):
            Number of frames in the acquisition sequence.
        frame_time (float):
            Frame cycling time in the acquisition sequence.

    Returns:
        longer_filename (str):
            The new filename with number of frames and frame cycling time
            appended. Frame time is included as e.g. 11p440 for 11.440 us.
    """
    frame_time_str = '{:d}p{:03d}'.format(
        floor(frame_time),
        round((frame_time - floor(frame_time)) * 1000)
        )
    longer_filename = '{}{}images_frames{}us'.format(
        filename, number_of_images, frame_time_str)
    return longer_filename
