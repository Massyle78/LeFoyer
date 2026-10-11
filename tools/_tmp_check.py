import itertools, sys
import ezdxf
from ezdxf.addons.drawing import Frontend, RenderContext
from ezdxf.addons.drawing.matplotlib import MatplotlibBackend
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from shapely.geometry import Polygon
from shapely.ops import unary_union

doc = ezdxf.readfile("merch/bus-buddy-pins.dxf")
aud = doc.audit()
print("audit errors", len(aud.errors), "fixes", len(aud.fixes))
msp = doc.modelspace()
cut = [Polygon(e.get_points("xy")) for e in msp if e.dxf.layer == "CUT"]
# outer contours = those not contained in another cut polygon
outers = [p for i, p in enumerate(cut) if not any(j != i and q.contains(p) for j, q in enumerate(cut))]
print("cut polys", len(cut), "outer", len(outers))
mind = min(a.distance(b) for a, b in itertools.combinations(outers, 2))
print("min gap between outer contours: %.2f" % mind)
allb = [e.dxf.layer for e in msp]
xs, ys = [], []
for e in msp:
    if e.dxf.layer in ("CUT", "ENGRAVE", "LABELS"):
        for x, y in e.get_points("xy"):
            xs.append(x); ys.append(y)
print("extent", min(xs), max(xs), min(ys), max(ys))
# engrave inside its piece border / label overlap checks
eng = [Polygon(e.get_points("xy")).buffer(0) for e in msp if e.dxf.layer == "ENGRAVE"]
lab = [Polygon(e.get_points("xy")).buffer(0) for e in msp if e.dxf.layer == "LABELS"]
labu = unary_union(lab)
print("label overlaps cut:", any(labu.intersects(o) for o in outers))
# border check: for each outer piece, engraved rings (lines) must not come within 0.4 of each other except border
bad = 0
for o in outers:
    inside = [Polygon(e.get_points("xy")) for e in msp if e.dxf.layer == "ENGRAVE" and o.contains(Polygon(e.get_points("xy")).representative_point())]
    border = max(inside, key=lambda p: p.area)
    ring = border.exterior
    print("piece %.0f,%.0f" % (o.centroid.x, o.centroid.y), end=" ")
    others = unary_union([p.buffer(0) for p in inside if p is not border])
    d_border = others.distance(ring) if not others.is_empty else 99
    d_cut = border.exterior.distance(o.exterior)
    print("engrave->border %.2f border->edge %.2f" % (d_border, d_cut))
# crops
def crop(name, x0, x1, y0, y1, dpi=300):
    fig = plt.figure(figsize=((x1 - x0) / 25.4 * 2.2, (y1 - y0) / 25.4 * 2.2), dpi=dpi)
    ax = fig.add_axes([0, 0, 1, 1])
    ctx = RenderContext(doc); ctx.set_current_layout(msp)
    Frontend(ctx, MatplotlibBackend(ax)).draw_layout(msp, finalize=True)
    ax.set_xlim(x0, x1); ax.set_ylim(y0, y1)
    fig.savefig(name, facecolor="white")
ys_sorted = sorted(set(round(o.bounds[1]) for o in outers))
print("row bottoms", ys_sorted)

from shapely.geometry import MultiPolygon
labs=[Polygon(e.get_points('xy')).buffer(0) for e in msp if e.dxf.layer=='LABELS']
g=[l for l in labs]
clusters=[]
for l in sorted(labs,key=lambda p:p.bounds[0]):
    pass
box=[unary_union(labs).buffer(0.3)]
import shapely
parts=list(box[0].geoms) if hasattr(box[0],'geoms') else box
print('label clusters',len(parts))
allp=unary_union(outers)
print('label min dist to cut: %.2f' % unary_union(labs).distance(allp))
