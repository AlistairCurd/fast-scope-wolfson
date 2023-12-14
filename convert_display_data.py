"""Convert grabber data between data types."""

import ctypes as ct
# import sys

import cv2
import numpy as np

from egrabber import BUFFER_INFO_WIDTH, BUFFER_INFO_HEIGHT, INFO_DATATYPE_SIZET


def mono8_to_ndarray(ptr_address, width, height, images_per_buffer=1):
    """Convert 8-bit buffer data to a 2D numpy array.

    Args:
        ptr_address:
            Location of the buffer data in memory.
        width (int):
            Width of the image.
        height (int):
            Height of the image.
        size (int):
            Number of pixels in the image (items in the buffer).
    Returns:
        numpy_image (2D numpy array, uint8):
            2D image data.
    """
    image_sequence_size = width * height * images_per_buffer
    data = ct.cast(ptr_address,
                   ct.POINTER(ct.c_ubyte * image_sequence_size)
                   ).contents
    numpy_images = np.frombuffer(data,
                                 count=image_sequence_size,
                                 dtype=np.uint8).reshape((images_per_buffer,
                                                          height,
                                                          width
                                                          ))
    return numpy_images


def get_buffer_properties_image_as_8bit(buffer):
    """Get buffer properties for accessing and using the data in it,
    with data converted to 8-bit.

    Args:
        buffer (Buffer object generated with Euresys egrabber.Buffer)

    Returns:
        ptr_address:
            Location in memory to find the buffer,
            after conversion to 8-bit data
        width (int):
            Width of the acquired field in pixels
        height (int):
            Height of the acquired field in pixels
        size (int):
            Total number of pixels acquired in the field
    """
    width = buffer.get_info(BUFFER_INFO_WIDTH, INFO_DATATYPE_SIZET)
    height = buffer.get_info(BUFFER_INFO_HEIGHT, INFO_DATATYPE_SIZET)
    # Redundant for 8-bit?, but makes other pixel formats work
    mono8 = buffer.convert('Mono8')
    ptr_address = mono8.get_address()
    return ptr_address, width, height


def display_8bit_numpy_opencv(buffer):
    """Convert data to 8-bit and display.

    Args:
        buffer (Buffer object generated with Euresys egrabber.Buffer)

    Returns:
        stop_decision (bool):
            Report on user action to stop display (True means stop)
    """
    buffer_props_8bit = get_buffer_properties_image_as_8bit(buffer)
    numpy_image = mono8_to_ndarray(*buffer_props_8bit)
    cv2.imshow('Preview', numpy_image)
    stop_decision = cv2.waitKey(1) >= 0
    return stop_decision


def display_8bit_numpy_opencv_from_ptr(ptr, width, height):
    """Convert data to 8-bit and display.

    Args:
        ptr:
            Location of the data in memory.
        width (int):
            Width of the image.
        height (int):
            Height of the image.
        size (int):
            Number of pixels in the image (items in the buffer).

    Returns:
        stop_decision (bool):
            Report on user action to stop display (True means stop)
    """
    # buffer_props_8bit = get_buffer_properties_as_8bit(buffer)
    numpy_image = mono8_to_ndarray(ptr, width, height)
    cv2.imshow('Preview', numpy_image)
    stop_decision = cv2.waitKey(1) >= 0
    return stop_decision


def display_opencv(numpy_image):
    """Display the numpy image.

    Args:
        numpy_image:
            Numpy array displayable by opencv

    Returns:
        stop_decision (bool):
            Report on user action to stop display (True means stop)
    """
    cv2.imshow('Preview', numpy_image)
    stop_decision = cv2.waitKey(1) >= 0
    return stop_decision


def build_image_stack_from_queue(inputqueue, outputqueue, save_signal_queue):
    """Build an image stack from a series of smaller stacks
    and pass to a queue, when a maximum size (~2GB) is reached,
    or a signal is received.

    Args:
        inputqueue (multiprocessing Queue):
            Queue where arrays arrive to be stacked.
        outputqueue (multiprocessing Queue):
            Queue to send output image stacks to.
        save_signal_queue (multiprocessing Queue):
            Queue for inst
    """
    finished = False
    array_stack = None
    stack_counter = 0
    while finished is False:
        # Start image stack with first chunk or end loop
        while array_stack is None:
            if not inputqueue.empty():
                queued_item = inputqueue.get()
                # Stop if signalled to stop
                if queued_item is None:
                    finished = True
                    outputqueue.put(None)
                    break
                # Or create stack
                else:
                    array_stack, buffer_number = queued_item
        # Don't bother with appending if the acquisition is finished
        if finished:
            break
        # Append successive chunks or end loop
        if not inputqueue.empty():
            queued_item = inputqueue.get()
            # End and send stack to save process
            # if stop signal received here
            if queued_item is None:
                finished = True
                outputqueue.put([array_stack, stack_counter])
                outputqueue.put(None)
            # Otherwise append frames to stack
            else:
                array_chunk, buffer_number = queued_item
                array_stack = np.append(array_stack, array_chunk, axis=0)
                # Save if past size threshold (number of elements) for saving
                if array_stack.size > 2 * 10**6:
                    # print(array_stack.shape, ',', stack_counter)
                    outputqueue.put([array_stack, stack_counter])
                    array_stack = None
                    stack_counter = stack_counter + 1

        # Save stack if signal for end of sequence arrives
        # if not save_signal_queue.empty() and array_stack is not None:
        #    signal = save_signal_queue.get()
        #    if signal == 'save_now':
        #        outputqueue.put(array_stack, stack_counter)
        #        array_stack = None
        #        stack_counter = stack_counter + 1


def readas16bit_uint12packed_in8bitlist(data_in):
    """Read packed 12-bit uint data that was stored in
    8-bit format to save file size/time. So two 12-bit values to recover
    are contained in three consecutive 8-bit values.

    Convert these 12-bit values to 8-bit for display.

    See https://stackoverflow.com/a/51967333/23094281 answer by
    https://stackoverflow.com/users/6234574/cyrilgaudefroy

    Args:
        data_in (list of 8-bit values)

    Returns:
        1D numpy array of 8-bit values, which are the 8 most significant
        bits if the 12-bit values
    """
    # Convert to one row of array per three bytes, as 16-bit:
    data_in = np.reshape(data_in, (len(data_in) // 3, 3)).astype(np.uint16)

    # Now vectors of first, second and third bytes in each set of three
    first_byte, second_byte, third_byte = data_in.T

    # Shift bits around into 12-bit values as read as desired bitdepth
    # Use 8 most significant bits to read as 8-bit for display

    # first_uint12_as8bit = first_byte
    # full 12-bit v:
    first_uint12 = (first_byte << 4) + (second_byte >> 4)

    # second_uint12_as8bit = ((second_byte % 16) << 4) + (third_byte >> 4)
    # full 12-bit v:
    second_uint12 = ((second_byte % 16) << 8) + third_byte

    # Put first and second 12-bit values in a pair
    reordered_values = np.vstack((first_uint12, second_uint12)).T

    # Return 1D list
    return reordered_values.reshape(reordered_values.size)
