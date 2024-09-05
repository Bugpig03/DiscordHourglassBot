from flask import Flask, render_template
import json
import os
from functions import *
import heapq

app = Flask(__name__, static_url_path='/static')

@app.context_processor
def utility_processor():
    return dict(enumerate=enumerate)

@app.route('/')
def home():
    total_top_users = FormatGetTop25Users()
    return render_template('home.html', total_top_users=total_top_users)

@app.route('/bot')
def bot():
    total_messages = GetTotalMessages()
    total_seconds = ConvertSecondsToTime(GetTotalSeconds())
    total_servers = GetDistinctServerCount()
    total_users = GetDistinctUserCount()
    total_profile = GetDistinctUserServerComboCount()
    return render_template('bot.html', total_messages=total_messages, total_seconds=total_seconds, total_servers=total_servers,total_users=total_users, total_profile=total_profile)

@app.route('/server')
def server():
    return render_template('server.html')

@app.route('/about')
def about():
    return render_template('about.html')


if __name__ == '__main__':
    print("Application start")
    app.run(host='0.0.0.0', port=5002)
