import psycopg2
from config import config
import random

def get_customers():
    first_names = ["John", "Janice", "Micheal", "Tony", "Clara"]
    last_names = ["Smith", "Doe", "Johnson", "Brown", "Davis"]
    websites = ["example.com", "test.com", "demo.com", "sample.com", "site.com"]
    customers = []

    for i in range(1, 101):
        first_name = random.choice(first_names)
        last_name = random.choice(last_names)
        website = random.choice(websites)
        email = f"{first_name.lower()}.{last_name.lower()}@{website}"
        number = random.randint(1000000000, 9999999999)
        customers.append((first_name, last_name, email, str(number)))
    
    return customers

def populate_db():
    customer_list = get_customers()
    try:
        connection = psycopg2.connect(
            dbname=config.DB_NAME,
            user=config.DB_USER,
            password=config.DB_PASSWORD,
            host=config.DB_HOST,
            port=config.DB_PORT
        )
        cursor = connection.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS customers (
                       id SERIAL PRIMARY KEY, 
                       first_name VARCHAR(50), 
                       last_name VARCHAR(50), 
                       email VARCHAR(100), 
                       number VARCHAR(15)
                    );
        """)

        for customer in customer_list:
            cursor.execute("""
                INSERT INTO customers (first_name, last_name, email, number) 
                VALUES (%s, %s, %s, %s);
            """, customer)
        
        connection.commit()
        cursor.close()
        connection.close()
        print("Database populated successfully.")
    except Exception as e:
        print(f"Error populating database: {e}")

def main():
    print("Populating database...")
    populate_db()


main()

