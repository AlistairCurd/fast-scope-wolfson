"""Image acquisition and display.

Sample script from Euresys modified to unscramble images from Phantom S710."""

from egrabber import *
from ctypes import cast, POINTER, c_ubyte
import cv2
import numpy as np

# Load the GenTL library
gentl = EGenTL()

# Create an EGrabber object
grabber = EGrabber(gentl)

# Create 3 buffers for the grabber
grabber.realloc_buffers(3)

# Start the grabber
grabber.start()

# Capture and display loop
display_zoom = 0.5
while True:
    with Buffer(grabber) as buffer:
        # Get address, width, and height of image in buffer
        ptr = buffer.get_info(BUFFER_INFO_BASE, INFO_DATATYPE_PTR)
        w = buffer.get_info(BUFFER_INFO_WIDTH, INFO_DATATYPE_SIZET)
        h = buffer.get_info(BUFFER_INFO_DELIVERED_IMAGEHEIGHT, INFO_DATATYPE_SIZET)
        # Convert image to BGR format
        bgr = buffer.convert('BGR8')
        # Resize and display the image (using opencv and numpy)
        data = cast(bgr.get_address(), POINTER(c_ubyte * bgr.get_buffer_size())).contents
        img = np.frombuffer(data, count=bgr.get_buffer_size(), dtype=np.uint8).reshape((h,w,3))
        img = cv2.resize(img, (int(w * display_zoom), int(h * display_zoom)))
        cv2.imshow("Press any key to exit", img)
        if cv2.waitKey(1) >= 0:
            break
cv2.destroyAllWindows()
