import psycopg2
import numpy as np
from datetime import datetime, timedelta
from collections import defaultdict
from app.database.db import get_db_connection, get_db_cursor
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
    if is_user_blocked(user_id):
        return {
            "verdict" : "Blocked",
            "reason" : "Blocked due to suspicious activity.",
            "is_intrusion" : True
        }
    
    try:
        model, cluster_map, allowed_clusters = load_model()
        
        for query_safe in whitelist:
            if query.strip().upper().rstrip(";") == query_safe:
                return{
                    "verdict" : "Allowed",
                    "is_intrusion" : False
                }
        
        quiplet_flattened = flatten_quiplet(to_quiplet(query, global_schema))
        quiplet_flattened = np.array(quiplet_flattened).reshape(1,-1)
        prediction = int(model.predict(quiplet_flattened)[0])

        user_cluster = cluster_map.get(user_id)
        if user_cluster is None:
            raise Exception(f"{user_id} was not trained on the model or has no cluster map")
        
        if not isinstance(user_cluster, list):
            user_cluster = [user_cluster]
        
        allowed_clusters = allowed_clusters.get(prediction, [])
        match_count = 0

        for cluster in user_cluster:
            if cluster in allowed_clusters:
                match_count += 1

        confidence_score = 0.0
        if len(user_cluster) > 0:
            confidence_score = match_count / len(user_cluster)
        else:
            confidence_score = 0.0
        
        role = None
        if user_id.startswith("admin"):
            role = "admin"
        elif user_id.startswith("analyst"):
            role = "analyst"
        elif user_id.startswith("staff"):
            role = "staff"
        threshold = user_thresholds[role]

        if match_count > 0 and confidence_score >= threshold:
            return {
                "verdict" : "Allowed",
                "confidence" : round(confidence_score, 2),
                "threshold" : threshold,
                "is_intrusion" : False
            }
        
        total_occurances[user_id] += 1
        if total_occurances[user_id] >= block_threshold:
            block_user(user_id)
            return {
                "verdict" : "Blocked",
                "reason" : "User query activity is suspicious. Please contact an admin or wait 1 hour.",
                "confidence" : round(confidence_score, 2),
                "threshold" : threshold,
                "is_intrusion" : True
            }
        
        return {
            "verdict" : "Intrusion",
            "confidence" : round(confidence_score, 2),
            "threshold" : threshold,
            is_intrusion : True
        }
    except Exception as e:
        print(f"Could not process query: {e}")



