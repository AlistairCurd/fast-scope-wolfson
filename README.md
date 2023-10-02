# fast-scope-wolfson
Software for running fast microscope system in Wolfson Imaging Facility, University of Leeds.

## Built With
* Python 3.10
* Euresys eGrabber API for Coaxlink cards

# Getting started
* Set up a Python 3 environment (only 3.10 tested).
* Install the eGrabber Python bindings wheel from Euresys.
* Install opencv, pillow
* Test with the sample eGrabber scripts from Euresys.

## Phantom S710 unscrambling
We use a Phantom S710 CMOS camera, which reads images in two banks, middle upwards and middle downwards. Without settings to correct for this, images will appear stripy.

To acquire unscrambled images with two banks of the camera in use (out of four), set these in Euresys GenICam Browser:

For 1280 x 800 resolution:
* Phantom S710: Banks: Set to Banks_A

For 1280 x 400 resolution:
* Phantom S710: Banks: Set to Banks_AB

In Stream0, for 8-bit images:
* LineWidth: 1280 (Probably 2560 for 16-bit)
* LinePitch: 0
* StripeHeight: 1
* StripePitch: 1
* BlockHeight: 8
* StripeOffset: 0
* StripeArrangement: Geometry_1X_2YM <2 taps arranged middle-up and middle-down>

# Contact
Alistair Curd - a.curd@leeds.ac.uk





