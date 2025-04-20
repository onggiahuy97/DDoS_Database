from quiplet import to_quiplet, flatten_quiplet, create_profile, train_classifier
from model_save import save_model
import psycopg2
from config import config
from sklearn.metrics import confusion_matrix
import numpy as np
import os

global_schema = {
    "customers" : ["first_name", "last_name", "email", "number"]
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
    cursor.execute("SELECT username, query_text FROM connection_log WHERE query_text IS NOT NULL")
    logs = cursor.fetchall()
    cursor.close()
    connection.close()
    return logs

def build_allowed_clusters(labels, predictions, threshold=0.2):
    cm = confusion_matrix(labels, predictions)
    allowed_clusters = {}

    for i in range(len(cm)):
        allowed = [i]
        for j in range(len(cm)):
            if i != j:
                rate = cm[i][j] / np.sum(cm[i])
                if rate > threshold:
                    allowed.append(j)
        allowed_clusters[i] = allowed

    return allowed_clusters

def main():
    logs = get_query_logs()
    if not logs:
        print("No query logs found.")
        return

    print(f"Found {len(logs)} queries for training.")
    cluster_map, labels, quiplets, user_ids = create_profile(logs, global_schema, eps=0.5, min_samples=1)
    clf = train_classifier(quiplets, labels)

    predictions = clf.predict(quiplets)
    allowed_clusters = build_allowed_clusters(labels, predictions, threshold=0.15)

    save_model(clf, cluster_map, allowed_clusters)

    folder_path = os.path.dirname(os.path.abspath(__file__))  # gets path to ./app/services/intrusion
    output_path = os.path.join(folder_path, "confusion_matrix.npy")
    np.save(output_path, confusion_matrix(labels, predictions))

    print("✅ Model trained and saved successfully.")
    print(f"📦 Trained users: {list(cluster_map.keys())}")

main()
