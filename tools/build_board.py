#!/usr/bin/env python3
"""Generate the X-Sub board figure directly from its imported PCB layout."""

import argparse
import json
import math
import re
from collections import defaultdict
from html import escape
from pathlib import Path

TOKEN = re.compile(r'"(?:[^"\\]|\\.)*"|[()]|[^\s()"]+')
LAYERS = ("B.Cu", "F.Cu")
SIGNALS = {
    "imu": ("SCL", "SDA"),
    "thrusters": tuple(f"M{i}_ESC" for i in range(1, 5)),
    "depth": ("P_OUT", "NetOPAMP_1_3", "ADC_PRESSURE_3.3V"),
    "ingress": (
        "PRESENCIAAGUA1",
        "PRESENCIAAGUA2",
        "NetPres_Agua1_2",
        "NetPres_Agua2_2",
    ),
    "camera": ("S_PANCAMERA", "S_TILTCAMERA"),
    "serial": ("TXSERIALCOM", "RXSERIALCOM", "TXSERIALCOM2", "RXSERIALCOM2"),
    "lights": ("LEDLIGHT1", "LEDLIGHT2"),
    "battery": ("AD5_BAT", "NetBatR1_2"),
    "power": ("+3.3V", "+5V", "GND", "+V_SERVO", "+V_SERVO_IN"),
}


def parse(source):
    stack = [[]]
    for token in TOKEN.findall(source):
        if token == "(":
            stack.append([])
        elif token == ")":
            value = stack.pop()
            stack[-1].append(value)
        else:
            stack[-1].append(token[1:-1] if token.startswith('"') else token)
    if len(stack) != 1 or len(stack[0]) != 1 or stack[0][0][0] != "kicad_pcb":
        raise ValueError("Expected a complete KiCad board")
    return stack[0][0]


def children(node, key):
    return [v for v in node if isinstance(v, list) and v[0] == key]


def child(node, key, default=()):
    return next((v[1:] for v in node if isinstance(v, list) and v[0] == key), default)


def nums(node, key):
    return tuple(map(float, child(node, key)))


def number(x):
    s = f"{x:.2f}".rstrip("0").rstrip(".")
    if s == "-0":
        return "0"
    return s.replace("-0.", "-.").removeprefix("0") if "." in s and abs(x) < 1 else s


def xy(p):
    return " ".join(number(v) for v in p)


def path(d, attrs=""):
    return f'<path {attrs} d="{d}"/>' if d else ""


def net(node):
    return child(node, "net", ("",))[-1]


def rotation(point, angle):
    theta = math.radians(-angle)
    x, y = point
    return (
        x * math.cos(theta) - y * math.sin(theta),
        x * math.sin(theta) + y * math.cos(theta),
    )


def transform(local, at):
    x, y = rotation(local, at[2] if len(at) > 2 else 0)
    return (at[0] + x, at[1] + y)


def polypath(points, close=False):
    first, *rest = points
    parts = ["M" + xy(first)]
    previous = first
    command = "L"
    for point in rest:
        x, y = point
        last_x, last_y = previous
        options = [("L", xy(point)), ("l", xy((x - last_x, y - last_y)))]
        # Relative movements must not accumulate rounding drift.
        if xy(point) != xy(
            (
                round(last_x, 2) + round(x - last_x, 2),
                round(last_y, 2) + round(y - last_y, 2),
            )
        ):
            options.pop()
        if number(x) == number(last_x):
            options.append(("V", number(y)))
        if number(y) == number(last_y):
            options.append(("H", number(x)))
        token, coords = min(
            options, key=lambda pair: len(pair[1]) + (pair[0] != command)
        )
        parts.append((" " if token == command else token) + coords)
        previous, command = point, token
    return "".join(parts).replace(" -", "-") + ("Z" if close else "")


def linework(segments):
    """Walk between junctions and drop intermediate collinear vertices."""
    graph = defaultdict(set)
    for a, b in segments:
        if a != b:
            graph[a].add(b)
            graph[b].add(a)
    degrees = {p: len(adj) for p, adj in graph.items()}
    lines = []
    for start in sorted(graph, key=lambda p: (degrees[p] == 2, p)):
        while graph[start]:
            chain = [start]
            at = start
            while graph[at]:
                nxt = min(graph[at])
                graph[at].remove(nxt)
                graph[nxt].remove(at)
                if len(chain) > 1:
                    a, b = chain[-2:]
                    cross = (b[0] - a[0]) * (nxt[1] - b[1]) - (b[1] - a[1]) * (
                        nxt[0] - b[0]
                    )
                    if abs(cross) < 1e-8:
                        chain.pop()
                chain.append(nxt)
                at = nxt
                if degrees[at] != 2:
                    break
            lines.append(polypath(chain))
    return "".join(lines)


def simplify(points, tolerance=0.15):
    """Simplify decorative zone boundaries to a subpixel tolerance in mm."""
    if len(points) < 3:
        return points
    a, b = points[0], points[-1]
    dx, dy = b[0] - a[0], b[1] - a[1]
    length = dx * dx + dy * dy
    error = 0
    split = 0
    for i, (x, y) in enumerate(points[1:-1], 1):
        t = (
            min(1, max(0, ((x - a[0]) * dx + (y - a[1]) * dy) / length))
            if length
            else 0
        )
        dist = (x - a[0] - t * dx) ** 2 + (y - a[1] - t * dy) ** 2
        if dist > error:
            error, split = dist, i
    if error <= tolerance * tolerance:
        return [a, b]
    return simplify(points[: split + 1], tolerance)[:-1] + simplify(
        points[split:], tolerance
    )


def circle(center, radius, reverse=False):
    x, y = center
    r = number(radius)
    diameter = number(2 * radius)
    sweep = int(reverse)
    return f"M{xy((x - radius, y))}a{r} {r} 0 1 {sweep} {diameter} 0 {r} {r} 0 1 {sweep} -{diameter} 0Z"


LICENCE = """<!-- MIT License

Copyright (c) 2015-2026 Danilo Díaz Tarascó

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE. -->"""


STYLE = """<style>
.board.xsub-board{display:block;width:100%;height:auto;overflow:visible}
.xsub-board .pcb-base{fill:var(--board-substrate,#f1ece2)}
.xsub-board .pcb-side{fill:var(--board-edge,#86847d);display:none}
@media(min-width:720px) and (prefers-reduced-motion:no-preference){.js .xsub-board .pcb-side,.ready .xsub-board .pcb-side{display:block}}
.xsub-board .pcb-edge{fill:none;stroke:var(--board-edge,#86847d);stroke-width:.19}
.xsub-board [data-layer="F.Cu"]{--net-color:color-mix(in srgb,var(--board-copper,#a8581f) 81%,var(--board-substrate,#f1ece2))}
.xsub-board [data-layer="B.Cu"]{--net-color:color-mix(in srgb,var(--board-copper-back,#c99a74) 50%,var(--board-substrate,#f1ece2))}
.xsub-board .pcb-route{stroke-width:var(--fine)}
.xsub-board [data-net].is-lit .pcb-route{stroke-width:var(--actual)}
.xsub-board [data-net],.xsub-board .pcb-free{color:var(--net-color,var(--board-copper,#a8581f))}
.xsub-board .pcb-zone{fill:var(--board-pour,#e9dccb);opacity:.38}
.xsub-board .pcb-tracks{fill:none;stroke:currentColor;stroke-linecap:round;stroke-linejoin:round}
.xsub-board .pcb-pads{fill:currentColor}
.xsub-board .pcb-silk{color:var(--board-silk,#3b3a36);fill:currentColor}
.xsub-board .pcb-drills{fill:var(--board-drill,#fff)}
.tech-figure[data-lit] .xsub-board [data-net],.tech-figure[data-lit] .xsub-board .pcb-free{--net-color:var(--board-copper-dim,#dccab6)}
.tech-figure[data-lit] .xsub-board [data-net].is-lit{--net-color:var(--board-highlight,#7c3b0e)}
.tech-figure[data-lit] .xsub-board .pcb-silk{opacity:.48}
.xsub-board .pcb-endpoint{display:none;color:var(--board-highlight,#7c3b0e);pointer-events:none}
.xsub-board .pcb-endpoint path{fill:none;stroke:currentColor;stroke-width:.16}
.xsub-board .pcb-endpoint circle{fill:var(--board-substrate,#f1ece2);stroke:currentColor;stroke-width:.25}
.xsub-board .pcb-endpoint text{font:500 2.05px var(--font-mono,"IBM Plex Mono",monospace);fill:currentColor;stroke:var(--board-substrate,#f1ece2);stroke-width:.8;stroke-linejoin:round;paint-order:stroke}
@media(min-width:720px){ENDPOINT_RULES}
@media(max-width:480px){.xsub-board [data-net].is-lit .pcb-route{stroke-width:max(.44px,calc(var(--actual)*1px))}}
</style>"""


def build(root):
    edges = [g for g in children(root, "gr_line") if child(g, "layer") == ["Edge.Cuts"]]
    points = [nums(g, k) for g in edges for k in ("start", "end")]
    left, top = map(min, zip(*points))
    right, bottom = map(max, zip(*points))
    width, height = right - left, bottom - top

    def local(p):
        return round(p[0] - left, 5), round(p[1] - top, 5)

    footprints, tracks, vias, zones = (
        children(root, k) for k in ("footprint", "segment", "via", "zone")
    )
    strokes, pads, pours, silk_lines = (
        defaultdict(list),
        defaultdict(list),
        defaultdict(list),
        defaultdict(list),
    )
    drills, silk_marks, all_nets = [], [], set()
    annuli, pin_centers, oval_pads = (
        defaultdict(list),
        defaultdict(list),
        defaultdict(list),
    )
    segments_by_layer = defaultdict(int)
    for track in tracks:
        layer, name = child(track, "layer")[0], net(track)
        strokes[layer, name, nums(track, "width")[0]].append(
            (local(nums(track, "start")), local(nums(track, "end")))
        )
        segments_by_layer[layer] += 1
        all_nets.add(name)
    for via in vias:
        center = local(nums(via, "at"))
        for layer in child(via, "layers"):
            outer, inner = nums(via, "size")[0] / 2, nums(via, "drill")[0] / 2
            annuli[layer, net(via), round(outer - inner, 4)].append(
                circle(center, (outer + inner) / 2)
            )
        drills.append(circle(center, nums(via, "drill")[0] / 2))
        all_nets.add(net(via))

    mcu = None
    for fp in footprints:
        fp_at = nums(fp, "at")
        ref = next(p[2] for p in children(fp, "property") if p[1] == "Reference")

        def place(p, placement=fp_at):
            return local(transform(p[:2], placement))

        for prop in children(fp, "property"):
            if prop[1] == "Value" and re.fullmatch(r"MCF51\w+", prop[2]):
                mcu = prop[2]
        for pad in children(fp, "pad"):
            center = place(nums(pad, "at"))
            at, size = nums(pad, "at"), nums(pad, "size")
            # Pad orientation is absolute in the board file; its position is footprint-local.
            angle = at[2] if len(at) > 2 else 0
            if pad[3] == "circle":
                copper = circle(center, size[0] / 2)
            elif pad[3] == "rect":
                corners = [
                    (a * size[0] / 2, b * size[1] / 2)
                    for a, b in ((-1, -1), (1, -1), (1, 1), (-1, 1))
                ]
                copper = polypath(
                    [transform(p, (*center, angle)) for p in corners], True
                )
            elif pad[3] == "oval":
                radius = min(size) / 2
                delta = (max(size) - min(size)) / 2
                span = (delta, 0) if size[0] >= size[1] else (0, delta)
                ends = [
                    transform((sign * span[0], sign * span[1]), (*center, angle))
                    for sign in (-1, 1)
                ]
                copper = None
            else:
                raise ValueError(f"Unsupported pad shape {pad[3]}")
            name = net(pad)
            pin_centers[ref, name].append(center)
            drill = nums(pad, "drill")
            if drill and pad[3] == "rect":
                copper += circle(center, drill[0] / 2)
            all_nets.add(name)
            for layer in LAYERS:
                assigned = child(pad, "layers")
                if layer in assigned or "*.Cu" in assigned:
                    if drill and pad[3] == "circle":
                        outer, inner = size[0] / 2, drill[0] / 2
                        if outer > inner:
                            annuli[layer, name, round(outer - inner, 4)].append(
                                circle(center, (outer + inner) / 2)
                            )
                    elif copper is None:
                        oval_pads[layer, name, radius * 2].append(polypath(ends))
                    else:
                        pads[layer, name].append(copper)
            if child(pad, "drill"):
                drills.append(circle(center, nums(pad, "drill")[0] / 2))
        for line in children(fp, "fp_line"):
            if child(line, "layer") == ["F.SilkS"]:
                silk_lines[nums(child(line, "stroke"), "width")[0]].append(
                    (place(nums(line, "start")), place(nums(line, "end")))
                )
        for mark in children(fp, "fp_circle"):
            if child(mark, "layer") == ["F.SilkS"]:
                center, edge = place(nums(mark, "center")), place(nums(mark, "end"))
                silk_marks.append(
                    path(
                        circle(center, math.dist(center, edge)),
                        f'class="pcb-tracks" stroke-width="{number(nums(child(mark, "stroke"), "width")[0])}"',
                    )
                )
    for rect in children(root, "gr_rect"):
        layer = child(rect, "layer")[0]
        if layer in LAYERS:
            x1, y1 = local(nums(rect, "start"))
            x2, y2 = local(nums(rect, "end"))
            pads[layer, net(rect)].append(
                polypath([(x1, y1), (x2, y1), (x2, y2), (x1, y2)], True)
            )
    for line in children(root, "gr_line"):
        layer = child(line, "layer")[0]
        if layer in LAYERS:
            strokes[layer, net(line), nums(child(line, "stroke"), "width")[0]].append(
                (local(nums(line, "start")), local(nums(line, "end")))
            )
    for zone in zones:
        for poly in children(zone, "filled_polygon"):
            layer = child(poly, "layer")[0]
            ring = [
                local(tuple(map(float, pt[1:])))
                for pt in children(child(poly, "pts"), "xy")
            ]
            if len(ring) >= 3:
                reduced = simplify(ring + [ring[0]])[:-1]
                if len(reduced) >= 3:
                    pours[layer].append(
                        polypath([(round(x, 1), round(y, 1)) for x, y in reduced], True)
                    )

    all_nets.discard("")
    missing = set().union(*SIGNALS.values()) - all_nets
    if missing or not mcu:
        raise ValueError(
            f"Board identity or signal mapping mismatch: {sorted(missing)}"
        )
    counts = {
        "width_mm": round(width, 3),
        "height_mm": round(height, 3),
        "copper_layers": len(segments_by_layer),
        "footprints": len(footprints),
        "nets": len(all_nets),
        "segments": len(tracks),
        "vias": len(vias),
        "mcu": mcu,
        "zones": len(zones),
        "filled_polygons": sum(len(children(z, "filled_polygon")) for z in zones),
    }
    data = {
        "spec": counts,
        "signals": {k: list(v) for k, v in SIGNALS.items()},
        "nets": sorted(all_nets),
    }

    def layer(name, items, extra=""):
        # The outer coordinate system uses ten units per mm so browsers rasterize
        # separated 3D planes sharply. All path geometry stays in millimeters.
        return (
            f'<g data-layer="{name}"{extra}><g transform="scale(10)">'
            + "\n".join(filter(None, items))
            + "</g></g>"
        )

    endpoint_refs = {
        "imu": ("MCU", "GY-521", "COMPASS"),
        "thrusters": ("MCU", "Motor_Out"),
        "depth": ("Sensor_Pres", "OPAMP_1"),
        "ingress": ("Q1", "Q2"),
        "camera": ("MCU", "Servo_Out"),
        "serial": ("MCU", "UART"),
        "lights": ("LED_L1", "LED_L2"),
        "battery": ("BatR1", "Batt_Measure"),
        "power": ("C_3.3V", "V_Servo_In"),
    }
    part_labels = {
        "COMPASS": "HMC6352",
        "OPAMP_1": "OPA345",
        "Sensor_Pres": "MPX5700AP",
        "Motor_Out": "ESC ×4",
        "Servo_Out": "Pan / tilt",
        "LED_L1": "LED 1",
        "LED_L2": "LED 2",
    }
    annotation = []
    for key, refs in endpoint_refs.items():
        marks = []
        for ref in refs:
            # Anchor the tag on a pad carrying the selected net.
            pins = [p for signal in SIGNALS[key] for p in pin_centers[ref, signal]]
            if not pins:
                raise ValueError(f"No {key} pin on {ref}")
            x, y = pins[0]
            rightward = x < width - 18
            dx = 3.2 if rightward else -3.2
            dy = 4 if y < 9 or ref == "COMPASS" else -4
            if ref == "OPAMP_1":
                dy = 5.5
            label = part_labels.get(ref, ref)
            pos = "start" if rightward else "end"
            marks.extend(
                [
                    path(polypath([(x, y), (x + dx, y + dy)])),
                    f'<circle cx="{number(x)}" cy="{number(y)}" r=".47"/>',
                    f'<text x="{number(x + dx)}" y="{number(y + dy)}" text-anchor="{pos}">{escape(label)}</text>',
                ]
            )
        annotation.append(
            f'<g class="pcb-endpoint e-{key}" aria-hidden="true">'
            + "".join(marks)
            + "</g>"
        )
    rules = (
        ",".join(f'.tech-figure[data-lit="{k}"] .xsub-board .e-{k}' for k in SIGNALS)
        + "{display:block}"
    )
    rect = f'width="{number(width)}" height="{number(height)}"'
    side = polypath(
        [
            (0, height),
            (width, height),
            (width, 0),
            (width + 0.22, 0.72),
            (width + 0.22, height + 0.72),
            (0.22, height + 0.72),
        ],
        True,
    )
    svg = [
        f'<svg xmlns="http://www.w3.org/2000/svg" class="board xsub-board" role="img" aria-label="X-Sub acquisition board copper layout" focusable="false" viewBox="-42 -26 {number((width + 8.4) * 10)} {number((height + 5.2) * 10)}">',
        LICENCE,
        STYLE.replace("ENDPOINT_RULES", rules),
        layer(
            "substrate",
            [path(side, 'class="pcb-side"'), f'<rect class="pcb-base" {rect}/>'],
        ),
        layer(
            "zones",
            [
                path(
                    "".join(pours[side]),
                    f'class="pcb-zone" data-side="{side}" fill-rule="evenodd"',
                )
                for side in LAYERS
            ],
        ),
    ]
    for side in LAYERS:
        groups = []
        for name in [""] + sorted(all_nets):
            items = []
            for (assigned_side, assigned_net, weight), lines in sorted(strokes.items()):
                if (assigned_side, assigned_net) != (side, name):
                    continue
                fine = (
                    min(0.31, weight * 0.72)
                    if side == "F.Cu"
                    else min(0.22, weight * 0.58)
                )
                items.append(
                    path(
                        linework(lines),
                        f'class="pcb-tracks pcb-route" style="--fine:{number(fine)};--actual:{number(weight)}"',
                    )
                )
            for (assigned_side, assigned_net, weight), spans in sorted(
                oval_pads.items()
            ):
                if (assigned_side, assigned_net) == (side, name):
                    items.append(
                        path(
                            "".join(spans),
                            f'class="pcb-tracks" stroke-width="{number(weight)}"',
                        )
                    )
            for (assigned_side, assigned_net, weight), rings in sorted(annuli.items()):
                if (assigned_side, assigned_net) == (side, name):
                    items.append(
                        path(
                            "".join(rings),
                            f'class="pcb-tracks" stroke-width="{number(weight)}"',
                        )
                    )
            items.append(path("".join(sorted(pads[side, name])), 'class="pcb-pads"'))
            if any(items):
                attr = (
                    f'data-net="{escape(name, quote=True)}"'
                    if name
                    else 'class="pcb-free"'
                )
                groups.append(f"<g {attr}>" + "".join(items) + "</g>")
        if side == "F.Cu":
            groups.extend(annotation)
        svg.append(layer(side, groups))
    for weight, lines in sorted(silk_lines.items()):
        silk_marks.append(
            path(linework(lines), f'class="pcb-tracks" stroke-width="{number(weight)}"')
        )
    svg.extend(
        [
            layer("F.SilkS", ['<g class="pcb-silk">', *silk_marks, "</g>"]),
            layer("drill", [path("".join(drills), 'class="pcb-drills"')]),
            layer("Edge.Cuts", [f'<rect class="pcb-edge" {rect}/>']),
            "</svg>",
        ]
    )
    return "\n".join(svg) + "\n", json.dumps(data, indent=2, ensure_ascii=False) + "\n"


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("source", type=Path)
    p.add_argument("--out", type=Path, default=Path("."))
    p.add_argument("--check", action="store_true")
    args = p.parse_args()
    outputs = zip(
        ("board.svg", "board.json"),
        build(parse(args.source.read_text(encoding="utf-8"))),
    )
    for name, content in outputs:
        dest = args.out / name
        if args.check:
            if not dest.exists() or dest.read_bytes() != content.encode():
                p.exit(1, f"Stale board output: {dest}\n")
        else:
            args.out.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(content.encode())


if __name__ == "__main__":
    main()
