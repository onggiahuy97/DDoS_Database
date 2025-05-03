import sqlparse
from sqlparse.sql import IdentifierList, Identifier, Where, Comparison, Function
from sqlparse.tokens import Keyword, DML

# schema of the database that is being worked with
# this is a way to map SQL queries into quiplets
global_schema = {
    "customers": ["first_name", "last_name", "email", "number"]
}

# figure out the table that is being accessed
# will traverse the SQL tokens and return the
# name of the table being queried
def get_table_name(tokens):
    # loop through all the tokens
    for i, token in enumerate(tokens):
        # is the current token of type Keyword and is it FROM?
        if token.ttype is Keyword and token.value.upper() == "FROM":
            # are there more tokems ahead of FROM?
            if i + 1 < len(tokens):
                next_token = tokens[i+1] 
                # is the next token a table name?
                # if so, return the name immedietly
                if isinstance(next_token, Identifier):
                    return next_token.get_real_name()
                # edge case of subqueries from another table
                # ex: FROM (SELECT * FROM customers) AS copy
                elif token.is_group:
                    for tkn in token.tokens:
                        if isinstance(tkn, Identifier):
                            return tkn.get_real_name()
                        
    return None

# parse a sql query and extract all SQL tokens 
# returns a token list along with what type of command is being
# parsed
def get_tokens(query):
    # send the query through sqlparse
    parsed = sqlparse.parse(query)[0]

    # list to hold all the tokens
    tokens = list()

    # loop through the tokens and take any non-whitespace tokens
    for token in parsed.tokens:
        if not token.is_whitespace:
            tokens.append(token)

    # return the tokens and the SQL command type
    return tokens, parsed.get_type().upper()

# extract the selection attributes that are being accessed in a SELECT
# statement and will associate the field with the table it belongs to
# returns it as a list of fields being accessed
def get_select_attr(tokens):
    # list to hold all the fields
    fields = list()

    # get the table name
    current_table = get_table_name(tokens)

    # has the SELECT token been seen
    select_seen = False

    # loop through all the tokens and stop once FROM is encountered
    for token in tokens:

        # is the token of type Data Manip. and is it SELECT?
        if token.ttype is DML and token.value.upper() == "SELECT":
            select_seen = True

        # is the token of type Keyword and is it FROM?
        # if so break out of the loop (finished parsing)
        elif token.ttype is Keyword and token.value.upper() == "FROM":
            break
        
        # extract the Field tokens
        elif select_seen:
            # is the token of type IdentiferList?
            if isinstance(token, IdentifierList):
                # go through the list of comma seperated
                # identifiers and keep track of each field
                for identifier in token.get_identifiers():
                    val = identifier.get_real_name()
                    fields.append(f"{current_table}.{val}")
            
            # is the token of type Identifer and is this
            # only accessing one field?
            elif isinstance(token, Identifier):
                val = token.get_real_name()
                fields.append(f"{current_table}.{val}")

            # # is this not valid token type and is it the * symbol?
            # # or is this a function like COUNT or other aggregation?
            # elif (token.ttype and token.value == "*") or (isinstance(token, Function)):
            #     fields.append("*")

            elif token.ttype and token.value == "*":
                # Handles SELECT * queries
                fields.append("*")

            elif isinstance(token, Function):
                # Handles COUNT(email), AVG(number), etc.
                func_name = token.get_name()
                if func_name:
                    fields.append(f"FUNC_{func_name.upper()}")
                else:
                    fields.append("FUNC_UNKNOWN")

    return fields

# parse the WHERE condition and extract the tokens
# that represent what fields are used in the conditionals
def get_conditions(tokens):
    # holds all the field token names
    cond = list()
    
    # loop through all WHERE clauses and extract the attribute being
    # used in the WHERE conditional
    for token in tokens:

        # is the token of type WHERE?
        if isinstance(token, Where):
            for t in token.tokens:
                # if the token is of type Comparrison, get the
                # left field attribute being used
                if isinstance(t, Comparison):
                    if hasattr(t.left, "get_name"):
                        cond.append(t.left.value.strip())
    return cond

# convert a SQL query to a lower dimensonal quiplet
def to_quiplet(query, schema):
    print(f"[query]: {query}")
    if not query or not isinstance(query, str):
        raise ValueError["[quiplet]: Invalid query: None or non-string brought in"]

    # numerical representation of the SQL commands
    command_map = {"SELECT": 0, "INSERT": 1,
                   "UPDATE" : 2, "DELETE" : 3,
                   "CREATE" : 4, "DROP" : 5}
    function_map = {
            "COUNT": 0, "SUM": 1, "AVG": 2,
            "MIN": 3, "MAX": 4, "NOW": 5,
            "UPPER": 6, "LOWER": 7}

    
    # parse and extract the tokens and the command being used
    tokens, command_type = get_tokens(query)

    # get the SQL command numerical representation
    command = command_map.get(command_type, -1)

    # list the tables being worked on based on the schema
    # in our case, it will just be customers table
    rel_list = list(schema.keys())

    # dictionary mapping representing table name as a key, and the 
    # the index (total tables and their respective index)
    # since we are only working with one table ("customers" : 0)
    # this is flexible and can work with more tables depending on how many
    # schemas are passed in the schema dict parameter
    rel_idx = {rel: i for i, rel in enumerate(rel_list)}

    # dict index that keeps track of the index order of all relation attributes
    # in the schema (key = "table", value is dict of attributes and the index order
    # in which they appear)
    attr_idx = {rel: {attr: j for j, attr in enumerate(schema[rel])} for rel in schema}

    # matrix list of 0 to signify which attributes are being accessed
    # in the SELECT statement
    prj_attr = [[0] * len(schema[rel]) for rel in schema]

    # matrix list of 0 to signify which attributes are accessed in the
    # WHERE conditions
    sel_attr = [[0] * len(schema[rel]) for rel in schema]

    # which schema table is being accessed
    prj_rel = [0] * len(schema)

    # what tables are involved in WHERE
    sel_rel = [0] * len(schema)

    fctn = [0] * len(function_map)

    # query token attributes denotation
    if command_type == "SELECT":
        # get the selection attribute names
        select_fields = get_select_attr(tokens)

        # if we are using * operator
        if select_fields == ["*"]:
            # get the table name 
            table = get_table_name(tokens)
            if table in rel_idx:
                # quiplet bit rep that * is being used
                prj_rel[rel_idx[table]] = 1
            # denote that allo attributes are being accessed
            for i in range (len(schema[table])):
                prj_attr[rel_idx[table]][i] = 1

        # assuming we are accessing specific fields
        else:
            # go through each field
            for field in select_fields:
                if field.startswith("FUNC_"):
                     name = field.split("_", 1)[1]
                     if name in function_map:
                         fctn[function_map[name]] = 1
                # check if dot notation is being used in SELECT
                # attributes
                if "." in field:
                    # remove the dot notation and get the 
                    # table and column names
                    rel, attr = field.strip().split(".")

                    # is the table name and attribute within the 
                    # respective dictionaries? if so, denote 
                    # which are being avvessed
                    if rel in rel_idx and attr in attr_idx[rel]:
                        prj_rel[rel_idx[rel]] = 1
                        prj_attr[rel_idx[rel]][attr_idx[rel][attr]] = 1
        
        # get the WHERE fields
        conditions = conditions = get_conditions(tokens)

        # loop through each field and denote which fields and
        # tables are being filtered
        for field in conditions:
            if "." in field:
                rel, attr = field.strip().split(".")
                if rel in rel_idx and attr in attr_idx[rel]:
                    sel_rel[rel_idx[rel]] = 1
                    sel_attr[rel_idx[rel]][attr_idx[rel][attr]] = 1
    
    # if INSERT is the command, mark all 
    # the fields as being projected/accessed
    elif command_type == "INSERT":
        table = get_table_name(tokens)
        if table in rel_idx:
            prj_rel[rel_idx[table]] = 1
            for i in range (len(schema[table])):
                prj_attr[rel_idx[table]][i] = 1
    
    # if UPDATE is the command, make the table
    # that is being accessed, what fields are projected,
    # and what fields are in the conditional WHERE
    elif command_type == "UPDATE":
        table = get_table_name(tokens)
        # check the table exists and mark the table
        # for selection and the projection 
        if table in rel_idx:
            sel_rel[rel_idx[table]] = 1
            prj_rel[rel_idx[table]] = 1

            # mark all attributes as being projected
            for i in range (len(schema[table])):
                prj_attr[rel_idx[table]][i] = 1
        
        # get the WHERE conditionals
        conditions = get_conditions(tokens)

        # denote which field is being selected in the conditonal
        for field in conditions:
            if "." in field:
                rel, attr = field.strip().split(".")
                if rel in rel_idx and attr in attr_idx[rel]:
                    sel_attr[rel_idx[rel]][attr_idx[rel][attr]] = 1
    
    # if DELETE, go through the table and denote which
    # table is being used to delete an entry
    # and denote the attributes being used in WHERE clause
    elif command_type == "DELETE":
        table = get_table_name(tokens)
        if table in rel_idx:
            sel_rel[rel_idx[table]] = 1
            conditions = get_conditions(tokens)
            for field in conditions:
                if "." in field:
                    rel, attr = field.strip().split(".")
                    if rel in rel_idx and attr in attr_idx[rel]:
                        sel_attr[rel_idx[rel]][attr_idx[rel][attr]] = 1

                        
    return [command, prj_rel, prj_attr, sel_rel, sel_attr, fctn]

# flatten the quiplet to be used with classifier
def flatten_quiplet(quiplet):
    flat = [quiplet[0]]
    flat.extend(quiplet[1])

    for row in quiplet[2]:
        flat.extend(row)

    flat.extend(quiplet[3])

    for row in quiplet[4]:
        flat.extend(row)
    flat.extend(quiplet[5])
    
    return flat



    

    
    

    


