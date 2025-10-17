"""
Data Backup and Restore Utility for Car Tracker
Run this script to backup/restore your data before deployment
"""

import pandas as pd
import os
import json
import datetime as dt
from pathlib import Path

def backup_user_data(username=None):
    """Backup user data to JSON format"""
    backup_dir = Path("backups")
    backup_dir.mkdir(exist_ok=True)
    
    timestamp = dt.datetime.now().strftime("%Y%m%d_%H%M%S")
    
    if username:
        # Backup specific user
        users_to_backup = [username]
    else:
        # Backup all users
        users_to_backup = []
        if os.path.exists("users.csv"):
            users_df = pd.read_csv("users.csv")
            users_to_backup = users_df["username"].tolist()
    
    for user in users_to_backup:
        user_data = {}
        
        # Backup cars
        cars_file = f"{user}_cars.csv"
        if os.path.exists(cars_file):
            cars_df = pd.read_csv(cars_file)
            user_data["cars"] = cars_df.to_dict('records')
        
        # Backup bookings
        bookings_file = f"{user}_bookings.csv"
        if os.path.exists(bookings_file):
            bookings_df = pd.read_csv(bookings_file)
            user_data["bookings"] = bookings_df.to_dict('records')
        
        # Backup expenses
        expenses_file = f"{user}_expenses.csv"
        if os.path.exists(expenses_file):
            expenses_df = pd.read_csv(expenses_file)
            user_data["expenses"] = expenses_df.to_dict('records')
        
        # Save backup
        if user_data:
            backup_file = backup_dir / f"{user}_backup_{timestamp}.json"
            with open(backup_file, 'w') as f:
                json.dump(user_data, f, indent=2)
            print(f"✅ Backed up data for user '{user}' to {backup_file}")
    
    # Backup users file
    if os.path.exists("users.csv"):
        users_backup = backup_dir / f"users_backup_{timestamp}.csv"
        pd.read_csv("users.csv").to_csv(users_backup, index=False)
        print(f"✅ Backed up users data to {users_backup}")

def restore_user_data(backup_file_path):
    """Restore user data from JSON backup"""
    with open(backup_file_path, 'r') as f:
        user_data = json.load(f)
    
    # Extract username from filename
    filename = Path(backup_file_path).name
    username = filename.split('_backup_')[0]
    
    # Restore cars
    if "cars" in user_data and user_data["cars"]:
        cars_df = pd.DataFrame(user_data["cars"])
        cars_df.to_csv(f"{username}_cars.csv", index=False)
        print(f"✅ Restored cars data for {username}")
    
    # Restore bookings
    if "bookings" in user_data and user_data["bookings"]:
        bookings_df = pd.DataFrame(user_data["bookings"])
        bookings_df.to_csv(f"{username}_bookings.csv", index=False)
        print(f"✅ Restored bookings data for {username}")
    
    # Restore expenses
    if "expenses" in user_data and user_data["expenses"]:
        expenses_df = pd.DataFrame(user_data["expenses"])
        expenses_df.to_csv(f"{username}_expenses.csv", index=False)
        print(f"✅ Restored expenses data for {username}")

def list_backups():
    """List available backup files"""
    backup_dir = Path("backups")
    if not backup_dir.exists():
        print("No backups directory found.")
        return
    
    backup_files = list(backup_dir.glob("*_backup_*.json"))
    if not backup_files:
        print("No backup files found.")
        return
    
    print("Available backups:")
    for i, backup_file in enumerate(backup_files, 1):
        print(f"{i}. {backup_file.name}")
    
    return backup_files

if __name__ == "__main__":
    print("🚗 Car Tracker Data Backup Utility")
    print("=" * 40)
    
    while True:
        print("\nOptions:")
        print("1. Backup all user data")
        print("2. Backup specific user data")
        print("3. Restore user data")
        print("4. List available backups")
        print("5. Exit")
        
        choice = input("\nEnter your choice (1-5): ").strip()
        
        if choice == "1":
            backup_user_data()
            print("\n✅ Backup completed!")
        
        elif choice == "2":
            username = input("Enter username to backup: ").strip()
            backup_user_data(username)
            print(f"\n✅ Backup completed for user '{username}'!")
        
        elif choice == "3":
            backup_files = list_backups()
            if backup_files:
                try:
                    choice_num = int(input("\nEnter backup number to restore: ")) - 1
                    if 0 <= choice_num < len(backup_files):
                        restore_user_data(backup_files[choice_num])
                        print("\n✅ Restore completed!")
                    else:
                        print("Invalid choice.")
                except ValueError:
                    print("Please enter a valid number.")
        
        elif choice == "4":
            list_backups()
        
        elif choice == "5":
            break
        
        else:
            print("Invalid choice. Please try again.")
    
    print("\nThank you for using Car Tracker Backup Utility!")
