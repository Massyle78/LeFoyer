import ezdxf
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from ezdxf.addons.drawing import Frontend, RenderContext
from ezdxf.addons.drawing.matplotlib import MatplotlibBackend

doc = ezdxf.readfile("merch/bus-buddy-pins.dxf")
msp = doc.modelspace()


def crop(name, x0, x1, y0, y1, dpi=300):
    fig = plt.figure(figsize=((x1 - x0) / 25.4 * 2.4, (y1 - y0) / 25.4 * 2.4), dpi=dpi)
    ax = fig.add_axes([0, 0, 1, 1])
    ctx = RenderContext(doc)
    ctx.set_current_layout(msp)
    Frontend(ctx, MatplotlibBackend(ax)).draw_layout(msp, finalize=True)
    ax.set_xlim(x0, x1)
    ax.set_ylim(y0, y1)
    fig.savefig(name, facecolor="white")


crop("merch/_zoom_a.png", 8, 152, 42, 72)
crop("merch/_zoom_b.png", 150, 292, 42, 72)
crop("merch/_zoom_c.png", 8, 152, 8, 38)
crop("merch/_zoom_d.png", 150, 292, 8, 38)
