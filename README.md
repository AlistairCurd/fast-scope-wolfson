# fast-scope-wolfson
Software for running fast microscope system in Wolfson Imaging Facility, University of Leeds.

## Built With
* Python 3.10 on Windows 11
* Euresys eGrabber API for Coaxlink cards
* Phantom S710 camera

## Getting started

* Set up a new Python 3 environment (only 3.10 tested).
* Install the eGrabber Python bindings wheel from Euresys.
* Install opencv, pillow
* Test with the sample eGrabber Python scripts from Euresys
  * Download the eGrabber sample programs
  * Navigate to the the eGrabber Python sample programs in a command prompt
  * Run a couple of them: `python <script_name>`
* Navigate to this repository
* Check options with `python runcam.py -h`
* Run `python runcam.py` with desired options.

## Code

* *runcam.py* : A script to acquire and save unscrambled images from the Phantom S710 with user-chosen number of frames, frame rate and exposure time over an ROI.
* *set_grabber_properties.py* : A library with functions for setting properties of the framegrabber.

### camera_tests
* *find_allowed_roi_widths.py* : A script to discover the allowed widths of the ROI for aqcuisition.
* *find_allowed_timings.py* : A script to discover the minimum and maximum frame rates that can be set.

## Files included
* *camera_settings_info/allowed_roi_widths.txt* : The allowed widths of the acquisition region for the Phantom S710.
* *camera_settings_info/allowed_frame_rates.txt* : The minimum and maximum allowed frame rates with different ROIs for the Phantom S710.

## Single-particle localisation
The flag --localise turns on single-particle localisation. Only one of the camera banks can be used for this because CustomLogic firmware supporting more banks is not available for our Coaxlink Octo card.

## Contact
Alistair Curd - a.curd@leeds.ac.uk





