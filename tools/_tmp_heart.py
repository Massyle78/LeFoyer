import sys
sys.path.insert(0, "tools")
import make_pins_dxf as m
from shapely.geometry import LineString
h = m.heart(0, 0, 25).buffer(-1.4)
print(h.bounds)
for y in range(-11, 12):
    i = h.intersection(LineString([(-30, y), (30, y)]))
    print(y, [round(v, 1) for v in i.bounds] if not i.is_empty else None, "pieces", len(getattr(i, "geoms", [i])))
