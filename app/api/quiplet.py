import sqlparse
from sqlparse.sql import IdentifierList, Identifier, Where, Comparison
from sqlparse.tokens import Keyword, DML
from sklearn.cluster import DBSCAN
import numpy as np
from collections import defaultdict
from sklearn.svm import SVC
from app.services.protection import get_query_logs

global_schema = {
    "customers": ["first_name", "last_name", "email", "number"]
}

model_store = {
    "clf": None,
    "cluster_map": None,
}

def get_tokens_from_table(tokens):
    for i, token in enumerate(tokens):
        if token.ttype is Keyword and token.value.upper() == "FROM":
            if i + 1 < len(tokens):
                next_token = tokens[i+1]
                if isinstance(next_token, Identifier):
                    return next_token.get_real_name()
    return None

def get_tokens(query):
    parsed = sqlparse.parse(query)[0]
    tokens = list()
    for token in parsed.tokens:
        if not token.is_whitespace:
            tokens.append(token)
    return tokens, parsed.get_type().upper()

def get_select_attr(tokens):
    fields = list()
    current_table = get_tokens_from_table(tokens)
    select_seen = False
    for token in tokens:
        if token.ttype is DML and token.value.upper() == "SELECT":
            select_seen = True
        elif token.ttype is Keyword and token.value.upper() == "FROM":
            break
        elif select_seen:
            if isinstance(token, IdentifierList):
                for identifier in token.get_identifiers():
                    val = identifier.get_real_name()
                    fields.append(f"{current_table}.{val}")
            elif isinstance(token, Identifier):
                val = token.get_real_name()
                fields.append(f"{current_table}.{val}")
            elif token.ttype and token.value == "*":
                fields.append("*")
    return fields

def get_conditions(tokens):
    cond = list()
    for token in tokens:
        if isinstance(token, Where):
            for t in token.tokens:
                if isinstance(t, Comparison):
                    if hasattr(t.left, "get_name"):
                        cond.append(t.left.value.strip())
    return cond

def to_quiplet(query, schema):
    command_map = {"SELECT": 0, "INSERT": 1,
                   "UPDATE" : 2, "DELETE" : 3,
                   "CREATE" : 4, "DROP" : 5}
    tokens, command_type = get_tokens(query)

    command = command_map.get(command_type, -1)

    rel_list = list(schema.keys())
    
    rel_idx = dict()
    attr_idx = dict()
    prj_attr = list()
    sel_attr = list()
    prj_rel = [0] * len(schema)
    sel_rel = [0] * len(schema)

    for i, rel in enumerate(rel_list):
        rel_idx[rel] = i
    
    for rel in schema:
        inner_dict = {}
        for j, attr in enumerate(schema[rel]):
            inner_dict[attr] = j
        attr_idx[rel] = inner_dict
    
    

    for rel in schema:
        prj_attr.append([0] * len(schema[rel]))
        sel_attr.append([0] * len(schema[rel]))
    
    select_fields = get_select_attr(tokens)
    if select_fields == ["*"]:
        table = get_tokens_from_table(tokens)
        if table in rel_idx:
            prj_rel[rel_idx[table]] = 1
        for i in range (len(schema[table])):
            prj_attr[rel_idx[table]][i] = 1
    else:
        for field in select_fields:
            if "." in field:
                rel, attr = field.strip().split(".")
                if rel in rel_idx and attr in attr_idx[rel]:
                    prj_rel[rel_idx[rel]] = 1
                    prj_attr[rel_idx[rel]][attr_idx[rel][attr]] = 1
        
    conditions = get_conditions(tokens)
    print(conditions)
    for field in conditions:
        if "." in field:
            rel, attr = field.strip().split(".")
            if rel in rel_idx and attr in attr_idx[rel]:
                sel_rel[rel_idx[rel]] = 1
                sel_attr[rel_idx[rel]][attr_idx[rel][attr]] = 1
    
    return [command, prj_rel, prj_attr, sel_rel, sel_attr]

def flatten_quiplet(quiplet):
    flat = [quiplet[0]]
    flat.extend(quiplet[1])

    for row in quiplet[2]:
        flat.extend(row)

    flat.extend(quiplet[3])

    for row in quiplet[4]:
        flat.extend(row)
    
    return flat

def create_profile(logs, schema, eps = 1.0, min_samples = 2):
    quiplets = list()
    user_ids = list()

    for id, query in logs:
        q = to_quiplet(query, schema)
        quiplets.append(flatten_quiplet(q))
        user_ids.append(id)
    
    clustering = DBSCAN(eps=eps, min_samples=min_samples).fit(quiplets)
    labels = clustering.labels_
    print(labels)


    cluster_map = dict()
    cluster_count = dict()

    for user, label in zip(user_ids, labels):
        if user not in cluster_count:
            cluster_count[user] = {}
        if label not in cluster_count[user]:
            cluster_count[user][label] = 0
        else:
            cluster_count[user][label] += 1
    
    for user, clusters in cluster_count.items():
        cluster_map[user] = max(clusters, key=clusters.get)
    
    return cluster_map, labels, quiplets, user_ids

def train_classifier(features, labels):
    clf = SVC(kernel="linear")
    clf.fit(features, labels)
    return clf

def intrusion_detection(query, user_id, schema, clf, cluster_map):
    quiplet = to_quiplet(query, schema)
    flatten = flatten_quiplet(quiplet)
    prediction = clf.predict([flatten])[0]

    user_cluster = cluster_map.get(user_id)
    if user_cluster != prediction:
        return True
    return False

def setup():
    logs = get_query_logs()
    if not logs:
        return 
    else:
        try:
            cluster_map, labels, quiplets, user_ids = create_profile(logs, global_schema, eps=1.5, min_samples=1)
            clf = train_classifier(quiplets, labels)
            model_store["clf"] = clf
            model_store["cluster_map"] = cluster_map
        except Exception as e:
            print(f"Unable to setup the detection model due to {e}")

def is_intrusion(query, user_id):
    clf = model_store.get("clf")
    cluster_map = model_store.get("cluster_map")
    if clf is None or cluster_map is None:
        return False
    else:
        return intrusion_detection(query, user_id, global_schema, clf, cluster_map)
      
def main():
    logs = [
        ("admin1", "SELECT A1 FROM REL1 WHERE C1 = 5"),
        ("admin1", "SELECT * FROM REL1"),
        ("admin1", "SELECT B1 FROM REL1"),
        ("staff1", "SELECT B2 FROM REL2"),
        ("staff1", "SELECT D2 FROM REL2 WHERE B2 = 3"),
        ("staff1", "SELECT A2 FROM REL2 WHERE A2 = 10")
    ]

    schema = {
        "REL1": ["A1", "B1", "C1"],
        "REL2": ["A2", "B2", "C2", "D2"]
    }

    user_cluster_map, labels, quiplets, user_ids = create_profile(logs, schema, eps=1.5, min_samples=1)
    clf = train_classifier(quiplets, labels)

    query = "SELECT D2 FROM REL2"
    user = "staff1"
    print("Intrusion?" , intrusion_detection(query, user, schema, clf, user_cluster_map))


# SELECT REL1.A1, REL1.B1 FROM REL1 WHERE REL1.C1 = 6
# DEBUG CONDITIONS: ['REL1.C1']
# CMD  proj_rel projection_attr          sel_Rel  [attributes used from table]
# [0, [1, 0], [[1, 1, 0], [0, 0, 0, 0]], [1, 0], [[0, 0, 1], [0, 0, 0, 0]]]
# proj_rel: what we choose from
# projection_attr: which cols are selected
# selection_relation: what table are used in where
    # dist = quiplet_distance(q1, q2)
    # print(dist)

main()

    

    
    

    


