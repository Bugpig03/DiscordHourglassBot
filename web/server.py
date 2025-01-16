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
    total_messages = GetTotalMessages()
    total_seconds = ConvertSecondsToTime(GetTotalSeconds())
    total_servers = GetDistinctServerCount()
    total_users = GetDistinctUserCount()
    total_profile = GetDistinctUserServerComboCount()
    database_size = GetDatabaseSize()
    stats_table_size = GetTableSize('stats')
    historical_stats_table_size = GetTableSize('historical_stats')
    last_historical = FormatSQLTimestampAndHoursToFrench(GetMostRecentDate())

    TopActivityUsers = GetTop5UsersEvolutionLast30Days()
    
    return render_template('home.html',TopActivityUsers=TopActivityUsers,total_messages=total_messages, total_seconds=total_seconds, total_servers=total_servers,total_users=total_users, total_profile=total_profile, database_size=database_size, stats_table_size=stats_table_size, historical_stats_table_size=historical_stats_table_size,last_historical=last_historical)

@app.route('/users')
def users():
    total_top_users = FormatGetTopUsers()
    return render_template('users.html', total_top_users=total_top_users)

@app.route('/servers')
def servers():
    server_stats = GetServersStats()
    return render_template('servers.html', server_stats=server_stats)

@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/profile/<username>')
def profile(username):
    user_id = GetUserIdByUsername(username)
    if user_id:
        user_server_stats = GetUserServerStats(user_id)
        user_global_time = GetTotalSecondsByUserId(user_id)
        user_global_msg = GetTotalMessagesByUserId(user_id)
        user_global_rank = GetUserRankBySeconds(user_id)
        activity = GetUserLastMonthSeconds(user_id)
        avatar_url = GetAvatarUrlById(user_id)

        return render_template('profile.html', username=username, user_server_stats=user_server_stats, user_global_time=user_global_time,user_global_msg=user_global_msg,user_global_rank=user_global_rank, activity=activity, avatar_url=avatar_url)
    else:
        return redirect(url_for('home'))
    
@app.route('/server/<server_id>')
def server(server_id):
    server_name = GetServerNameById(server_id)
    server_time = GetTotalSecondsByServerId(server_id)
    server_msg = GetTotalMessagesByServerId(server_id)
    server_rank = GetServerRankByTotalSeconds(server_id)
    server_count = GetDistinctServerCount()
    server_member_count = GetMemberCountByServerId(server_id)
    server_users_stats = GetUsersRankingByServerId(server_id)
    server_avatar_url = GetServerAvatarUrlById(server_id)
    return render_template('server.html', server_id = server_id, server_time = server_time,server_name = server_name, server_msg=server_msg,server_member_count=server_member_count, server_rank = server_rank, server_count = server_count, server_users_stats= server_users_stats, server_avatar_url=server_avatar_url)
    
@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404

if __name__ == '__main__':
    print("Application start")
    app.run(host='0.0.0.0', port=5002,debug=False)
