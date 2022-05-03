import json
import os

from flask import Flask
from flask_socketio import SocketIO, emit
from flask_cors import CORS
from flask_mysqldb import MySQL

app = Flask(__name__)
app.config['SECRET_KEY'] = 'development key'
socket = SocketIO(app, cors_allowed_origins="*")
CORS(app)

app.config['MYSQL_HOST'] = 'us-cdbr-east-05.cleardb.net'
app.config['MYSQL_USER'] = 'b8d01d88271309'
app.config['MYSQL_PASSWORD'] = '3b220325'
app.config['MYSQL_DB'] = 'heroku_9390bfdc44d4566'
# app.config['MYSQL_URL'] = 'mysql://b8d01d88271309:3b220325@us-cdbr-east-05.cleardb.net/heroku_9390bfdc44d4566?reconnect=true'
mysql = MySQL(app)

active_users = {}
messages = []


@app.route('/port')
def port():
    return json.dumps(int(os.environ.get('PORT')))


@app.route('/')
def serve_static_index():
    cursor = mysql.connection.cursor()
    sql = "SELECT * FROM user"
    cursor.execute(sql, )
    users = cursor.fetchall()
    sql = "SELECT * FROM block"
    cursor.execute(sql, )
    block = cursor.fetchall()

    data = {"messages": [], "users": [], "block": []}
    sql = "SELECT * FROM message"
    cursor.execute(sql, )
    messages = cursor.fetchall()

    for val in messages:
        data["messages"].append(
            {"room": val[1], "sender": val[2], "receiver": val[3], "time": val[4], "message": val[5]})

    for val in users:
        data["users"].append({"name": val[1], "email": val[2], "picture": val[3]})
    for val in block:
        data["block"].append({"user": val[1], "blocked_user": val[2]})
    return json.dumps(data, )


@socket.on('connect')
def on_connect():
    print('user connected', )


@socket.on('activate_user')
def on_active_user(data):
    active_users[data['email']] = data
    emit('user_activated', active_users, broadcast=True)
    cursor = mysql.connection.cursor()
    sql_check = "SELECT * FROM user WHERE email = %s"
    cursor.execute(sql_check, (data['email'],))
    val = cursor.fetchall()
    if len(val) < 1:
        cursor.execute("INSERT INTO user (name, email, picture) values (%s,%s,%s) ",
                       (data["name"], data["email"], data["picture"]))
        mysql.connection.commit()
    cursor.close()


@socket.on('deactivate_user')
def on_inactive_user(data):
    del active_users[data['email']]
    emit('user_deactivated', active_users, broadcast=True)


@socket.on('block_user')
def on_block(data):
    cursor = mysql.connection.cursor()
    sql = "INSERT into block (blocked_user, user) value (%s,%s)"
    cursor.execute(sql, (data['blocked_user'], data['user'],))
    mysql.connection.commit()
    emit('user_blocked', data, broadcast=True)


@socket.on('unblock_user')
def un_block(data):
    cursor = mysql.connection.cursor()
    sql = "DELETE FROM block WHERE blocked_user=%s AND user=%s"
    cursor.execute(sql, (data['blocked_user'], data['user'],))
    mysql.connection.commit()
    emit('user_unblocked', data, broadcast=True)


@socket.on('send_message')
def on_chat_sent(data):
    messages.append(data)
    emit('message_sent', messages, broadcast=True)
    cursor = mysql.connection.cursor()
    sql = "INSERT into message (room, sender, receiver, time, message) values (%s,%s,%s,%s,%s)"
    cursor.execute(sql, (data['room'], data['sender'], data['receiver'], data['sent'], data['message']))
    mysql.connection.commit()
    cursor.close()


if __name__ == "__main__":
    port = int(os.environ.get('PORT'))
    socket.run(app=app, debug=True, port=port, host='0.0.0.0')
