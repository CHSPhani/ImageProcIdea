# Standard Segmentation Methods in Computer Vision

This document lists well-known and widely-used image segmentation algorithms for reference.

---

## Superpixel Methods

These methods group pixels into small, uniform regions (superpixels) that respect image boundaries.

### SLIC (Simple Linear Iterative Clustering) - 2010 ✅
- **Status:** Industry standard, very popular
- **Published:** Achanta et al., EPFL Switzerland
- **How it works:** K-means clustering adapted for images (color + spatial proximity)
- **Pros:** Fast, simple, creates compact uniform regions
- **Cons:** Doesn't understand object semantics
- **Used in:** scikit-image, OpenCV
- **Current project:** We use this as baseline

### Felzenszwalb's Graph-Based Segmentation - 2004
- **Published:** Felzenszwalb & Huttenlocher
- **How it works:** Treats image as graph, merges regions based on edge weights
- **Pros:** Preserves boundaries well, adaptive to image structure
- **Cons:** Can create irregular region sizes
- **Used in:** scikit-image

### Quickshift - 2008
- **How it works:** Mode-seeking based on color and space
- **Pros:** Good for natural images
- **Cons:** Slower than SLIC
- **Used in:** scikit-image

### Watershed Transform - 1970s-80s
- **Status:** Classic algorithm
- **How it works:** Treats image as topographic map, finds "watershed" boundaries
- **Pros:** Good for separating touching objects
- **Cons:** Tends to over-segment, sensitive to noise
- **Used in:** OpenCV, scikit-image

---

## Deep Learning Methods (Modern AI-Based)

These use neural networks trained on large datasets. Very powerful but require GPU and training data.

### Mask R-CNN - 2017
- **Published:** Facebook AI Research (FAIR)
- **Task:** Instance segmentation (identifies and segments each individual object)
- **Pros:** Very accurate, understands object classes
- **Cons:** Slow, requires GPU, needs trained model
- **Use case:** Object detection + segmentation

### U-Net - 2015
- **Published:** Ronneberger et al.
- **Task:** Semantic segmentation (pixel-level classification)
- **Pros:** Excellent for medical images, works with small datasets
- **Cons:** Requires training
- **Use case:** Medical imaging, biomedical applications

### DeepLab - 2017
- **Published:** Google Research
- **Task:** Semantic segmentation
- **Pros:** State-of-the-art accuracy, handles multiple scales
- **Cons:** Computationally expensive
- **Use case:** Scene understanding, autonomous vehicles

### SAM (Segment Anything Model) - 2023
- **Published:** Meta AI
- **Task:** Universal segmentation (anything in any image)
- **Pros:** Zero-shot learning, works on any image without training
- **Cons:** Very large model, requires significant GPU
- **Status:** Current state-of-the-art
- **Use case:** General-purpose segmentation

---

## Classic Clustering-Based Methods

### Mean Shift - 1995
- **How it works:** Iteratively shifts points to modes of density distribution
- **Pros:** Doesn't require number of clusters upfront
- **Cons:** Slow, sensitive to bandwidth parameter
- **Used in:** OpenCV

### K-means Clustering
- **Status:** Very basic, from 1950s-60s
- **How it works:** Groups pixels into K clusters by color
- **Pros:** Simple, fast
- **Cons:** Ignores spatial relationships, requires K upfront
- **Use case:** Color quantization

### Graph Cuts - 2001
- **Published:** Boykov & Jolly
- **How it works:** Energy minimization on image graph
- **Pros:** Global optimization
- **Cons:** Computationally expensive
- **Use case:** Interactive segmentation

### GrabCut - 2004
- **Published:** Microsoft Research
- **How it works:** Interactive foreground/background separation using graph cuts
- **Pros:** User-friendly, good results with minimal input
- **Cons:** Requires user interaction
- **Used in:** OpenCV, Photoshop-like tools

---

## Edge-Based Methods

These find boundaries/edges and use them to define regions.

### Canny Edge Detection - 1986 ✅
- **Published:** John Canny
- **Status:** Gold standard for edge detection
- **How it works:** Multi-stage algorithm (smoothing, gradient, non-max suppression, hysteresis)
- **Used in:** OpenCV, everywhere
- **Current project:** Used in our "Brick Boundaries" method

### Sobel/Prewitt Operators
- **Status:** Classic edge detectors (1960s-70s)
- **How it works:** Gradient-based edge detection
- **Pros:** Simple, fast
- **Cons:** Sensitive to noise

### Contour Finding
- **How it works:** Traces boundaries after edge detection
- **Used in:** OpenCV (findContours)
- **Current project:** Used in our "Brick Boundaries" method

---

## Comparison Summary

| Method | Year | Type | Speed | Accuracy | Use Case |
|--------|------|------|-------|----------|----------|
| **SLIC** | 2010 | Superpixel | Fast | Good | General purpose |
| **Felzenszwalb** | 2004 | Graph | Medium | Good | Boundary preservation |
| **Watershed** | 1970s | Region growing | Fast | Variable | Separating objects |
| **Mean Shift** | 1995 | Clustering | Slow | Good | Mode detection |
| **K-means** | 1950s | Clustering | Fast | Basic | Color segmentation |
| **Canny** | 1986 | Edge | Fast | Excellent | Edge detection |
| **GrabCut** | 2004 | Interactive | Medium | Good | User-guided |
| **U-Net** | 2015 | Deep Learning | Slow (GPU) | Excellent | Medical images |
| **Mask R-CNN** | 2017 | Deep Learning | Slow (GPU) | Excellent | Object instances |
| **DeepLab** | 2017 | Deep Learning | Slow (GPU) | Excellent | Scene segmentation |
| **SAM** | 2023 | Deep Learning | Slow (GPU) | State-of-art | Universal |

---

## Most Popular Today (2026)

**Traditional Methods:**
1. **SLIC** - Default choice for superpixels
2. **Felzenszwalb** - When boundary quality matters
3. **Watershed** - For separating touching objects
4. **Canny + Contours** - For structured patterns

**AI Methods:**
1. **SAM (Segment Anything)** - Universal segmentation
2. **Mask R-CNN** - Instance segmentation
3. **U-Net** - Biomedical applications

---

## What We're Using in This Project

**Implemented:**
- ✅ **SLIC** (standard) - Baseline superpixel segmentation
- 🔧 **Brick Boundaries** (custom using Canny + morphology)
- 🧪 **Mortar Based** (custom thresholding experiment)

**Could Add:**
- Felzenszwalb (standard, easy to add)
- Watershed (standard, already imported)
- SAM (state-of-the-art, but needs GPU setup)

---

## References

- **SLIC:** Achanta et al. "SLIC Superpixels Compared to State-of-the-Art Superpixel Methods" (2012)
- **Felzenszwalb:** "Efficient Graph-Based Image Segmentation" (2004)
- **Watershed:** Beucher & Lantuéjoul (1979), Meyer (1991)
- **Canny:** "A Computational Approach to Edge Detection" (1986)
- **Mean Shift:** Comaniciu & Meer (2002)
- **GrabCut:** Rother et al. (2004)
- **U-Net:** Ronneberger et al. (2015)
- **Mask R-CNN:** He et al. (2017)
- **SAM:** Kirillov et al., Meta AI (2023)

---

*This document serves as a reference for standard segmentation methods in computer vision. Our project currently uses SLIC as the baseline with custom edge-based methods for comparison.*
