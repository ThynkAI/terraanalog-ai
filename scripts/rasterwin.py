"""Raster window utilities: read a window around a point from (remote) rasters and
reproject it onto a local azimuthal-equidistant grid centred on the site, so that
slope/roughness are computed in metres with the same algorithm on Earth, Moon and Mars."""
import math
import numpy as np
import rasterio
from rasterio.windows import from_bounds
from rasterio.warp import reproject, Resampling, transform_bounds
from rasterio.transform import from_origin
from rasterio.crs import CRS

R_EARTH = 6371008.8


def aeqd_crs(lat, lon, radius=None):
    if radius is None:
        return CRS.from_proj4(f"+proj=aeqd +lat_0={lat} +lon_0={lon} +x_0=0 +y_0=0 +datum=WGS84 +units=m +no_defs")
    return CRS.from_proj4(f"+proj=aeqd +lat_0={lat} +lon_0={lon} +x_0=0 +y_0=0 +R={radius} +units=m +no_defs")


def target_grid(half_m, res):
    n = int(round(2 * half_m / res))
    return from_origin(-half_m, half_m, res, res), (n, n)


def warp_sources_to_grid(sources, dst_crs, dst_transform, shape, resampling=Resampling.bilinear,
                         src_crs_override=None, scale=1.0, dtype="float32"):
    """sources: list of open rasterio datasets. Returns float array (NaN = nodata)."""
    out = np.full(shape, np.nan, dtype="float32")
    half = shape[0] * dst_transform.a / 2
    for ds in sources:
        src_crs = src_crs_override or ds.crs
        # bounds of the target grid in source CRS (with margin)
        try:
            b = transform_bounds(dst_crs, src_crs, -half * 1.05, -half * 1.05, half * 1.05, half * 1.05, densify_pts=41)
        except Exception:
            continue
        win = from_bounds(*b, transform=ds.transform).round_offsets().round_lengths()
        win = win.intersection(rasterio.windows.Window(0, 0, ds.width, ds.height)) if _intersects(win, ds) else None
        if win is None or win.width < 2 or win.height < 2:
            continue
        arr = ds.read(1, window=win).astype("float32")
        nd = ds.nodata
        if nd is not None:
            arr[arr == nd] = np.nan
        arr = arr * scale
        tmp = np.full(shape, np.nan, dtype="float32")
        reproject(arr, tmp, src_transform=ds.window_transform(win), src_crs=src_crs, src_nodata=np.nan,
                  dst_transform=dst_transform, dst_crs=dst_crs, dst_nodata=np.nan, resampling=resampling)
        m = np.isnan(out) & ~np.isnan(tmp)
        out[m] = tmp[m]
    return out


def _intersects(win, ds):
    return not (win.col_off >= ds.width or win.row_off >= ds.height or win.col_off + win.width <= 0 or win.row_off + win.height <= 0)


def block_mean(a, k, min_valid=0.5):
    if k == 1:
        return a
    n0 = (a.shape[0] // k) * k
    n1 = (a.shape[1] // k) * k
    b = a[:n0, :n1].reshape(n0 // k, k, n1 // k, k)
    valid = np.sum(~np.isnan(b), axis=(1, 3))
    with np.errstate(invalid="ignore"):
        m = np.nanmean(b, axis=(1, 3)) if np.any(valid) else np.full(valid.shape, np.nan)
    m[valid < min_valid * k * k] = np.nan
    return m


def horn_slope_deg(z, res):
    """Horn (1981) 3x3 slope in degrees; edges and any NaN neighbourhood -> NaN."""
    p = np.pad(z, 1, constant_values=np.nan)
    a, b, c = p[:-2, :-2], p[:-2, 1:-1], p[:-2, 2:]
    d, f = p[1:-1, :-2], p[1:-1, 2:]
    g, h, i = p[2:, :-2], p[2:, 1:-1], p[2:, 2:]
    dzdx = ((c + 2 * f + i) - (a + 2 * d + g)) / (8 * res)
    dzdy = ((g + 2 * h + i) - (a + 2 * b + c)) / (8 * res)
    return np.degrees(np.arctan(np.hypot(dzdx, dzdy)))


def tri_riley(z):
    """Terrain Ruggedness Index (Riley et al. 1999): sqrt of summed squared differences to 8 neighbours (m)."""
    p = np.pad(z, 1, constant_values=np.nan)
    acc = np.zeros_like(z)
    for dy in (0, 1, 2):
        for dx in (0, 1, 2):
            if dy == 1 and dx == 1:
                continue
            acc = acc + (p[dy:dy + z.shape[0], dx:dx + z.shape[1]] - z) ** 2
    return np.sqrt(acc)


def disk_mask(shape, res, radius):
    n = shape[0]
    c = (np.arange(n) + 0.5) * res - n * res / 2
    X, Y = np.meshgrid(c, c)
    return np.hypot(X, Y) <= radius


def terrain_metrics(z, res, radius, prefix):
    """Elevation/slope/roughness statistics inside a disk of `radius` m."""
    m = disk_mask(z.shape, res, radius)
    s = horn_slope_deg(z, res)
    t = tri_riley(z)
    zz, ss, tt = z[m], s[m], t[m]
    zz, ss, tt = zz[~np.isnan(zz)], ss[~np.isnan(ss)], tt[~np.isnan(tt)]
    out = {f"{prefix}_n_valid": int(ss.size), f"{prefix}_valid_fraction": float(ss.size / max(m.sum(), 1))}
    if ss.size < 20:
        for k in ("elev_mean_m", "relief_m", "slope_median_deg", "slope_p90_deg", "slope_frac_lt15", "tri_median_m"):
            out[f"{prefix}_{k}"] = None
        return out
    out.update({f"{prefix}_elev_mean_m": float(np.mean(zz)),
                f"{prefix}_relief_m": float(np.percentile(zz, 99) - np.percentile(zz, 1)),
                f"{prefix}_slope_median_deg": float(np.median(ss)),
                f"{prefix}_slope_p90_deg": float(np.percentile(ss, 90)),
                f"{prefix}_slope_frac_lt15": float(np.mean(ss < 15)),
                f"{prefix}_tri_median_m": float(np.median(tt))})
    return out
