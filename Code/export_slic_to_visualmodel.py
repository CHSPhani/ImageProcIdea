import numpy as np
import json
from skimage.color import rgb2gray
#from scipy import ndimage as ndi

def export_slic_to_visualmodel(image, slic_segments, output_path):
    """
    Export SLIC segmentation result to VisualModel JSON schema.
    Args:
        image: HxWx3 numpy array (RGB)
        slic_segments: HxW numpy array of int labels
        output_path: path to save JSON
    """
    h, w = slic_segments.shape
    objects = []
    label_ids = np.unique(slic_segments)
    label_ids = label_ids[label_ids >= 0]  # Exclude -1 if present
    gray = rgb2gray(image)
    for label in label_ids:
        mask = slic_segments == label
        area = int(np.sum(mask))
        if area == 0:
            continue
        y_idx, x_idx = np.nonzero(mask)
        centroid = [float(np.mean(x_idx)), float(np.mean(y_idx))]
        x_min, x_max = int(np.min(x_idx)), int(np.max(x_idx))
        y_min, y_max = int(np.min(y_idx)), int(np.max(y_idx))
        bbox = [x_min, y_min, x_max, y_max]
        mean_rgb = [float(np.mean(image[..., c][mask])) for c in range(3)]
        mean_intensity = float(np.mean(gray[mask]))
        objects.append({
            "id": int(label),
            "type": "Region",
            "area": area,
            "centroid": centroid,
            "bbox": bbox,
            "mean_rgb": mean_rgb,
            "mean_intensity": mean_intensity
        })
    # Adjacency (8-connected)
    padded = np.pad(slic_segments, 1, mode='edge')
        # Adjacency (4-connected) via label transitions (robust + fast)
    seg = slic_segments
    adj_set = set()

    # Horizontal neighbors: (y, x) vs (y, x+1)
    a = seg[:, :-1]
    b = seg[:, 1:]
    diff = (a != b)
    if np.any(diff):
        pairs = np.stack([a[diff], b[diff]], axis=1)
        for s, d in pairs:
            s = int(s); d = int(d)
            if s == d:
                continue
            if s > d:
                s, d = d, s
            adj_set.add((s, d))

    # Vertical neighbors: (y, x) vs (y+1, x)
    a = seg[:-1, :]
    b = seg[1:, :]
    diff = (a != b)
    if np.any(diff):
        pairs = np.stack([a[diff], b[diff]], axis=1)
        for s, d in pairs:
            s = int(s); d = int(d)
            if s == d:
                continue
            if s > d:
                s, d = d, s
            adj_set.add((s, d))

    relations = [{"type": "adjacent", "src": s, "dst": d} for (s, d) in sorted(adj_set)]
    # adj_set = set()
    # for dy in [-1, 0, 1]:
    #     for dx in [-1, 0, 1]:
    #         if dx == 0 and dy == 0:
    #             continue
    #         shifted = padded[1+dy:h+1+dy, 1+dx:w+1+dx]
    #         mask = (slic_segments != shifted)
    #         src = slic_segments[mask]
    #         dst = shifted[mask]
    #         for s, d in zip(src, dst):
    #             if s != d:
    #                 pair = tuple(sorted((int(s), int(d))))
    #                 adj_set.add(pair)
    # relations = [
    #     {"type": "adjacent", "src": src, "dst": dst}
    #     for src, dst in adj_set
    # ]
    visualmodel = {
        "schema": "svcs.visualmodel.v1",
        "image_width": int(w),
        "image_height": int(h),
        "objects": objects,
        "relations": relations
    }
    with open(output_path, 'w') as f:
        json.dump(visualmodel, f, indent=2)
