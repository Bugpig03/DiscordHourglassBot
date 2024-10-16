from flask import Flask, render_template, redirect, url_for
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
    total_top_users = FormatGetTopUsers()
    return render_template('home.html', total_top_users=total_top_users)

@app.route('/bot')
def bot():
    total_messages = GetTotalMessages()
    total_seconds = ConvertSecondsToTime(GetTotalSeconds())
    total_servers = GetDistinctServerCount()
    total_users = GetDistinctUserCount()
    total_profile = GetDistinctUserServerComboCount()
    db_size = GetDatabaseSize()
    transaction_count = GetCommittedTransactionCount()
    return render_template('bot.html', total_messages=total_messages, total_seconds=total_seconds, total_servers=total_servers,total_users=total_users, total_profile=total_profile, db_size=db_size, transaction_count=transaction_count)

@app.route('/server')
def server():
    server_stats = GetServersStats()
    return render_template('server.html', server_stats=server_stats)

@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/profile/<username>')
def profile(username):
    user_id = GetUserIdByUsername(username)
    if user_id:
        user_server_stats = GetUserServerStats(user_id)
        return render_template('profile.html', username=username, user_server_stats=user_server_stats)
    else:
        return redirect(url_for('home'))
    
@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404

if __name__ == '__main__':
    print("Application start")
    app.run(host='0.0.0.0', port=5002)
