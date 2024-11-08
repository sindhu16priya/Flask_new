from flask import Flask, render_template, redirect, url_for, request, session, flash, jsonify
import mysql.connector
import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash
from googleapiclient.discovery import build  # YouTube API
from textblob import TextBlob
import os
from datetime import datetime

app = Flask(__name__)

# Database Configuration (SQLite / MySQL)
USE_SQLITE = False  # Set to True if you prefer SQLite, False for MySQL

if USE_SQLITE:
    app.config['DATABASE'] = 'feedback.db'  # SQLite database file
else:
    app.config['MYSQL_HOST'] = 'localhost'
    app.config['MYSQL_USER'] = 'root'  
    app.config['MYSQL_PASSWORD'] = 'user@123Root'  
    app.config['MYSQL_DB'] = 'customer_feedback'  

app.secret_key = 'your_secret_key'

API_KEY = 'AIzaSyDZZ6kKqLOTRc95E_V3xF4_eAvJA4_kFNY'  
youtube = build('youtube', 'v3', developerKey=API_KEY)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        # Connect to the database
        connection = get_db_connection()
        cursor = connection.cursor()
        cursor.execute('SELECT * FROM user WHERE username = %s', (username,))
        user = cursor.fetchone()
        cursor.close()
        connection.close()
        
        if user:  # Check if user exists
            if check_password_hash(user[2], password):  # user[2] is the hashed password
                session['user_id'] = user[0]  # user[0] is the user id
                session['role'] = user[3]  # user[3] is the user role
                flash('Login successful', 'success')

                # Redirect based on user role
                if user[3] == 'admin':
                    return redirect(url_for('dashboard'))
                else:
                    return redirect(url_for('user_dashboard'))  # Or wherever the user is redirected

            else:
                flash('Incorrect password', 'danger')
        else:
            flash('User does not exist', 'danger')

    return render_template('login.html')


# Function to get database connection (handles both MySQL and SQLite)
def get_db_connection():
    if USE_SQLITE:
        conn = sqlite3.connect(app.config['DATABASE'])
        conn.row_factory = sqlite3.Row
        return conn
    else:
        try:
            return mysql.connector.connect(
                host=app.config['MYSQL_HOST'],
                user=app.config['MYSQL_USER'],
                password=app.config['MYSQL_PASSWORD'],
                database=app.config['MYSQL_DB']
            )
        except mysql.connector.Error as err:
            print(f"Error: {err}")
            return None

# Define User model with roles (admin, developer, user)
def create_user(username, password, role):
    connection = get_db_connection()
    cursor = connection.cursor()
    
    # Check if the user already exists
    cursor.execute('SELECT * FROM user WHERE username = %s', (username,))
    existing_user = cursor.fetchone()
    
    if existing_user:
        print(f"User '{username}' already exists.")
        cursor.close()
        connection.close()
        return False
    
    # Hash the password before inserting it into the database
    hashed_password = generate_password_hash(password)
    cursor.execute('''INSERT INTO user (username, password, role) VALUES (%s, %s, %s)''',
                   (username, hashed_password, role))
    connection.commit()
    cursor.close()
    connection.close()
    return True

# ETL: Extract feedback and transform it
def extract_and_transform_feedback(feedback_text):
    # Extract - Get raw feedback text (already passed as input)
    # Transform - Process the feedback: Clean, Normalize, and Analyze sentiment
    feedback_text = feedback_text.strip().lower()  # Normalize text to lowercase
    feedback_text = ''.join(e for e in feedback_text if e.isalnum() or e.isspace())  # Remove special chars

    # Perform Sentiment Analysis using TextBlob
    sentiment, polarity = analyze_sentiment(feedback_text)

    return feedback_text, sentiment, polarity

def analyze_sentiment(text):
    blob = TextBlob(text)
    polarity = blob.sentiment.polarity
    sentiment = 'positive' if polarity > 0 else 'negative' if polarity < 0 else 'neutral'
    return sentiment, polarity
def load_feedback_to_db(name, email, message, sentiment, polarity):
    
    connection = get_db_connection()
    cursor = connection.cursor()
    cursor.execute('''INSERT INTO feedback (name, email, message, sentiment, polarity) 
                      VALUES (%s, %s, %s, %s, %s)''',
                   (name, email, message, sentiment, polarity))
    connection.commit()
    cursor.close()
    connection.close()

def submit_feedback(name, email, message):
    # ETL Process: Extract, Transform and Load feedback data
    message, sentiment, polarity = extract_and_transform_feedback(message)
    load_feedback_to_db(name, email, message, sentiment, polarity)

def get_video_comments(video_id):
    comments = []
    try:
        request = youtube.commentThreads().list(
            part='snippet',
            videoId=video_id,
            textFormat='plainText',
            maxResults=100
        )
        response = request.execute()
        
        for item in response['items']:
            comment = item['snippet']['topLevelComment']['snippet']['textDisplay']
            comments.append(comment)
            
    except Exception as e:
        print(f"An error occurred: {e}")
    
    return comments

def store_comment_in_db(comment_text, sentiment, polarity):
    connection = get_db_connection()
    cursor = connection.cursor()
    cursor.execute('''INSERT INTO feedback (name, email, message, sentiment, polarity) 
                      VALUES (%s, %s, %s, %s, %s)''',
                   ('YouTube Comment', 'N/A', comment_text, sentiment, polarity))
    connection.commit()
    cursor.close()
    connection.close()

@app.route('/store_youtube_comments/<video_id>')
def store_youtube_comments(video_id):
    comments = get_video_comments(video_id)
    return jsonify(comments=comments)


import random
import requests
from bs4 import BeautifulSoup
from textblob import TextBlob
from flask import render_template, session, redirect, url_for


def scrape_reviews(website_url):
    response = requests.get(website_url)
    soup = BeautifulSoup(response.content, 'html.parser')

    reviews = []
    
    for review_div in soup.find_all('div', class_='a-row a-spacing-small'):
        review_text = review_div.get_text(strip=True)
        reviews.append(review_text)

    return reviews


from textblob import TextBlob


def perform_sentiment_analysis(comment):
    
    blob = TextBlob(comment)
   
    polarity = blob.sentiment.polarity

    if polarity > 0:
        return 'positive', polarity
    elif polarity < 0:
        return 'negative', polarity
    else:
        return 'neutral', polarity

def analyze_sentiment(comments):
    sentiments = []
    for comment in comments:
        sentiment, confidence = perform_sentiment_analysis(comment)  
        sentiments.append((sentiment, confidence))  
    return sentiments


@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    role = session.get('role')
    
    connection = get_db_connection()
    cursor = connection.cursor()
    cursor.execute('SELECT sentiment, COUNT(*) FROM feedback GROUP BY sentiment')
    sentiment_data = cursor.fetchall()

    print("Sentiment Data:", sentiment_data)

    labels = ['Positive', 'Negative', 'Neutral']
    data = [0, 0, 0] 

    # Ensure sentiment_data is in the expected format and handle unexpected results
    for sentiment_row in sentiment_data:
        print(f"Processing row: {sentiment_row}")  # Debugging line to see row data
        if len(sentiment_row) == 2:  # Check if the row has exactly two columns
            sentiment, count = sentiment_row
            if sentiment == 'positive':
                data[0] = count
            elif sentiment == 'negative':
                data[1] = count
            elif sentiment == 'neutral':
                data[2] = count
        else:
            print(f"Skipping row with unexpected structure: {sentiment_row}")

    user_feedback_chart = {
        "data": {
            "labels": labels,
            "datasets": [{
                "label": "User Feedback Sentiment Distribution",
                "data": data,
                "backgroundColor": ["#4caf50", "#f44336", "#ffeb3b"],
                "borderColor": ["#388e3c", "#c62828", "#fbc02d"],
                "borderWidth": 1
            }]
        }
    }

    # YouTube sentiment analysis for Spiderman and Bahubali
    spiderman_video_id = 'JfVOs4VSpmA'  # Spiderman Trailer
    bahubali_video_id = 'sOEg_YZQsTI'  # Bahubali Trailer

    spiderman_comments = get_video_comments(spiderman_video_id)
    bahubali_comments = get_video_comments(bahubali_video_id)
    if not spiderman_comments:
        print("No comments found for Spiderman")
    if not bahubali_comments:
        print("No comments found for Bahubali")

    # Sentiment analysis for Spiderman and Bahubali comments
    spiderman_sentiments = {'positive': 0, 'negative': 0, 'neutral': 0}
    bahubali_sentiments = {'positive': 0, 'negative': 0, 'neutral': 0}
    
    for comment in spiderman_comments:
        sentiment, confidence = analyze_sentiment([comment])[0]  # Unpack first element
        spiderman_sentiments[sentiment] += 1

    for comment in bahubali_comments:
        sentiment, confidence = analyze_sentiment([comment])[0]  # Unpack first element
        bahubali_sentiments[sentiment] += 1

    # Sentiment chart for Spiderman
    spiderman_chart = {
        "data": {
            "labels": labels,
            "datasets": [{
                "label": "Spiderman Trailer Comments Sentiment",
                "data": [spiderman_sentiments['positive'], spiderman_sentiments['negative'], spiderman_sentiments['neutral']],
                "backgroundColor": ["#4caf50", "#f44336", "#ffeb3b"],
                "borderColor": ["#388e3c", "#c62828", "#fbc02d"],
                "borderWidth": 1
            }]
        }
    }

    # Sentiment chart for Bahubali
    bahubali_chart = {
        "data": {
            "labels": labels,
            "datasets": [{
                "label": "Bahubali Trailer Comments Sentiment",
                "data": [bahubali_sentiments['positive'], bahubali_sentiments['negative'], bahubali_sentiments['neutral']],
                "backgroundColor": ["#4caf50", "#f44336", "#ffeb3b"],
                "borderColor": ["#388e3c", "#c62828", "#fbc02d"],
                "borderWidth": 1
            }]
        }
    }


    clothing_labels = ["T-shirts", "Jeans", "Jackets", "Sweaters", "Shorts"]
    jewelry_labels = ["Necklaces", "Earrings", "Bracelets", "Rings", "Watches"]
    
    clothing_data = [random.randint(10, 50) for _ in range(len(clothing_labels))]
    jewelry_data = [random.randint(5, 20) for _ in range(len(jewelry_labels))]

    clothing_chart = {
        "data": {
            "labels": clothing_labels,
            "datasets": [{
                "label": "Clothing Sentiment",
                "data": clothing_data,
                "backgroundColor": ["#FFCD38", "#FF5959", "#7D5B29", "#3B9F8B", "#4DB8FF"],
                "borderColor": ["#F5B800", "#FF2A2A", "#9F4B1F", "#33A84B", "#0288D1"],
                "borderWidth": 1
            }]
        }
    }

    jewelry_chart = {
        "data": {
            "labels": jewelry_labels,
            "datasets": [{
                "label": "Jewelry Sentiment",
                "data": jewelry_data,
                "backgroundColor": ["#73C6B6", "#DA4E2A", "#FF82A2", "#8E44AD", "#F39C12"],
                "borderColor": ["#1B5E20", "#C62828", "#C2185B", "#6A1B9A", "#F39C12"],
                "borderWidth": 1
            }]
        }
    }


    cursor.close()
    connection.close()

    return render_template('dashboard.html',
                           role=role,
                           user_feedback_chart=user_feedback_chart,
                           spiderman_chart=spiderman_chart,  
                           bahubali_chart=bahubali_chart,    
                           clothing_chart=clothing_chart,
                           jewelry_chart=jewelry_chart,
    )

# Routes for user login, feedback submission, YouTube comment management, etc. as before

# Create admin user (Once only)
@app.route('/create_admin')
def create_admin():
    if create_user('admin', 'admin_password', 'admin'):
        return 'Admin user created successfully.'
    else:
        return 'Admin user already exists.'

# Logout Route
@app.route('/logout')
def logout():
    session.clear()  
    return redirect(url_for('login'))  

if __name__ == "__main__":
    app.run(debug=True)
