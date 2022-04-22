import mysql.connector
import os

mydb = mysql.connector.connect(
  host="remotemysql.com",
  user=os.environ.get("DB_NAME"),
  password=os.environ.get("DB_PASSWORD"),
  database=os.environ.get("DB_NAME")
)

mycursor = mydb.cursor()

# Users Table Creation
mycursor.execute("CREATE TABLE Users (userid VARCHAR(40) PRIMARY KEY, username VARCHAR(30) NOT NULL, email VARCHAR(30) NOT NULL, phonenumber CHAR(10) NOT NULL, password TEXT NOT NULL, is_admin INT DEFAULT 0, wallet DECIMAL(15,2), is_verified INT DEFAULT 0)")

mycursor.execute("INSERT INTO Users (userid, username, email, phonenumber, password, wallet) VALUES (UUID(), 'Sai Jeevan P', 'jeevanrockjump1989@gmail.com', '7288961100', 'Jeevan@2002', '1000')")

# Purchases Table Creation
mycursor.execute("CREATE TABLE Purchases (purchase_id INT NOT NULL AUTO_INCREMENT, user_id VARCHAR(40) NOT NULL, item_name TEXT NOT NULL, price INT NOT NULL, amount_paid DECIMAL(15,2) NOT NULL, purchase_date DATE NOT NULL, PRIMARY KEY (purchase_id))")


# Payments Table Creation
mycursor.execute("CREATE TABLE Payments (payment_id INT NOT NULL AUTO_INCREMENT, purchase_id INT NOT NULL, amount_paid DECIMAL(15,2) NOT NULL, payment_date DATE NOT NULL, PRIMARY KEY (payment_id))")

mydb.commit()