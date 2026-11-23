"""People-scale world for 1 cm humans: every everyday object is ~170x bigger (170 cm person -> 1 cm)."""
from studio3d.lib.blocky import box
from studio3d.lib.sets import ground

SCALE = 170.0


def table_top(col=(0.62, 0.45, 0.28), wall=(0.88, 0.85, 0.78)):
    """A wooden table that is a plain to the tiny people, with a room wall far behind."""
    ground(2000, col)
    for k in range(-6, 7):                                       # wood grain stripes
        box((0, k * 22.0, 0.003), (2000, 0.6, 0.006), (0.55, 0.39, 0.24), bevel=0)
    box((0, 420, 150), (2000, 10, 300), wall, bevel=0)
