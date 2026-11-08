"""s02: a car waits at a crossing; the signal is grey — but the lit lamp sits on the right (= red). Low angle."""
import math

from _common import aim, camera, daylight, ease, lerp
from studio3d.lib.blocky import Person, car, traffic_signal
from studio3d.lib.sets import town_street

SECONDS = 5.0


def build(ctx):
    town_street(seed=22)
    daylight(55, 160, 0.4, 3.2)
    traffic_signal((3.0, 9.0, 0), yaw=0.0, lit="red")
    c = car("car", (1.4, 4.0, 0), 0.0, col=(0.2, 0.45, 0.8))
    p = Person("ped", (-2.8, 8.6, 0), -math.pi / 2, 1.68, shirt=1)
    return {"car": c, "p": p, "cam": camera(34)}


def pose(ctx, h, t):
    h["p"].stand(t)
    h["p"].look_up(t, 0.4)
    q = ease(t / SECONDS)
    aim(h["cam"], (lerp(0.2, 0.6, q), lerp(1.0, 2.5, q), 1.3), (1.2, 9.0, lerp(4.2, 4.9, q)))
