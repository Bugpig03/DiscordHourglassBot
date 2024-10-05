import schedule
import time
from datetime import datetime
from functions import *

if __name__ == '__main__':

    print("Application start")
    conn = ConnectToDataBase()
    if conn:
        conn.commit()
        conn.close()
        print("DB ON and conn close")
    else:
        print("Error DB connection")
    
    # WAIT DATE
    schedule.every().day.at("23:59").do(routine)
    while True:
        schedule.run_pending()
        # Attendre une minute avant de vérifier à nouveau
        time.sleep(30)