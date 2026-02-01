#!/usr/bin/env python3
"""Software-render an STL to PNG with a consistent marketing angle.

- Parses ASCII or binary STL
- Computes vertex normals (area-weighted)
- Perspective projection
- Z-buffer rasterization (barycentric)
- Simple Lambert shading with 1 directional light + ambient

Dependencies: pillow
"""

from __future__ import annotations

import argparse
import math
import os
import struct
from dataclasses import dataclass
from typing import Iterable, List, Optional, Sequence, Tuple, Dict

from PIL import Image

Vec3 = Tuple[float, float, float]


def v_add(a: Vec3, b: Vec3) -> Vec3:
    return (a[0] + b[0], a[1] + b[1], a[2] + b[2])


def v_sub(a: Vec3, b: Vec3) -> Vec3:
    return (a[0] - b[0], a[1] - b[1], a[2] - b[2])


def v_mul(a: Vec3, s: float) -> Vec3:
    return (a[0] * s, a[1] * s, a[2] * s)


def v_dot(a: Vec3, b: Vec3) -> float:
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]


def v_cross(a: Vec3, b: Vec3) -> Vec3:
    return (
        a[1] * b[2] - a[2] * b[1],
        a[2] * b[0] - a[0] * b[2],
        a[0] * b[1] - a[1] * b[0],
    )


def v_len(a: Vec3) -> float:
    return math.sqrt(v_dot(a, a))


def v_norm(a: Vec3) -> Vec3:
    l = v_len(a)
    if l <= 1e-12:
        return (0.0, 0.0, 0.0)
    return (a[0] / l, a[1] / l, a[2] / l)


def clamp01(x: float) -> float:
    return 0.0 if x < 0.0 else 1.0 if x > 1.0 else x


def parse_hex_color(s: str) -> Tuple[int, int, int]:
    s = s.strip()
    if s.startswith("#"):
        s = s[1:]
    if len(s) != 6:
        raise ValueError(f"Expected #rrggbb, got: {s!r}")
    r = int(s[0:2], 16)
    g = int(s[2:4], 16)
    b = int(s[4:6], 16)
    return (r, g, b)


def parse_vec3(s: str) -> Vec3:
    parts = [p.strip() for p in s.split(",")]
    if len(parts) != 3:
        raise ValueError(f"Expected x,y,z, got: {s!r}")
    return (float(parts[0]), float(parts[1]), float(parts[2]))


@dataclass
class Tri:
    a: Vec3
    b: Vec3
    c: Vec3


def read_stl(path: str) -> List[Tri]:
    with open(path, "rb") as f:
        data = f.read()

    # Heuristic: if starts with 'solid' and looks like ASCII, try ASCII parse.
    # Binary STLs can also start with 'solid', so confirm by scanning for 'facet'.
    head = data[:80]
    if head.lstrip().startswith(b"solid") and b"facet" in data[:4096]:
        try:
            text = data.decode("utf-8", errors="ignore")
            return read_stl_ascii(text)
        except Exception:
            pass
    return read_stl_binary(data)


def read_stl_ascii(text: str) -> List[Tri]:
    tris: List[Tri] = []
    verts: List[Vec3] = []
    for line in text.splitlines():
        line = line.strip()
        if line.startswith("vertex "):
            _, xs, ys, zs = line.split()
            verts.append((float(xs), float(ys), float(zs)))
            if len(verts) == 3:
                tris.append(Tri(verts[0], verts[1], verts[2]))
                verts = []
    if verts:
        # ignore partial
        pass
    if not tris:
        raise ValueError("No triangles parsed from ASCII STL")
    return tris


def read_stl_binary(data: bytes) -> List[Tri]:
    if len(data) < 84:
        raise ValueError("STL file too small")
    n = struct.unpack_from("<I", data, 80)[0]
    offset = 84
    tris: List[Tri] = []
    rec_size = 50
    expected = offset + n * rec_size
    if expected > len(data):
        # Some STLs lie; clamp by available bytes.
        n = max(0, (len(data) - offset) // rec_size)
    for _ in range(n):
        # normal ignored; recompute later
        # <3f normal, 9f vertices, H attr
        if offset + rec_size > len(data):
            break
        _nx, _ny, _nz = struct.unpack_from("<3f", data, offset)
        ax, ay, az, bx, by, bz, cx, cy, cz = struct.unpack_from("<9f", data, offset + 12)
        tris.append(Tri((ax, ay, az), (bx, by, bz), (cx, cy, cz)))
        offset += rec_size
    if not tris:
        raise ValueError("No triangles parsed from binary STL")
    return tris


def bounds(tris: Sequence[Tri]) -> Tuple[Vec3, Vec3]:
    xs: List[float] = []
    ys: List[float] = []
    zs: List[float] = []
    for t in tris:
        for v in (t.a, t.b, t.c):
            xs.append(v[0])
            ys.append(v[1])
            zs.append(v[2])
    return (min(xs), min(ys), min(zs)), (max(xs), max(ys), max(zs))


def tri_normal(t: Tri) -> Vec3:
    ab = v_sub(t.b, t.a)
    ac = v_sub(t.c, t.a)
    return v_norm(v_cross(ab, ac))


def tri_area(t: Tri) -> float:
    ab = v_sub(t.b, t.a)
    ac = v_sub(t.c, t.a)
    return 0.5 * v_len(v_cross(ab, ac))


def build_vertex_normals(tris: Sequence[Tri]) -> Tuple[List[Vec3], List[Tuple[int, int, int]]]:
    # Deduplicate vertices by exact float tuple.
    vmap: dict[Vec3, int] = {}
    verts: List[Vec3] = []
    faces: List[Tuple[int, int, int]] = []
    acc: List[Vec3] = []

    def vid(v: Vec3) -> int:
        if v in vmap:
            return vmap[v]
        i = len(verts)
        vmap[v] = i
        verts.append(v)
        acc.append((0.0, 0.0, 0.0))
        return i

    for t in tris:
        ia, ib, ic = vid(t.a), vid(t.b), vid(t.c)
        faces.append((ia, ib, ic))
        n = tri_normal(t)
        a = tri_area(t)
        w = a if a > 1e-12 else 1.0
        acc[ia] = v_add(acc[ia], v_mul(n, w))
        acc[ib] = v_add(acc[ib], v_mul(n, w))
        acc[ic] = v_add(acc[ic], v_mul(n, w))

    norms = [v_norm(n) for n in acc]
    return verts, faces, norms


def rot_z(v: Vec3, ang: float) -> Vec3:
    c = math.cos(ang)
    s = math.sin(ang)
    return (v[0] * c - v[1] * s, v[0] * s + v[1] * c, v[2])


def rot_x(v: Vec3, ang: float) -> Vec3:
    c = math.cos(ang)
    s = math.sin(ang)
    return (v[0], v[1] * c - v[2] * s, v[1] * s + v[2] * c)


def mat3_mul_vec(m: Tuple[Vec3, Vec3, Vec3], v: Vec3) -> Vec3:
    (m0, m1, m2) = m
    return (
        m0[0] * v[0] + m0[1] * v[1] + m0[2] * v[2],
        m1[0] * v[0] + m1[1] * v[1] + m1[2] * v[2],
        m2[0] * v[0] + m2[1] * v[1] + m2[2] * v[2],
    )


def rotation_from_to(a: Vec3, b: Vec3) -> Tuple[Vec3, Vec3, Vec3]:
    """Return 3x3 rotation matrix that rotates vector a onto b (both need not be unit)."""
    au = v_norm(a)
    bu = v_norm(b)
    dot = clamp01((v_dot(au, bu) + 1.0) / 2.0) * 2.0 - 1.0  # stable clamp to [-1,1]
    dot = max(-1.0, min(1.0, dot))

    if dot > 1.0 - 1e-9:
        return ((1.0, 0.0, 0.0), (0.0, 1.0, 0.0), (0.0, 0.0, 1.0))

    if dot < -1.0 + 1e-9:
        # 180 deg: choose any orthogonal axis
        axis = v_norm(v_cross(au, (1.0, 0.0, 0.0)))
        if v_len(axis) < 1e-6:
            axis = v_norm(v_cross(au, (0.0, 1.0, 0.0)))
        x, y, z = axis
        # Rodrigues with angle pi => R = -I + 2*axis*axis^T
        return (
            (-1.0 + 2 * x * x, 2 * x * y, 2 * x * z),
            (2 * y * x, -1.0 + 2 * y * y, 2 * y * z),
            (2 * z * x, 2 * z * y, -1.0 + 2 * z * z),
        )

    axis = v_norm(v_cross(au, bu))
    ang = math.acos(dot)
    x, y, z = axis
    c = math.cos(ang)
    s = math.sin(ang)
    C = 1.0 - c
    # Rodrigues rotation matrix
    return (
        (c + x * x * C, x * y * C - z * s, x * z * C + y * s),
        (y * x * C + z * s, c + y * y * C, y * z * C - x * s),
        (z * x * C - y * s, z * y * C + x * s, c + z * z * C),
    )


def auto_upright_rotation(tris: Sequence[Tri], center: Vec3, radius: float) -> Tuple[Vec3, Vec3, Vec3]:
    """Heuristic: pick a face-normal (from large triangles) that yields max bottom support area."""
    # Collect candidates from largest triangles
    scored: List[Tuple[float, Vec3]] = []
    for t in tris:
        a = tri_area(t)
        if a <= 1e-10:
            continue
        n = tri_normal(t)
        scored.append((a, n))
    scored.sort(key=lambda x: x[0], reverse=True)
    candidates = [n for _, n in scored[:250]]

    # Dedup by quantized direction
    uniq: Dict[Tuple[int, int, int], Vec3] = {}
    for n in candidates:
        nn = v_norm(n)
        k = (int(round(nn[0] * 20)), int(round(nn[1] * 20)), int(round(nn[2] * 20)))
        uniq.setdefault(k, nn)

    # Evaluate both n and -n (either could be "up")
    test_dirs: List[Vec3] = []
    for nn in uniq.values():
        test_dirs.append(nn)
        test_dirs.append(v_mul(nn, -1.0))

    up = (0.0, 0.0, 1.0)
    best_R = ((1.0, 0.0, 0.0), (0.0, 1.0, 0.0), (0.0, 0.0, 1.0))
    best_score = -1.0

    eps = 0.01 * radius

    for d in test_dirs:
        R = rotation_from_to(d, up)

        # Compute min z after rotation
        minz = float("inf")
        for t in tris:
            for v in (t.a, t.b, t.c):
                vc = v_sub(v, center)
                vr = mat3_mul_vec(R, vc)
                if vr[2] < minz:
                    minz = vr[2]

        # Support area = sum area of triangles that lie on the bottom plane (within eps)
        support = 0.0
        for t in tris:
            ar = tri_area(t)
            if ar <= 1e-10:
                continue
            vs = []
            for v in (t.a, t.b, t.c):
                vc = v_sub(v, center)
                vr = mat3_mul_vec(R, vc)
                vs.append(vr)
            if max(v[2] for v in vs) <= minz + eps:
                support += ar

        if support > best_score:
            best_score = support
            best_R = R

    return best_R


def project_persp(v: Vec3, f: float) -> Tuple[float, float, float]:
    # v is in camera space; camera looks down -Z
    z = v[2]
    # Prevent blowup if behind camera
    if z > -1e-6:
        z = -1e-6
    x = (v[0] * f) / (-z)
    y = (v[1] * f) / (-z)
    return x, y, z


def blend_rgb(base: Tuple[int, int, int], over: Tuple[int, int, int], a: float) -> Tuple[int, int, int]:
    a = clamp01(a)
    return (
        int(base[0] * (1 - a) + over[0] * a),
        int(base[1] * (1 - a) + over[1] * a),
        int(base[2] * (1 - a) + over[2] * a),
    )


def draw_grid(img: Image.Image, bg_rgb: Tuple[int, int, int], grid_rgb: Tuple[int, int, int], step: int, alpha: float) -> None:
    if step <= 0:
        return
    a = clamp01(alpha)
    if a <= 0:
        return
    w, h = img.size
    pix = img.load()

    col = blend_rgb(bg_rgb, grid_rgb, a)

    for x in range(0, w, step):
        for y in range(h):
            pix[x, y] = col
    for y in range(0, h, step):
        for x in range(w):
            pix[x, y] = col


def draw_line_z(
    img: Image.Image,
    zbuf: List[List[float]],
    p0: Tuple[float, float, float],
    p1: Tuple[float, float, float],
    color: Tuple[int, int, int],
    alpha: float,
) -> None:
    """Draw a 2D line with depth testing (p0/p1 include z in camera space)."""
    a = clamp01(alpha)
    if a <= 0:
        return

    w, h = img.size
    pix = img.load()

    x0, y0, z0 = p0
    x1, y1, z1 = p1

    dx = x1 - x0
    dy = y1 - y0
    steps = int(max(abs(dx), abs(dy)))
    if steps <= 0:
        return

    for i in range(steps + 1):
        t = i / steps
        x = x0 + dx * t
        y = y0 + dy * t
        z = z0 + (z1 - z0) * t
        xi = int(round(x))
        yi = int(round(y))
        if xi < 0 or xi >= w or yi < 0 or yi >= h:
            continue
        if z >= zbuf[yi][xi]:
            continue
        # don't write zbuf; grid is behind objects, but can overlap itself
        pix[xi, yi] = blend_rgb(pix[xi, yi], color, a)


def render(
    stl_path: str,
    out_png: str,
    size: int,
    bg_rgb: Tuple[int, int, int],
    color_rgb: Tuple[int, int, int],
    azim_deg: float,
    elev_deg: float,
    fov_deg: float,
    margin: float,
    light_dir: Vec3,
    grid: bool = False,
    grid_step: int = 80,
    grid_rgb: Tuple[int, int, int] = (42, 49, 58),
    grid_alpha: float = 0.45,
    ground_grid: bool = False,
    ground_step: float = 0.0,
    ground_extent: float = 1.35,
    ground_rgb: Tuple[int, int, int] = (36, 48, 59),
    ground_alpha: float = 0.55,
    axes: bool = False,
    axes_len: float = 0.9,
    two_sided: bool = False,
    auto_upright: bool = True,
) -> None:
    tris = read_stl(stl_path)
    vmin, vmax = bounds(tris)
    center = ((vmin[0] + vmax[0]) / 2, (vmin[1] + vmax[1]) / 2, (vmin[2] + vmax[2]) / 2)
    extent = (vmax[0] - vmin[0], vmax[1] - vmin[1], vmax[2] - vmin[2])
    radius = max(extent) / 2
    if radius <= 1e-9:
        radius = 1.0

    verts, faces, norms = build_vertex_normals(tris)

    # Optional: auto-upright (rotate model so it "stands" on its largest supporting face)
    upright_R = ((1.0, 0.0, 0.0), (0.0, 1.0, 0.0), (0.0, 0.0, 1.0))
    if auto_upright:
        upright_R = auto_upright_rotation(tris, center=center, radius=radius)

    # Camera
    az = math.radians(azim_deg)
    el = math.radians(elev_deg)

    # Put mesh at origin
    v0 = [v_sub(v, center) for v in verts]

    # Auto-upright (pre-rotation in object space)
    v0u = [mat3_mul_vec(upright_R, v) for v in v0]
    n0u = [v_norm(mat3_mul_vec(upright_R, n)) for n in norms]

    # Apply view rotation (object rotation into camera frame)
    v1 = [rot_x(rot_z(v, az), el) for v in v0u]
    n1 = [v_norm(rot_x(rot_z(n, az), el)) for n in n0u]

    # Compute required camera distance to fit within FOV.
    # We approximate by using bounding sphere and focal length.
    fov = math.radians(fov_deg)
    f = 1.0 / math.tan(fov / 2.0)

    # Distance so that radius fits in normalized screen space with margin.
    # For perspective: x_ndc ~= (x*f)/d. Want radius*f/d <= (1 - margin)
    d = (radius * f) / max(1e-6, (1.0 - margin))

    # Translate camera back along +Z in object space, so points are at z=-d ...
    vcam = [(v[0], v[1], v[2] - d) for v in v1]

    # Light
    light = v_norm(light_dir)

    img = Image.new("RGB", (size, size), bg_rgb)
    if grid:
        draw_grid(img, bg_rgb=bg_rgb, grid_rgb=grid_rgb, step=grid_step, alpha=grid_alpha)
    pix = img.load()
    zbuf = [[float("inf")] * size for _ in range(size)]

    # Map NDC [-1,1] to pixel
    def to_px(x: float, y: float) -> Tuple[int, int]:
        px = int((x * 0.5 + 0.5) * (size - 1))
        py = int(((-y) * 0.5 + 0.5) * (size - 1))
        return px, py

    def obj_to_cam(p: Vec3) -> Vec3:
        # object-centered -> upright -> view rotation -> camera translation
        pu = mat3_mul_vec(upright_R, p)
        pr = rot_x(rot_z(pu, az), el)
        return (pr[0], pr[1], pr[2] - d)

    def cam_to_screen(pc: Vec3) -> Tuple[float, float, float]:
        x_ndc, y_ndc, zc = project_persp(pc, f)
        px, py = to_px(x_ndc, y_ndc)
        return float(px), float(py), float(zc)

    # Optional 3D ground-plane grid: draw first, then the mesh will occlude it via zbuf.
    # IMPORTANT: compute the ground plane in the same (auto-uprighted) object frame.
    minz_u = min(v[2] for v in v0u)
    z_plane = minz_u - (0.02 * radius)  # slightly below the model

    if ground_grid:
        ext = radius * float(ground_extent)
        step = float(ground_step) if float(ground_step) > 0 else max(1e-6, (2.0 * ext) / 10.0)

        # draw lines on plane z=z_plane in object-centered coordinates
        x = -ext
        while x <= ext + 1e-9:
            p0 = cam_to_screen(obj_to_cam((x, -ext, z_plane)))
            p1 = cam_to_screen(obj_to_cam((x, ext, z_plane)))
            draw_line_z(img, zbuf, p0, p1, color=ground_rgb, alpha=ground_alpha)
            x += step

        y = -ext
        while y <= ext + 1e-9:
            p0 = cam_to_screen(obj_to_cam((-ext, y, z_plane)))
            p1 = cam_to_screen(obj_to_cam((ext, y, z_plane)))
            draw_line_z(img, zbuf, p0, p1, color=ground_rgb, alpha=ground_alpha)
            y += step

    if axes:
        axis_len = radius * float(axes_len)
        o = (0.0, 0.0, z_plane)
        # X axis (red)
        draw_line_z(img, zbuf, cam_to_screen(obj_to_cam(o)), cam_to_screen(obj_to_cam((axis_len, 0.0, z_plane))), color=(220, 60, 60), alpha=0.95)
        # Y axis (green)
        draw_line_z(img, zbuf, cam_to_screen(obj_to_cam(o)), cam_to_screen(obj_to_cam((0.0, axis_len, z_plane))), color=(60, 200, 120), alpha=0.95)
        # Z axis (blue) -- draw upward from plane
        draw_line_z(img, zbuf, cam_to_screen(obj_to_cam(o)), cam_to_screen(obj_to_cam((0.0, 0.0, z_plane + axis_len))), color=(80, 140, 240), alpha=0.95)

    # For each face, rasterize
    for ia, ib, ic in faces:
        a = vcam[ia]
        b = vcam[ib]
        c = vcam[ic]

        # Backface cull in camera space: compute face normal and check facing.
        # If the STL has inconsistent winding, culling creates "missing" faces.
        if not two_sided:
            fn = v_cross(v_sub(b, a), v_sub(c, a))
            if fn[2] >= 0:  # facing away (camera looks down -Z)
                continue

        ax, ay, azc = project_persp(a, f)
        bx, by, bzc = project_persp(b, f)
        cx, cy, czc = project_persp(c, f)

        # Clip triangles that are wildly off-screen
        if all(x < -2 or x > 2 for x in (ax, bx, cx)) or all(y < -2 or y > 2 for y in (ay, by, cy)):
            continue

        A = to_px(ax, ay)
        B = to_px(bx, by)
        C = to_px(cx, cy)

        minx = max(0, min(A[0], B[0], C[0]))
        maxx = min(size - 1, max(A[0], B[0], C[0]))
        miny = max(0, min(A[1], B[1], C[1]))
        maxy = min(size - 1, max(A[1], B[1], C[1]))
        if minx >= maxx or miny >= maxy:
            continue

        # Barycentric setup
        x0, y0 = A
        x1, y1 = B
        x2, y2 = C
        denom = (y1 - y2) * (x0 - x2) + (x2 - x1) * (y0 - y2)
        if abs(denom) < 1e-12:
            continue

        na = n1[ia]
        nb = n1[ib]
        nc = n1[ic]

        # Depth values: use camera-space z (negative). For z-buffer, smaller is closer (more negative).
        za, zb, zc = azc, bzc, czc

        for py in range(miny, maxy + 1):
            for px in range(minx, maxx + 1):
                w0 = ((y1 - y2) * (px - x2) + (x2 - x1) * (py - y2)) / denom
                w1 = ((y2 - y0) * (px - x2) + (x0 - x2) * (py - y2)) / denom
                w2 = 1.0 - w0 - w1
                if w0 < 0 or w1 < 0 or w2 < 0:
                    continue

                z = w0 * za + w1 * zb + w2 * zc
                if z >= zbuf[py][px]:
                    continue
                zbuf[py][px] = z

                n = v_norm(
                    (
                        w0 * na[0] + w1 * nb[0] + w2 * nc[0],
                        w0 * na[1] + w1 * nb[1] + w2 * nc[1],
                        w0 * na[2] + w1 * nb[2] + w2 * nc[2],
                    )
                )

                # Lambert + ambient
                ndotl = clamp01(v_dot(n, light))
                ambient = 0.20
                diffuse = 0.90 * ndotl
                shade = clamp01(ambient + diffuse)

                r = int(color_rgb[0] * shade)
                g = int(color_rgb[1] * shade)
                bcol = int(color_rgb[2] * shade)
                pix[px, py] = (r, g, bcol)

    os.makedirs(os.path.dirname(out_png) or ".", exist_ok=True)
    img.save(out_png)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--stl", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--size", type=int, default=1024)
    ap.add_argument("--bg", default="#0b0f14")
    ap.add_argument("--color", default="#4cc9f0")
    ap.add_argument("--grid", action="store_true", help="Draw background grid lines (2D screen-space)")
    ap.add_argument("--grid-step", type=int, default=80, help="Grid spacing in pixels")
    ap.add_argument("--grid-color", default="#2a313a", help="Grid line color")
    ap.add_argument("--grid-alpha", type=float, default=0.45, help="Grid opacity 0..1")

    ap.add_argument("--two-sided", action="store_true", help="Disable backface culling (render both sides; safer for inconsistent STL winding)")

    ap.add_argument("--auto-upright", action="store_true", default=True, help="Auto-rotate model to a stable upright orientation (default: on)")
    ap.add_argument("--no-auto-upright", action="store_true", help="Disable auto-upright")

    ap.add_argument("--axes", action="store_true", help="Draw XYZ axes triad at the origin on the ground plane")
    ap.add_argument("--axes-len", type=float, default=0.9, help="Axes length as radius multiplier")

    ap.add_argument("--ground-grid", action="store_true", help="Draw a 3D ground-plane grid under the model (occluded by mesh)")
    ap.add_argument("--ground-step", type=float, default=0.0, help="Ground grid step in model units (0 = auto)")
    ap.add_argument("--ground-extent", type=float, default=1.35, help="Ground grid extent as radius multiplier")
    ap.add_argument("--ground-color", default="#24303b", help="Ground grid color")
    ap.add_argument("--ground-alpha", type=float, default=0.55, help="Ground grid opacity 0..1")
    ap.add_argument("--azim-deg", type=float, default=-35.0)
    ap.add_argument("--elev-deg", type=float, default=-35.0)
    ap.add_argument("--fov-deg", type=float, default=35.0)
    ap.add_argument("--margin", type=float, default=0.08)
    ap.add_argument("--light-dir", default="-0.4,-0.3,1.0")

    args = ap.parse_args()

    render(
        stl_path=args.stl,
        out_png=args.out,
        size=args.size,
        bg_rgb=parse_hex_color(args.bg),
        color_rgb=parse_hex_color(args.color),
        azim_deg=args.azim_deg,
        elev_deg=args.elev_deg,
        fov_deg=args.fov_deg,
        margin=args.margin,
        light_dir=parse_vec3(args.light_dir),
        grid=bool(args.grid),
        grid_step=int(args.grid_step),
        grid_rgb=parse_hex_color(args.grid_color),
        grid_alpha=float(args.grid_alpha),
        ground_grid=bool(args.ground_grid),
        ground_step=float(args.ground_step),
        ground_extent=float(args.ground_extent),
        ground_rgb=parse_hex_color(args.ground_color),
        ground_alpha=float(args.ground_alpha),
        axes=bool(args.axes),
        axes_len=float(args.axes_len),
        two_sided=bool(args.two_sided),
        auto_upright=(False if bool(args.no_auto_upright) else True),
    )


if __name__ == "__main__":
    main()
