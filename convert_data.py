"""Convert grabber data between data types."""


from egrabber import BUFFER_INFO_WIDTH, BUFFER_INFO_HEIGHT, INFO_DATATYPE_SIZET
import ctypes as ct
import numpy as np


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
    width = buffer.get_info(BUFFER_INFO_WIDTH, INFO_DATATYPE_SIZET)
    height = buffer.get_info(BUFFER_INFO_HEIGHT, INFO_DATATYPE_SIZET)
    # Redundant for 8-bit?, but makes other pixel formats work
    mono8 = buffer.convert('Mono8')
    ptr_address = mono8.get_address()
    size = mono8.get_buffer_size()
    return ptr_address, width, height, size
