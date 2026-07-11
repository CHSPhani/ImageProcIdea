# Segmentation Methods Explained

## Are These Standard Methods?

**Yes and No:**

### SLIC - YES, Very Standard
- **Full name:** Simple Linear Iterative Clustering
- **Published:** 2010 by Achanta et al. (EPFL Switzerland)
- **Status:** Industry standard for superpixel segmentation
- **Used in:** Image processing libraries (scikit-image, OpenCV)
- **Purpose:** Creates uniform regions (superpixels) for efficient image analysis

### Brick Boundaries - Custom Implementation
- **Based on:** Standard techniques (Canny edge detection + morphology)
- **Status:** Custom combination created for this project
- **Uses standard tools:**
  - Canny edge detection (1986, John Canny - very standard)
  - Morphological operations (erosion, dilation - standard)
  - Contour finding (standard in OpenCV)
- **Purpose:** Adapted specifically to find brick/object boundaries

### Mortar Based - Custom Implementation
- **Based on:** Thresholding (very basic, standard technique)
- **Status:** Simple custom approach created for this project
- **Uses:** Basic image thresholding + connected components
- **Purpose:** Experimental approach to detect bricks by finding dark mortar lines

---

## Method Details

### 1. SLIC (Standard Method) ✅

**What it does:**
- Groups similar colored pixels that are nearby into "superpixels"
- Like K-means clustering but considers both color AND position

**How it works:**
1. Initialize grid of cluster centers across the image
2. Assign each pixel to nearest cluster (by color + distance)
3. Update cluster centers
4. Repeat until convergence

**Pros:**
- Fast and efficient
- Creates uniform, compact regions
- Works on any image

**Cons:**
- Doesn't understand object boundaries
- May split single objects into multiple regions
- Sensitive to texture variations

**Parameters:**
- `n_segments`: How many regions to create (~150 for brick wall)
- `compactness`: Balance between color similarity vs spatial proximity

---

### 2. Brick Boundaries (Custom - Using Standard Techniques) 🔧

**What it does:**
- Finds edges (sharp changes in brightness)
- Treats regions between edges as separate objects

**How it works:**
1. **Bilateral filter:** Smooth image while keeping edges sharp
2. **Canny edge detection:** Find edges where brightness changes
3. **Morphological operations:** Close gaps in detected edges
4. **Contour finding:** Identify enclosed regions
5. **Watershed:** Fill any unlabeled areas

**Standard techniques used:**
- **Canny Edge Detection** (1986) - Standard algorithm
- **Bilateral Filter** - Standard denoising
- **Morphological Operations** - Standard image processing
- **Watershed Algorithm** - Standard for region separation

**Pros:**
- Follows actual object boundaries
- Good for structured patterns (bricks, tiles)
- More accurate for objects with clear edges

**Cons:**
- Sensitive to noise
- May miss edges if mortar is light
- Requires parameter tuning

**Parameters:**
- `edge_threshold1/2`: Sensitivity of edge detection (lower = more sensitive)
- `morph_kernel_size`: Size of smoothing operations
- `min_area`: Filter out tiny regions

---

### 3. Mortar Based (Custom - Experimental) 🧪

**What it does:**
- Assumes dark pixels = mortar (gaps between bricks)
- Everything else = bricks

**How it works:**
1. **Gaussian blur:** Remove brick texture, keep large features
2. **Percentile thresholding:** Find darkest pixels (mortar)
3. **Morphology:** Clean up detected mortar lines
4. **Connected components:** Label each brick region

**Based on:**
- **Thresholding** - Very basic, standard technique from 1970s
- **Connected components** - Standard algorithm

**Pros:**
- Simple concept
- Fast

**Cons:**
- Too aggressive for real images
- Assumes mortar is much darker than bricks
- Doesn't work if bricks have similar brightness to mortar
- Failed on test image (merged most bricks)

**Parameters:**
- `mortar_threshold_percentile`: What percentage of darkest pixels are "mortar"
- `min_brick_area`: Minimum size for a brick

---

## Summary: Standard vs Custom

| Method | Status | Based On |
|--------|--------|----------|
| **SLIC** | ✅ Standard, widely used | Published algorithm (2010) |
| **Brick Boundaries** | 🔧 Custom combination | Standard techniques (Canny, morphology) |
| **Mortar Based** | 🧪 Experimental | Basic thresholding |

**For this project:**
- **SLIC** is the "safe" standard method
- **Brick Boundaries** is a custom approach using standard tools (created for this project)
- **Mortar Based** is a simple experiment (didn't work well)

---

## Which Method Won?

**For Brick Wall:**
- 🥇 **Brick Boundaries** (61 regions, 3 colors) - Best balance
- 🥈 SLIC (118 regions, 5 colors) - Too detailed
- 🥉 Mortar Based (2 regions, 2 colors) - Failed

The custom "Brick Boundaries" approach outperformed the standard SLIC method for brick images because it understands edges/boundaries rather than just color similarity.

---

## Generated Files in This Folder

**brickwall_complete.png** - Complete analysis showing all three methods:
- Row 1: SLIC results
- Row 2: Brick Boundaries results  
- Row 3: Mortar Based results
- Each row shows: Original | Segmented | Colored | Adjacency Graph

The adjacency graph (rightmost column) shows how regions connect to each other - this is the core concept of the project!
