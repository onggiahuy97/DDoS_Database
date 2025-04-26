from quiplet import to_quiplet, flatten_quiplet
from model_save import save_model
from config import config
import psycopg2
import numpy as np
from sklearn.svm import SVC
from sklearn.cluster import DBSCAN
from sklearn.metrics import confusion_matrix
from collections import defaultdict

# schema being used
global_schema = {
    "customers": ["first_name", "last_name", "email", "number"]
}

# get the query_logs stored in the database to create
# the user profile
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


def build_allowed_clusters(labels, predictions, threshold=0.05):
    # build the confusion matrix based on cluster labels and the predictions
    # based on the feature vectors
    cm = confusion_matrix(labels, predictions)

    #dict to hold the allowed clsuters
    allowed_clusters = {}

    # loop through truth labels
    for i in range(len(cm)):
        allowed = [i]
        total = np.sum(cm[i]) # sum the total number of true labels at i
        if total == 0: # no samples for cluster at i
            continue
        # compare the prediction to the ground truth
        for j in range(len(cm)):
            # calculate the misclassification
            if i != j:
                # calculate if i was predicted as j
                misclass_rate = cm[i][j] / total

                # if misclassification is too high for us, we can
                # approve it (to better allow classification)
                if misclass_rate >= threshold:
                    allowed.append(j)
        allowed_clusters[i] = allowed
    return allowed_clusters

def main():
    print("Fetching query logs")
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

    # build out the feature matrixes
    X = np.array(quiplets)
    user_ids = np.array(user_ids)

    # cluster the queries to find the groups in which each query
    # belongs to and fit it to the features of X
    print("Clustering with DBSCAN")
    clustering = DBSCAN(eps=0.5, min_samples=1).fit(X)
    predictions = clustering.labels_

    # build a cluster mapping to show where each user falls into each clster
    cluster_map = {}
    user_cluster_counts = defaultdict(lambda: defaultdict(int))

    # denote which cluster the user query belongs to
    for user, cluster in zip(user_ids, predictions):
        user_cluster_counts[user][cluster] += 1

    # keep only the clusters with the most queries that existed for that userr
    for user in user_cluster_counts:
        most_common_cluster = max(user_cluster_counts[user], key=user_cluster_counts[user].get)
        cluster_map[user] = most_common_cluster

    # get the cluster labels
    labels = [cluster_map[u] for u in user_ids]

    print("Training SVM classifier")
    clf = SVC()
    clf.fit(X, labels)
    
    # build the clusters that exist for each truth label
    allowed_clusters = build_allowed_clusters(labels, predictions)
    print(f"Cluster Map Keys: {list(cluster_map.keys())}")

    save_model(clf, cluster_map, allowed_clusters)

main()

