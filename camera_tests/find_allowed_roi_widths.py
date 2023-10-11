"""Find the widths that can be set on the Phantom S710
without producing a GenTL error."""

from egrabber import EGenTL, EGrabber, errors


# Create grabber
gentl = EGenTL()
grabber = EGrabber(gentl)

print('\nGrabber created.')

for w in range(1280):
    try:
        width = w + 1
        grabber.remote.set('Width', width)

    except errors.GenTLException:
        continue

    print(width)
