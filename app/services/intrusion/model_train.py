from quiplet import to_quiplet, flatten_quiplet
from model_save import save_model
from config import config

import psycopg2
import numpy as np
from sklearn.svm import SVC
from sklearn.cluster import DBSCAN
from sklearn.metrics import confusion_matrix, classification_report, accuracy_score
from sklearn.model_selection import train_test_split
import matplotlib.pyplot as plt
import seaborn as sns
from collections import defaultdict

# Schema being used
global_schema = {
    "customers": ["first_name", "last_name", "email", "number"]
}

def get_query_logs():
    connection = psycopg2.connect(
        host=config.DB_HOST,
        database=config.DB_NAME,
        user=config.DB_USER,
        password=config.DB_PASSWORD,
        port=config.DB_PORT
    )
    cursor = connection.cursor()
    cursor.execute("SELECT username, query_text FROM user_logs WHERE query_text IS NOT NULL AND executed = TRUE")
    logs = cursor.fetchall()
    cursor.close()
    connection.close()
    return logs

def build_allowed_clusters(labels, predictions, threshold=0.05):
    cm = confusion_matrix(labels, predictions)
    allowed_clusters = {}
    for i in range(len(cm)):
        allowed = [i]
        total = np.sum(cm[i])
        if total == 0:
            continue
        for j in range(len(cm)):
            if i != j:
                misclass_rate = cm[i][j] / total
                if misclass_rate >= threshold:
                    allowed.append(j)
        allowed_clusters[i] = allowed
    return allowed_clusters

def main():
    print("Fetching query logs...")
    logs = get_query_logs()
    print(f"Found {len(logs)} queries for training.")

    quiplets = []
    user_ids = []

    for username, query in logs:
        try:
            q = to_quiplet(query, global_schema)
            f = flatten_quiplet(q)
            quiplets.append(f)
            user_ids.append(username)
        except Exception as e:
            print(f"Skipping query for {username} due to {e}")

    X = np.array(quiplets)
    user_ids = np.array(user_ids)

    print("Clustering with DBSCAN...")
    clustering = DBSCAN(eps=0.5, min_samples=1).fit(X)
    predictions = clustering.labels_

    cluster_map = {}
    user_cluster_counts = defaultdict(lambda: defaultdict(int))

    for user, cluster in zip(user_ids, predictions):
        user_cluster_counts[user][cluster] += 1

    for user in user_cluster_counts:
        most_common_cluster = max(user_cluster_counts[user], key=user_cluster_counts[user].get)
        cluster_map[user] = most_common_cluster

    labels = np.array([cluster_map[u] for u in user_ids])

    # 80/20 train/test split
    X_train, X_test, y_train, y_test = train_test_split(X, labels, test_size=0.2, random_state=42)

    print("Training SVM classifier...")
    clf = SVC()
    clf.fit(X_train, y_train)

    # Evaluate on test set
    print("Evaluating classifier on test set...")
    y_pred = clf.predict(X_test)

    cm = confusion_matrix(y_test, y_pred)

    plt.figure(figsize=(8,6))
    sns.heatmap(cm, annot=True, fmt="d", cmap="Blues")
    plt.title("Confusion Matrix (Test Set)")
    plt.xlabel("Predicted Cluster")
    plt.ylabel("True Cluster")
    plt.show()

    print("Classification Report (Test Set):")
    print(classification_report(y_test, y_pred))

    print("Accuracy (Test Set):", accuracy_score(y_test, y_pred))

    # Build allowed clusters (based on full labels and clustering)
    allowed_clusters = build_allowed_clusters(labels, predictions)
    print(f"Cluster Map Keys: {list(cluster_map.keys())}")

    # Save model and cluster maps
    save_model(clf, cluster_map, allowed_clusters)

if __name__ == "__main__":
    main()
