import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from scipy.spatial import ConvexHull
from sklearn.cluster import DBSCAN
from sklearn.decomposition import PCA
import numpy as np
import json

with open("deposition_points.json", "r") as f:
    deposition_points = json.load(f)

def compute_obb_features(points):
    centroid = np.mean(points, axis= 0)
    
    centered = points - centroid

    pca = PCA(n_components= 2)
    pca.fit(centered)

    # Project points onto the principal axes
    projected = pca.transform(centered)

    min_proj = np.min(projected, axis =0)
    max_proj = np.max(projected, axis =0)
    dims = max_proj - min_proj
    length = max(dims)
    width = min(dims)
    diagonal = np.sqrt(np.sum(dims**2))

    return {'centroid': centroid, 'length': length, 'width': width, 'diagonal': diagonal, 'dims': dims}


def process_deposition_points(deposition_points, layer_height=1, eps=40, min_samples=5):
    """
    Process deposition points to group into layers and clusters and compute geometric features.
    
    Parameters:
        deposition_points: List of tuples (x, y, z)
        layer_height: Nominal height of each layer.
        eps: DBSCAN epsilon parameter (distance threshold for clustering in XY).
        min_samples: DBSCAN minimum number of points to form a cluster.
    """
    if not deposition_points:
        print("No deposition points recorded.")
        return

    df_dep = pd.DataFrame(deposition_points, columns=['x', 'y', 'z'])
    df_dep['layer'] = (df_dep['z'] // layer_height).astype(int)
    height = df_dep['z'].max()- df_dep['z'].min()

    # Dictionary to store results per layer
    layer_geometries = {}
    
    for layer, group in df_dep.groupby('layer'):
        points_xy = group[['x', 'y']].values
        
        # Use DBSCAN to identify clusters within the layer
        clustering = DBSCAN(eps=eps, min_samples=min_samples).fit(points_xy)
        labels = clustering.labels_
        
        clusters = {}
        for label in set(labels):
            if label == -1:
                continue  # Skip noise points if any
            cluster_points = points_xy[labels == label]
            if cluster_points.shape[0] >= 3:
                hull = ConvexHull(cluster_points)
                area = hull.volume  # In 2D, 'volume' is the area
            else:
                area = 0
            obb_features = compute_obb_features(cluster_points)
            
            clusters[label] = {
                'points': cluster_points,
                'area': area,
                'num_points': cluster_points.shape[0],
                'centroid': obb_features['centroid'],
                'length': obb_features['length'],
                'width': obb_features['width'],
                'diagonal': obb_features['diagonal']
            }
        
        layer_geometries[layer] = clusters

    # Print out the computed area and number of points for each cluster in each layer

    for layer, clusters in sorted(layer_geometries.items()):
        print(f"Layer {layer}:")
        for label, geom in clusters.items():
            print(f"  Piece {label}: {geom['num_points']} points, Area ~ {geom['area']:.2f} units², "
                  f"Length ~ {geom['length']:.2f}, Width ~ {geom['width']:.2f}, Diagonal ~ {geom['diagonal']:.2f}, Height ~ {height:.2f}")
    
    return layer_geometries
    
