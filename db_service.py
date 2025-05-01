import mysql.connector
from datetime import datetime

# Configure MySQL Database
mysql_config = {
    'host': 'YOUR_HOST',
    'user': 'YOUR_USERNAME',
    'password': 'YOUR_MYSQL_PASSWORD',
    'database': 'YOUR_DATABASE'
}

def get_or_create_session(slack_user_id, channel_id):
    """Retrieves or creates a session for the user in the database."""
    connection = mysql.connector.connect(**mysql_config)
    cursor = connection.cursor(dictionary=True)
    cursor.execute("SELECT session_id FROM slack_session WHERE slack_user_id=%s AND channel_id=%s AND ended_at IS NULL", 
                   (slack_user_id, channel_id))
    session = cursor.fetchone()
    
    if not session:
        session_id = f"session_{int(datetime.utcnow().timestamp())}"
        cursor.execute("INSERT INTO slack_session (slack_user_id, session_id, channel_id) VALUES (%s, %s, %s)",
                       (slack_user_id, session_id, channel_id))
        connection.commit()
    else:
        session_id = session["session_id"]
    
    cursor.close()
    connection.close()
    return session_id

def save_chat_history(slack_user_id, session_id, channel_id, thread_ts, user_request, system_response):
    """Saves the chat history in the database."""
    connection = mysql.connector.connect(**mysql_config)
    cursor = connection.cursor()
    cursor.execute("""
        INSERT INTO slack_history (slack_user_id, session_id, channel_id, thread_ts, user_request, system_response)
        VALUES (%s, %s, %s, %s, %s, %s)
    """, (slack_user_id, session_id, channel_id, thread_ts, user_request, system_response))
    connection.commit()
    cursor.close()
    connection.close()

def save_feedback(slack_user_id, session_id, thread_ts, feedback):
    """Save user feedback in the database."""
    connection = mysql.connector.connect(**mysql_config)
    cursor = connection.cursor()
    cursor.execute("""
        UPDATE slack_history 
        SET feedback = %s 
        WHERE slack_user_id = %s AND session_id = %s AND thread_ts = %s
    """, (feedback, slack_user_id, session_id, thread_ts))
    connection.commit()
    cursor.close()
    connection.close()
