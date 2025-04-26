import psycopg2
import numpy as np
from datetime import datetime, timedelta
from collections import defaultdict
from app.database.db import get_db_cursor
from app.services.intrusion.model_save import load_model
from app.services.intrusion.quiplet import flatten_quiplet, to_quiplet

#schema of the database
global_schema = {
    "customers": ["first_name", "last_name", "email", "number"]
}

#adjustable thresholds for each user
user_thresholds = {
    "admin" : 0.9,
    "staff" : 0.7,
    "analyst" : 0.1
}

#total occurances for each user
total_occurances = defaultdict(int)
#how many times each user level can do an infraction
block_threshold = 3

#certain queries that can be whitelisted (subjective)
whitelist = {
    "SELECT * FROM customers"
}

# total ammount of time the user will be blocked for
block_duration = 60

#check the table blocked_users to determine if the
#user is blocked or not (return the status if it does exist)
def is_user_blocked(user_id):
    try:
        print(f"{user_id} block check initiated")
        with get_db_cursor() as cursor:
            cursor.execute("""
                SELECT 1 FROM blocked_users
                WHERE user_id = %s AND (block_expires IS NULL or block_expires > NOW())
                        """, (user_id,) )
            result = cursor.fetchone()
            blocked_status = result is not None
            return blocked_status
    except Exception as e:
        print(f"Error: Could not get blocked status {e}")

#connect to the blocked_users database and insert the user
#into the ban list, along with a timeout of 60 min
def block_user(user_id, reason="Intrusion was detected"):
    try:
        print(f"Blocking user {user_id} initiated")
        duration = datetime.now() + timedelta(minutes=block_duration)
        with get_db_cursor() as cursor:
            cursor.execute("""
                INSERT INTO blocked_users (user_id, block_expires, reason)
                VALUES (%s, %s, %s)
                ON CONFLICT (user_id) DO UPDATE
                SET block_expires = EXCLUDED.block_expires,
                    reason = EXCLUDED.reason
            """, (user_id, duration, reason))
            print(f"Blocked {user_id} for {duration} min")
    except Exception as e:
        print(f"Could not write to blocked_users for {user_id}: {e}")

#main method that will take a user query and user_id and determine if 
#the query matches previous user queries
def is_intrusion(query, user_id):

    # early exit and returns a blocked status
    if is_user_blocked(user_id):
        return {
            "verdict" : "Blocked",
            "reason" : "Blocked due to suspicious activity.",
            "is_intrusion" : True
        }
    
    # load the model and determine if the query matches oprevious logged
    # behavior
    try:
        model, cluster_map, allowed_clusters = load_model()
        
        # see if the query belongs to whitelisted queries
        # and return allowed status 
        for query_safe in whitelist:
            if query.strip().upper().rstrip(";") == query_safe.upper():
                return{
                    "verdict" : "Allowed",
                    "is_intrusion" : False
                }
        
        # convert query to a quiplet and then feed it to the saved prediction model
        quiplet_flattened = flatten_quiplet(to_quiplet(query, global_schema))
        quiplet_flattened = np.array(quiplet_flattened).reshape(1,-1)
        prediction = int(model.predict(quiplet_flattened)[0])

        # get the cluster associated with the user
        user_cluster = cluster_map.get(user_id)
        if user_cluster is None:
            raise Exception(f"{user_id} was not trained on the model or has no cluster map")
        
        # in case the cluster is a single value, convert to a list
        if not isinstance(user_cluster, list):
            user_cluster = [user_cluster]
        
        # get the list of clusters that the prediction matches
        allowed_clusters = allowed_clusters.get(prediction, [])
        match_count = 0

        # match each instance in which the user_cluser aligns with their
        # allowed cluster set
        for cluster in user_cluster:
            if cluster in allowed_clusters:
                match_count += 1

        # calculate the confidence score based on the number of
        # matches divided by the user_clusters
        confidence_score = 0.0
        if len(user_cluster) > 0:
            confidence_score = match_count / len(user_cluster)

        # determine the role of the user and ontain 
        #their threshold for activity
        role = None
        if user_id.startswith("admin"):
            role = "admin"
        elif user_id.startswith("analyst"):
            role = "analyst"
        elif user_id.startswith("staff"):
            role = "staff"
        threshold = user_thresholds[role]

        # assuming they meet their threshold, allow the query
        # to execute
        if match_count > 0 and confidence_score >= threshold:
            return {
                "verdict" : "Allowed",
                "confidence" : round(confidence_score, 2),
                "threshold" : threshold,
                "is_intrusion" : False
            }
        
        # else: count this as an occurance
        total_occurances[user_id] += 1

        # if they haven't met the block threshold, block
        # the action for now (DO NOT TIME THEM OUT)
        if total_occurances[user_id] >= block_threshold:
            block_user(user_id)
            return {
                "verdict" : "Blocked",
                "reason" : "User query activity is suspicious. Please contact an admin or wait 1 hour.",
                "confidence" : round(confidence_score, 2),
                "threshold" : threshold,
                "is_intrusion" : True
            }
        
        # if the exceeded their occurances, label it
        # an intrusion
        return {
            "verdict" : "Intrusion",
            "confidence" : round(confidence_score, 2),
            "threshold" : threshold,
            is_intrusion : True
        }
    except Exception as e:
        print(f"Could not process query: {e}")



