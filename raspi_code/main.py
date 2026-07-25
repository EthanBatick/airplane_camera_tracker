#!/usr/bin/python

from PlaneTracker import PlaneTracker
import sys

pt = PlaneTracker(
    str(sys.argv[1]),
    (39.663280, -104.995552),
    1630
)

pt.start()
