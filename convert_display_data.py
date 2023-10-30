"""Convert grabber data between data types."""


from egrabber import BUFFER_INFO_WIDTH, BUFFER_INFO_HEIGHT, INFO_DATATYPE_SIZET
import ctypes as ct
import numpy as np
import cv2


def mono8_to_ndarray(ptr_address, width, height, size):
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
    data = ct.cast(ptr_address, ct.POINTER(ct.c_ubyte * size)).contents
    numpy_image = np.frombuffer(data,
                                count=size,
                                dtype=np.uint8).reshape((height, width))
    return numpy_image


def get_buffer_properties_as_8bit(buffer):
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
    size = mono8.get_buffer_size()
    return ptr_address, width, height, size


def display_8bit_numpy_opencv(buffer):
    """Convert data to 8-bit and display.

    Args:
        buffer (Buffer object generated with Euresys egrabber.Buffer)

    Returns:
        stop_decision (bool):
            Report on user action to stop display (True means stop)
    """
    buffer_props_8bit = get_buffer_properties_as_8bit(buffer)
    numpy_image = mono8_to_ndarray(*buffer_props_8bit)
    cv2.imshow('Preview', numpy_image)
    stop_decision = cv2.waitKey(1) >= 0
    return stop_decision


def display_8bit_numpy_opencv_from_ptr(ptr, width, height, size):
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
    numpy_image = mono8_to_ndarray(ptr, width, height, size)
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
