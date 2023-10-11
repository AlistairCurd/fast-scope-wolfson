# fast-scope-wolfson
Software for running fast microscope system in Wolfson Imaging Facility, University of Leeds.

## Built With
* Python 3.10 on Windows 11
* Euresys eGrabber API for Coaxlink cards

## Getting started
* Set up a Python 3 environment (only 3.10 tested).
* Install the eGrabber Python bindings wheel from Euresys.
* Install opencv, pillow
* Clone this repository and navigate to it.
* Test with the sample eGrabber scripts from Euresys (`python <script_name>`).

## Code

* *acquire-number-rate-exposure* : A script to acquire and save unscrambled images from the Phantom S710 with user-chosen number of frames, frame rate and exposure time over an ROI.
* *live-numpy-opencv-unscramble.py* : A script to acquire and display unscrambled images from the Phantom S710 chip-reading pattern (two banks in use).
* *set_grabber_properties.py* : A library with functions for setting properties of the framegrabber.

### camera_tests
* *find_allowed_roi_widths.py* : A script to discover the allowed widths of the ROI for aqcuisition.
* *find_allowed_timings.py* : A script to discover the minimum and maximum frame rates that can be set.

## Files included
* *allowed_roi_widths.txt* : The allowed widths of the acquisition region for the Phantom S710.

## Contact
Alistair Curd - a.curd@leeds.ac.uk





