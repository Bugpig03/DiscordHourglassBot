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
    schedule.every().day.at("00:30").do(routine)
    while True:
        schedule.run_pending()
        # Attendre une minute avant de vérifier à nouveau
        print("wait 30s until check routine > current time >",datetime.now())
        time.sleep(30)