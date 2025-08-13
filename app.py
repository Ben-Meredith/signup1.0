import hashlib
import json
import os
import getpass
import warnings
from getpass import GetPassWarning

USERS_FILE = "users.json"

# Load users from file
def load_users():
    if not os.path.exists(USERS_FILE):
        return {}
    with open(USERS_FILE, "r") as file:
        return json.load(file)

# Save users to file
def save_users(users):
    with open(USERS_FILE, "w") as file:
        json.dump(users, file)

# Hash a password
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

# Create a new account
def signup(users):
    username = input("Choose a username: ")
    if username in users:
        print("❌ That username is already taken.")
        return
    full_name = input("Enter your full name: ")

    with warnings.catch_warnings():
        warnings.simplefilter("ignore", GetPassWarning)
        password = getpass.getpass("Choose a password: ")

    users[username] = {
        "name": full_name,
        "password": hash_password(password)
    }
    save_users(users)
    print(f"✅ Account for '{username}' created successfully!")

# Log into an account
def login(users):
    username = input("Enter username: ")

    with warnings.catch_warnings():
        warnings.simplefilter("ignore", GetPassWarning)
        password = getpass.getpass("Enter password: ")

    if username in users and users[username]["password"] == hash_password(password):
        print(f"✅ Welcome back, {users[username]['name']}!")
    else:
        print("❌ Invalid username or password.")

# Main program
def main():
    users = load_users()

    while True:
        choice = input("\n1. Sign Up\n2. Log In\n3. Exit\nChoose an option: ")
        if choice == "1":
            signup(users)
        elif choice == "2":
            login(users)
        elif choice == "3":
            print("👋 Goodbye!")
            break
        else:
            print("❌ Invalid choice.")

if __name__ == "__main__":
    main()

