import pickle
import os

def save_model(clf, cluster_map, allowed_clusters):
    try:
        base_dir = os.path.dirname(__file__)
        clf_path = os.path.join(base_dir, "clf.pkl")
        cluster_map_path = os.path.join(base_dir, "cluster_map.pkl")
        allowed_clusters_path = os.path.join(base_dir, "allowed_clusters.pkl")

        with open(clf_path, "wb") as f:
            pickle.dump(clf, f)
        with open(cluster_map_path, "wb") as f:
            pickle.dump(cluster_map, f)
        with open(allowed_clusters_path, "wb") as f:
            pickle.dump(allowed_clusters, f)

        print("Model, cluster map, and allowed clusters saved successfully.")
        print(f"Cluster Map Keys (Saved): {list(cluster_map.keys())}")
    except Exception as e:
        print(f"Error: Could not save model: {e}")

def load_model():
    base_dir = os.path.dirname(__file__)
    clf_path = os.path.join(base_dir, "clf.pkl")
    cluster_map_path = os.path.join(base_dir, "cluster_map.pkl")
    allowed_clusters_path = os.path.join(base_dir, "allowed_clusters.pkl")

    try:
        with open(clf_path, "rb") as f:
            clf = pickle.load(f)
        with open(cluster_map_path, "rb") as f:
            cluster_map = pickle.load(f)
        with open(allowed_clusters_path, "rb") as f:
            allowed_clusters = pickle.load(f)

        print("Model and cluster map loaded successfully.")
        print(f"Cluster Map Keys (Loaded): {list(cluster_map.keys())}")
        return clf, cluster_map, allowed_clusters
    except Exception as e:
        print(f"Error: Could not load model: {e}")
        return None, None, None
