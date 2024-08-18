import sqlite3
import os
import heapq
from collections import defaultdict

def get_total_server_bot():
    data_directory = 'data'
    total_servers = 0
    
    # Iterate over all files in the specified directory
    for db_file in os.listdir(data_directory):
        # Construct the full path to the database file
        db_path = os.path.join(data_directory, db_file)
        
        # Check if it's a file (to skip directories or other file types)
        if os.path.isfile(db_path):
            total_servers += 1
    
    return total_servers

def get_total_messages_bot():
    data_directory = 'data'
    total_messages = 0
    
    # Iterate over all files in the specified directory
    for db_file in os.listdir(data_directory):
        # Construct the full path to the database file
        db_path = os.path.join(data_directory, db_file)
        
        # Check if it's a file (to skip directories or other file types)
        if os.path.isfile(db_path):
            try:
                # Connect to the SQLite database
                conn = sqlite3.connect(db_path)
                cursor = conn.cursor()
                
                # Execute the query to sum messages
                cursor.execute("SELECT SUM(messages) FROM users")
                
                # Fetch the result
                result = cursor.fetchone()
                
                # Add the result to the total, handle None case
                if result[0] is not None:
                    total_messages += result[0]
                
                # Close the connection
                conn.close()
            except sqlite3.Error as e:
                print(f"Error accessing {db_file}: {e}")
                continue
    
    return total_messages

def get_total_seconds_bot():
    data_directory = 'data'
    total_seconds = 0
    
    # Iterate over all files in the specified directory
    for db_file in os.listdir(data_directory):
        # Construct the full path to the database file
        db_path = os.path.join(data_directory, db_file)
        
        # Check if it's a file (to skip directories or other file types)
        if os.path.isfile(db_path):
            try:
                # Connect to the SQLite database
                conn = sqlite3.connect(db_path)
                cursor = conn.cursor()
                
                # Execute the query to sum seconds
                cursor.execute("SELECT SUM(seconds) FROM users")
                
                # Fetch the result
                result = cursor.fetchone()
                
                # Add the result to the total, handle None case
                if result[0] is not None:
                    total_seconds += result[0]
                
                # Close the connection
                conn.close()
            except sqlite3.Error as e:
                print(f"Error accessing {db_file}: {e}")
                continue
    
    return total_seconds

def ConvertSecondsToTime(seconds):
    # Calcul des heures, minutes et secondes
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    seconds = seconds % 60
    
    # Formatage du temps
    time_format = "{:02d}:{:02d}:{:02d}".format(hours, minutes, seconds)
    
    return time_format

def get_top_users_by_seconds():
    data_directory = 'data'
    top_n = 10
    user_times = []

    for db_file in os.listdir(data_directory):
        db_path = os.path.join(data_directory, db_file)
        
        if os.path.isfile(db_path) and db_file.endswith('.db'):
            try:
                with sqlite3.connect(db_path) as conn:
                    cursor = conn.cursor()
                    
                    # Assuming 'users' table has columns 'id' and 'seconds'
                    cursor.execute("SELECT id, seconds FROM users")
                    results = cursor.fetchall()
                    
                    # Add results to the list, if any
                    if results:
                        user_times.extend(results)
            except sqlite3.Error as e:
                print(f"Error accessing {db_file}: {e}")
                continue
    
    # Combine results for the same user
    combined_user_times = defaultdict(int)
    for user_id, seconds in user_times:
        combined_user_times[user_id] += seconds
    
    # Convert to a list of tuples
    combined_user_times_list = list(combined_user_times.items())
    
    # Use heapq to find the top_n users with the most seconds
    top_users = heapq.nlargest(top_n, combined_user_times_list, key=lambda x: x[1])
    
    # Convert seconds to formatted time
    top_users_formatted = [(user_id, ConvertSecondsToTime(seconds)) for user_id, seconds in top_users]
    
    return top_users_formatted

