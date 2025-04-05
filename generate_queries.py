import random
import requests
import time

def generate_random_ip():
    return f"{random.randint(1, 255)}.{random.randint(0, 255)}.{random.randint(0, 255)}.{random.randint(0, 255)}"

user_names = list()


for i in range(20):
    user_names.append(f"user_{i+1}")
    user_names.append(f"admin_{i+1}")

select_queries = [
    "SELECT * FROM customers",
    "SELECT first_name, last_name FROM customers",
    "SELECT * FROM customers WHERE first_name = 'John'",
    "SELECT * FROM customers WHERE last_name = 'Doe'",
    "SELECT * FROM customers WHERE email LIKE '%example.com'",
]

headers = {
    'Content-Type': 'application/json'
}

total = 0
for i in range(10):
    try:
        user = random.choice(user_names)
        query = random.choice(select_queries)
        url = f"http://localhost:5002/query?username={user}" 
        payload = {
            "query": query,
            "X-Forwarded-For": generate_random_ip()
        }
        print(f"Sending request as {user}: {query}")
        response = requests.post(url, headers=headers, json=payload)

        if response.status_code != 200:
            print(f"Request failed with status code {response.status_code}")
        elif response.status_code == 200:
            print("Response:", response.json())

        print(response.status_code, response.json())
        print("Success!")
        total += 1
        time.sleep(0.1)  
    except Exception as e:
        print(f"Error: {e}")

print(f"{total} requests sent successfully.")
