"""
Image Segmentation to Graph Coloring Pipeline
Segments an image into regions and applies graph coloring
"""

import cv2
import numpy as np
import matplotlib
matplotlib.use('Agg')  # headless: this pipeline saves figures to disk, no interactive display needed
import matplotlib.pyplot as plt
from skimage import segmentation, color
from skimage import graph
import networkx as nx
from pathlib import Path


class ImageSegmentColorizer:
    """Main class for image segmentation and graph coloring"""
    
    def __init__(self, image_path):
        """Initialize with image path"""
        self.image_path = Path(image_path)
        self.original_image = None
        self.preprocessed_image = None
        self.segments = None
        self.rag = None
        self.coloring = None
        self.colored_image = None
        
    def load_and_preprocess(self, target_size=None, blur_kernel=5):
        """
        Load image and apply preprocessing
        
        Args:
            target_size: (width, height) tuple to resize, or None
            blur_kernel: Gaussian blur kernel size (odd number)
        """
        print(f"Loading image: {self.image_path}")
        self.original_image = cv2.imread(str(self.image_path))
        
        if self.original_image is None:
            raise ValueError(f"Could not load image: {self.image_path}")
        
        # Convert BGR to RGB for display
        self.original_image = cv2.cvtColor(self.original_image, cv2.COLOR_BGR2RGB)
        
        # Resize if requested
        if target_size:
            self.preprocessed_image = cv2.resize(
                self.original_image, target_size, interpolation=cv2.INTER_AREA
            )
        else:
            self.preprocessed_image = self.original_image.copy()
        
        # Apply Gaussian blur to reduce noise
        self.preprocessed_image = cv2.GaussianBlur(
            self.preprocessed_image, (blur_kernel, blur_kernel), 0
        )
        
        print(f"Image loaded: {self.preprocessed_image.shape}")
        return self.preprocessed_image
    
    def segment_slic(self, n_segments=100, compactness=30):
        """
        Segment image using SLIC superpixels
        
        Args:
            n_segments: Approximate number of segments
            compactness: Balance between color and space proximity
        """
        print(f"Segmenting with SLIC (n_segments={n_segments})...")
        self.segments = segmentation.slic(
            self.preprocessed_image,
            n_segments=n_segments,
            compactness=compactness,
            start_label=0
        )
        
        n_regions = len(np.unique(self.segments))
        print(f"Created {n_regions} regions")
        # Export SLIC segmentation to VisualModel JSON
        try:
            from .export_slic_to_visualmodel import export_slic_to_visualmodel
        except ImportError:
            from export_slic_to_visualmodel import export_slic_to_visualmodel
        import os
        output_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'JSONs')
        os.makedirs(output_dir, exist_ok=True)
        # Use the original image filename (without extension) for the JSON filename
        image_stem = self.image_path.stem
        output_path = os.path.join(output_dir, f'{image_stem}.json')
        export_slic_to_visualmodel(self.preprocessed_image, self.segments, output_path)
        print(f"VisualModel JSON exported to: {output_path}")
        return self.segments
    
    def segment_watershed(self, markers=100):
        """
        Segment image using Watershed algorithm
        
        Args:
            markers: Number of markers (seed points)
        """
        print(f"Segmenting with Watershed (markers={markers})...")
        
        # Convert to grayscale for gradient
        gray = cv2.cvtColor(self.preprocessed_image, cv2.COLOR_RGB2GRAY)
        
        # Calculate gradient
        gradient = cv2.morphologyEx(
            gray, cv2.MORPH_GRADIENT, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
        )
        
        # Create markers using distance transform
        _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        kernel = np.ones((3, 3), np.uint8)
        opening = cv2.morphologyEx(thresh, cv2.MORPH_OPEN, kernel, iterations=2)
        
        # Dilate to get background
        sure_bg = cv2.dilate(opening, kernel, iterations=3)
        
        # Distance transform for foreground
        dist_transform = cv2.distanceTransform(opening, cv2.DIST_L2, 5)
        _, sure_fg = cv2.threshold(dist_transform, 0.5 * dist_transform.max(), 255, 0)
        
        # Unknown region
        sure_fg = np.uint8(sure_fg)
        unknown = cv2.subtract(sure_bg, sure_fg)
        
        # Label markers
        _, markers_labeled = cv2.connectedComponents(sure_fg)
        markers_labeled = markers_labeled + 1
        markers_labeled[unknown == 255] = 0
        
        # Apply watershed
        temp_image = self.preprocessed_image.copy()
        markers_result = cv2.watershed(temp_image, markers_labeled)
        
        self.segments = markers_result
        
        n_regions = len(np.unique(self.segments[self.segments > 0]))
        print(f"Created {n_regions} regions")
        return self.segments
    
    def segment_brick_boundaries(self, edge_threshold1=30, edge_threshold2=100, 
                                  morph_kernel_size=3, min_area=50):
        """
        Segment image using edge detection focused on brick boundaries (mortar lines)
        
        Args:
            edge_threshold1: Lower threshold for Canny edge detection
            edge_threshold2: Upper threshold for Canny edge detection
            morph_kernel_size: Size of morphological operations kernel
            min_area: Minimum area for a region to be considered
        """
        print(f"Segmenting with brick boundary detection...")
        
        # Convert to grayscale
        gray = cv2.cvtColor(self.preprocessed_image, cv2.COLOR_RGB2GRAY)
        
        # Apply bilateral filter to reduce noise while preserving edges
        bilateral = cv2.bilateralFilter(gray, 9, 75, 75)
        
        # Detect edges using Canny
        edges = cv2.Canny(bilateral, edge_threshold1, edge_threshold2)
        
        # Dilate edges to close gaps in brick boundaries
        kernel = np.ones((morph_kernel_size, morph_kernel_size), np.uint8)
        dilated = cv2.dilate(edges, kernel, iterations=2)
        
        # Close gaps
        closed = cv2.morphologyEx(dilated, cv2.MORPH_CLOSE, kernel, iterations=2)
        
        # Find contours
        contours, _ = cv2.findContours(closed, cv2.RETR_CCOMP, cv2.CHAIN_APPROX_SIMPLE)
        
        # Create labeled image
        self.segments = np.zeros(gray.shape, dtype=np.int32)
        
        # Fill regions between edges
        label = 1
        for i, contour in enumerate(contours):
            area = cv2.contourArea(contour)
            if area > min_area:
                cv2.drawContours(self.segments, [contour], -1, label, -1)
                label += 1
        
        # Fill unlabeled regions using watershed
        if np.any(self.segments == 0):
            # Use distance transform on unlabeled areas
            mask = (self.segments == 0).astype(np.uint8)
            dist_transform = cv2.distanceTransform(mask, cv2.DIST_L2, 5)
            
            # Find local maxima as markers
            _, sure_fg = cv2.threshold(dist_transform, 0.3 * dist_transform.max(), 255, 0)
            sure_fg = np.uint8(sure_fg)
            
            # Get markers from sure foreground
            _, markers = cv2.connectedComponents(sure_fg)
            markers = markers + label  # Start from next available label
            markers[self.segments > 0] = self.segments[self.segments > 0]
            
            # Apply watershed
            temp_image = cv2.cvtColor(self.preprocessed_image, cv2.COLOR_RGB2BGR)
            markers = cv2.watershed(temp_image, markers)
            self.segments = markers
        
        # Clean up: remove boundary markers (-1) and background (0)
        self.segments[self.segments == -1] = 0
        
        # Relabel segments consecutively
        unique_labels = np.unique(self.segments)
        unique_labels = unique_labels[unique_labels > 0]  # Remove 0
        label_map = {old: new for new, old in enumerate(unique_labels, start=1)}
        
        temp_segments = np.zeros_like(self.segments)
        for old_label, new_label in label_map.items():
            temp_segments[self.segments == old_label] = new_label
        self.segments = temp_segments
        
        n_regions = len(np.unique(self.segments)) - 1  # Exclude background
        print(f"Created {n_regions} regions")
        return self.segments
    
    def segment_mortar_based(self, mortar_threshold_percentile=20, min_brick_area=100):
        """
        Segment bricks by detecting dark mortar lines
        
        Args:
            mortar_threshold_percentile: Percentile for mortar darkness threshold
            min_brick_area: Minimum area for a brick region
        """
        print(f"Segmenting using mortar line detection...")
        
        # Convert to grayscale
        gray = cv2.cvtColor(self.preprocessed_image, cv2.COLOR_RGB2GRAY)
        
        # Apply strong Gaussian blur to remove brick texture
        blurred = cv2.GaussianBlur(gray, (11, 11), 0)
        
        # Threshold to find dark mortar lines
        threshold_value = np.percentile(blurred, mortar_threshold_percentile)
        _, mortar_mask = cv2.threshold(blurred, threshold_value, 255, cv2.THRESH_BINARY)
        
        # Invert so mortar is white (foreground)
        mortar_mask = cv2.bitwise_not(mortar_mask)
        
        # Clean up mortar lines
        kernel = np.ones((3, 3), np.uint8)
        mortar_clean = cv2.morphologyEx(mortar_mask, cv2.MORPH_CLOSE, kernel, iterations=2)
        mortar_clean = cv2.morphologyEx(mortar_clean, cv2.MORPH_OPEN, kernel, iterations=1)
        
        # Dilate mortar lines slightly to ensure separation
        mortar_dilated = cv2.dilate(mortar_clean, kernel, iterations=2)
        
        # Find brick regions (inverse of mortar)
        brick_mask = cv2.bitwise_not(mortar_dilated)
        
        # Label connected components as individual bricks
        n_labels, labels = cv2.connectedComponents(brick_mask)
        
        # Filter small regions
        self.segments = np.zeros_like(labels)
        new_label = 1
        for label_id in range(1, n_labels):
            mask = (labels == label_id)
            area = np.sum(mask)
            if area >= min_brick_area:
                self.segments[mask] = new_label
                new_label += 1
        
        n_regions = new_label - 1
        print(f"Created {n_regions} regions (bricks)")
        return self.segments
    
    def build_rag(self):
        """Build Region Adjacency Graph from segments"""
        print("Building Region Adjacency Graph...")
        
        # Create RAG with mean color of regions
        self.rag = graph.rag_mean_color(
            self.preprocessed_image, self.segments, mode='similarity'
        )
        
        print(f"RAG created: {self.rag.number_of_nodes()} nodes, "
              f"{self.rag.number_of_edges()} edges")
        return self.rag
    
    def apply_graph_coloring(self):
        """Apply greedy graph coloring algorithm"""
        print("Applying graph coloring...")
        
        # Use NetworkX greedy coloring
        self.coloring = nx.greedy_color(self.rag, strategy='largest_first')
        
        n_colors = len(set(self.coloring.values()))
        print(f"Graph colored with {n_colors} colors")
        
        return self.coloring
    
    def create_colored_image(self):
        """Create image with regions colored by graph coloring"""
        print("Creating colored output image...")
        
        # Define distinct colors for visualization
        color_palette = [
            [255, 0, 0],      # Red
            [0, 255, 0],      # Green
            [0, 0, 255],      # Blue
            [255, 255, 0],    # Yellow
            [255, 0, 255],    # Magenta
            [0, 255, 255],    # Cyan
            [255, 128, 0],    # Orange
            [128, 0, 255],    # Purple
            [0, 255, 128],    # Spring Green
            [255, 0, 128],    # Rose
        ]
        
        # Create output image
        self.colored_image = np.zeros_like(self.preprocessed_image)
        
        # Map each segment to its color
        for segment_id in np.unique(self.segments):
            if segment_id == -1 or segment_id == 0:  # Skip background/borders
                continue
            
            color_idx = self.coloring.get(segment_id, 0)
            mask = self.segments == segment_id
            self.colored_image[mask] = color_palette[color_idx % len(color_palette)]
        
        return self.colored_image
    
    def visualize_results(self, save_path=None):
        """Display all results in a grid"""
        fig, axes = plt.subplots(2, 3, figsize=(15, 10))
        
        # Original image
        axes[0, 0].imshow(self.original_image)
        axes[0, 0].set_title('Original Image')
        axes[0, 0].axis('off')
        
        # Preprocessed image
        axes[0, 1].imshow(self.preprocessed_image)
        axes[0, 1].set_title('Preprocessed Image')
        axes[0, 1].axis('off')
        
        # Segmentation boundaries
        boundaries = segmentation.mark_boundaries(
            self.preprocessed_image, self.segments, color=(1, 1, 1)
        )
        axes[0, 2].imshow(boundaries)
        axes[0, 2].set_title(f'Segments ({len(np.unique(self.segments))} regions)')
        axes[0, 2].axis('off')
        
        # Segment labels visualization
        axes[1, 0].imshow(color.label2rgb(self.segments, self.preprocessed_image, kind='avg'))
        axes[1, 0].set_title('Segment Colors')
        axes[1, 0].axis('off')
        
        # Graph coloring result
        axes[1, 1].imshow(self.colored_image)
        axes[1, 1].set_title(f'Graph Coloring ({len(set(self.coloring.values()))} colors)')
        axes[1, 1].axis('off')
        
        # Graph structure visualization (THE HEART OF THE PROJECT!)
        axes[1, 2].axis('off')
        if self.rag.number_of_nodes() < 200:  # Only show for small graphs
            pos = {}
            for node in self.rag.nodes():
                # Get region centroid for positioning
                mask = self.segments == node
                if np.any(mask):
                    y, x = np.where(mask)
                    pos[node] = (np.mean(x), -np.mean(y))  # Negative y for correct orientation
            
            node_colors = [self.coloring.get(node, 0) for node in self.rag.nodes()]
            nx.draw(self.rag, pos, node_color=node_colors, node_size=10, 
                   ax=axes[1, 2], with_labels=False, cmap=plt.cm.Set1)
            axes[1, 2].set_title('Region Adjacency Graph')
        else:
            axes[1, 2].text(0.5, 0.5, f'Graph too large to display\n({self.rag.number_of_nodes()} nodes)',
                           ha='center', va='center', fontsize=12)
            axes[1, 2].set_title('Region Adjacency Graph')
        
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, dpi=150, bbox_inches='tight')
            print(f"Results saved to: {save_path}")
        
        plt.show()
    
    def visualize_graph_only(self, save_path=None, figsize=(12, 12)):
        """
        Create a detailed standalone visualization of the Region Adjacency Graph
        This is the CORE of the project - showing how regions connect to each other
        """
        fig, axes = plt.subplots(1, 2, figsize=figsize)
        
        # Get node positions based on region centroids
        pos = {}
        for node in self.rag.nodes():
            mask = self.segments == node
            if np.any(mask):
                y, x = np.where(mask)
                pos[node] = (np.mean(x), -np.mean(y))
        
        # Left: Graph with colored nodes matching the graph coloring
        node_colors = [self.coloring.get(node, 0) for node in self.rag.nodes()]
        
        # Draw graph with thicker edges and larger nodes for visibility
        nx.draw(self.rag, pos, 
               node_color=node_colors, 
               node_size=30,
               edge_color='gray',
               width=0.8,
               alpha=0.8,
               ax=axes[0], 
               with_labels=False, 
               cmap=plt.cm.Set1)
        
        axes[0].set_title(f'Region Adjacency Graph\n{self.rag.number_of_nodes()} nodes, '
                         f'{self.rag.number_of_edges()} edges\n'
                         f'{len(set(self.coloring.values()))} colors needed', 
                         fontsize=12, fontweight='bold')
        
        # Right: Show the colored image for comparison
        axes[1].imshow(self.colored_image)
        axes[1].set_title('Corresponding Colored Regions', fontsize=12, fontweight='bold')
        axes[1].axis('off')
        
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, dpi=150, bbox_inches='tight')
            print(f"Graph visualization saved to: {save_path}")
        
        plt.show()
    
    def get_statistics(self):
        """Return statistics about the segmentation and coloring"""
        stats = {
            'image_size': self.original_image.shape,
            'n_regions': len(np.unique(self.segments)),
            'n_edges': self.rag.number_of_edges(),
            'n_colors': len(set(self.coloring.values())),
            'avg_degree': sum(dict(self.rag.degree()).values()) / self.rag.number_of_nodes(),
        }
        return stats
    
    def process_pipeline(self, method='slic', **kwargs):
        """
        Run the complete pipeline
        
        Args:
            method: 'slic', 'watershed', 'brick_boundaries', or 'mortar_based'
            **kwargs: Additional arguments for segmentation
        """
        self.load_and_preprocess()
        
        if method == 'slic':
            self.segment_slic(**kwargs)
        elif method == 'watershed':
            self.segment_watershed(**kwargs)
        elif method == 'brick_boundaries':
            self.segment_brick_boundaries(**kwargs)
        elif method == 'mortar_based':
            self.segment_mortar_based(**kwargs)
        else:
            raise ValueError(f"Unknown method: {method}")
        
        self.build_rag()
        self.apply_graph_coloring()
        self.create_colored_image()
        
        return self.colored_image


def compare_methods(image_path, methods_config, output_name):
    """
    Compare different segmentation methods on the same image
    
    Args:
        image_path: Path to image file
        methods_config: List of (method_name, params_dict) tuples
        output_name: Base name for output file
    """
    results = []
    
    for method_name, params in methods_config:
        print("\n" + "=" * 60)
        print(f"Method: {method_name.upper()}")
        print("=" * 60)
        
        processor = ImageSegmentColorizer(image_path)
        processor.process_pipeline(method=method_name, **params)
        
        stats = processor.get_statistics()
        print(f"\nStatistics for {method_name}:")
        for key, value in stats.items():
            print(f"  {key}: {value}")
        
        results.append({
            'method': method_name,
            'processor': processor,
            'stats': stats
        })
    
    # Create comparison visualization
    n_methods = len(results)
    fig, axes = plt.subplots(n_methods, 3, figsize=(18, 6 * n_methods))
    
    if n_methods == 1:
        axes = axes.reshape(1, -1)
    
    for i, result in enumerate(results):
        processor = result['processor']
        method = result['method']
        stats = result['stats']
        
        # Original/Method name (first column)
        axes[i, 0].imshow(processor.original_image)
        axes[i, 0].set_title(f'Method: {method.upper()}', fontsize=12, fontweight='bold')
        axes[i, 0].axis('off')
        
        # Segmentation with boundaries (second column)
        boundaries = segmentation.mark_boundaries(
            processor.preprocessed_image, processor.segments, color=(1, 1, 0), mode='thick'
        )
        axes[i, 1].imshow(boundaries)
        axes[i, 1].set_title(f'Segments: {stats["n_regions"]} regions', fontsize=12)
        axes[i, 1].axis('off')
        
        # Colored result (third column)
        axes[i, 2].imshow(processor.colored_image)
        axes[i, 2].set_title(f'Graph Coloring: {stats["n_colors"]} colors', fontsize=12)
        axes[i, 2].axis('off')
    
    plt.tight_layout()
    output_path = f'../results/comparison_{output_name}.png'
    plt.savefig(output_path, dpi=150, bbox_inches='tight')
    print(f"\n\nComparison saved to: {output_path}")
    plt.show()
    
    # Print summary
    print("\n" + "=" * 60)
    print("SUMMARY COMPARISON")
    print("=" * 60)
    for result in results:
        method = result['method']
        stats = result['stats']
        print(f"\n{method.upper()}:")
        print(f"  Regions: {stats['n_regions']}")
        print(f"  Colors needed: {stats['n_colors']}")
        print(f"  Avg neighbors: {stats['avg_degree']:.2f}")
    
    return results


def comprehensive_visualization(image_path):
    """
    Create ONE comprehensive visualization showing all methods with their graphs
    
    Args:
        image_path: Path to image file
    """
    # Extract filename without extension from image path
    output_name = Path(image_path).stem
    
    print("=" * 60)
    print(f"COMPREHENSIVE ANALYSIS: {output_name.upper()}")
    print("=" * 60)
    
    # Define methods to compare
    methods = [
        ('SLIC', 'slic', {'n_segments': 150, 'compactness': 10}),
        ('Brick Boundaries', 'brick_boundaries', {
            'edge_threshold1': 20,
            'edge_threshold2': 60,
            'morph_kernel_size': 2,
            'min_area': 20
        }),
        ('Mortar Based', 'mortar_based', {
            'mortar_threshold_percentile': 15,
            'min_brick_area': 80
        }),
    ]
    
    results = []
    
    # Process each method
    for display_name, method_name, params in methods:
        print(f"\nProcessing: {display_name}...")
        processor = ImageSegmentColorizer(image_path)
        processor.process_pipeline(method=method_name, **params)
        
        stats = processor.get_statistics()
        print(f"  Regions: {stats['n_regions']}, Colors: {stats['n_colors']}, Edges: {stats['n_edges']}")
        
        results.append({
            'name': display_name,
            'processor': processor,
            'stats': stats
        })
    
    # Create comprehensive visualization
    fig = plt.figure(figsize=(20, 15))
    gs = fig.add_gridspec(3, 4, hspace=0.3, wspace=0.3)
    
    for i, result in enumerate(results):
        processor = result['processor']
        name = result['name']
        stats = result['stats']
        
        # Column 1: Original with method name
        ax1 = fig.add_subplot(gs[i, 0])
        ax1.imshow(processor.original_image)
        ax1.set_title(f'{name}\n({stats["n_regions"]} regions)', fontsize=11, fontweight='bold')
        ax1.axis('off')
        
        # Column 2: Segmentation boundaries
        ax2 = fig.add_subplot(gs[i, 1])
        boundaries = segmentation.mark_boundaries(
            processor.preprocessed_image, processor.segments, color=(1, 1, 0), mode='thick'
        )
        ax2.imshow(boundaries)
        ax2.set_title(f'Segmented Regions', fontsize=11)
        ax2.axis('off')
        
        # Column 3: Graph colored result
        ax3 = fig.add_subplot(gs[i, 2])
        ax3.imshow(processor.colored_image)
        ax3.set_title(f'{stats["n_colors"]} Colors Used', fontsize=11)
        ax3.axis('off')
        
        # Column 4: Adjacency Graph
        ax4 = fig.add_subplot(gs[i, 3])
        
        # Get node positions from centroids
        pos = {}
        for node in processor.rag.nodes():
            mask = processor.segments == node
            if np.any(mask):
                y, x = np.where(mask)
                pos[node] = (np.mean(x), -np.mean(y))
        
        # Get node colors from graph coloring
        node_colors = [processor.coloring.get(node, 0) for node in processor.rag.nodes()]
        
        # Draw graph with small dot-like nodes
        nx.draw(processor.rag, pos,
               node_color=node_colors,
               node_size=20,
               edge_color='gray',
               width=0.5,
               alpha=0.8,
               ax=ax4,
               with_labels=False,
               cmap=plt.cm.Set1)
        
        ax4.set_title(f'Region Adjacency Graph\n{stats["n_edges"]} edges', fontsize=11)
        ax4.set_aspect('equal')
    
    # Overall title
    fig.suptitle(f'Complete Analysis: {output_name.upper()}', fontsize=16, fontweight='bold')
    
    # Save
    results_dir = Path(__file__).resolve().parent.parent / 'results'
    results_dir.mkdir(parents=True, exist_ok=True)
    output_path = str(results_dir / f'{output_name}_complete.png')
    plt.savefig(output_path, dpi=150, bbox_inches='tight')
    print(f"\n{'='*60}")
    print(f"Complete visualization saved to: {output_path}")
    print(f"{'='*60}\n")
    plt.close(fig)


def main():
    """Main execution function"""
    
    # Generate comprehensive visualization
    comprehensive_visualization('../input_images/Original_Dest.png')


if __name__ == '__main__':
    main()
