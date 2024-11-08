from flask import Flask, render_template, redirect, url_for, request, session
from models import db, User, Feedback
from flask_migrate import Migrate
import plotly.express as px
import requests 
from requests.exceptions import RequestException
import pandas as pd
from config import Config

app = Flask(__name__)
app.config.from_object(Config)
db.init_app(app)
migrate = Migrate(app, db)

# Example for login route
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        user = User.query.filter_by(username=username).first()
        if user and user.password == password:
            session['user_id'] = user.id
            session['role'] = user.role  # Store user role in session
            return redirect(url_for('dashboard'))  # Redirect to appropriate dashboard

    return render_template('login.html')

import logging
logging.basicConfig(level=logging.DEBUG)

# Admin Dashboard Route (accessible only by admins)
import json
@app.route('/admin/dashboard')
def admin_dashboard():
    if 'role' not in session or session['role'] != 'admin':
        return redirect(url_for('index'))

    # Get the accident data
    accident_by_location = db.session.query(Accident.location, db.func.count(Accident.id).label('accident_count')).group_by(Accident.location).all()
    locations = [accident.location for accident in accident_by_location]
    counts = [accident.accident_count for accident in accident_by_location]

    return render_template('admin_dashboard.html', 
                           accident_by_location=json.dumps(locations),
                           accident_count=json.dumps(counts))

@app.route('/user/dashboard')
def user_dashboard():
    recent_accidents = get_recent_accidents()  
    accident_severity = get_accident_severity()  
    
    return render_template('user_dashboard.html', 
                           recent_accidents=recent_accidents,
                           accident_severity=accident_severity)

from flask import request, redirect, url_for
from flask_login import login_required, current_user
from models import db, Feedback

@app.route('/submit_feedback', methods=['POST'])
@login_required  
def submit_feedback():
    feedback = request.form['feedback']
    new_feedback = Feedback(feedback_text=feedback, user_id=current_user.id)
    db.session.add(new_feedback)
    db.session.commit()

    return redirect(url_for('user_dashboard')) 

@app.route('/logout')
def logout():
    session.clear()  
    return redirect(url_for('index'))

@app.route('/charts')
def charts():
    try:
        # Load data from CSV file
        csv_data = pd.read_csv('etl/Cleandata.csv')
        
        # Chart 1: Accident Severity Distribution (from CSV data)
        severity_data = csv_data['Severity'].value_counts().reset_index()
        severity_data.columns = ['Severity', 'Count']
        chart_csv = px.pie(severity_data, names='Severity', values='Count', title='Accident Severity Distribution from CSV')
        chart_csv_div = chart_csv.to_html(full_html=False)

        # Load data from API
        api_url = "https://transport-statistics.api.gov.uk/road-accidents"
        response = requests.get(api_url)
        
        if response.status_code == 200:
            try:
                
                api_data = response.json()
                
                if api_data:
                    api_df = pd.DataFrame(api_data)
                    
                   
                    if 'accident_type' in api_df.columns:
                        accident_type_data = api_df['accident_type'].value_counts().reset_index()
                        accident_type_data.columns = ['Accident Type', 'Count']
                        chart_api = px.bar(accident_type_data, x='Accident Type', y='Count', title='Accident Type Distribution from API')
                    else:
                        
                        chart_api = px.bar(pd.DataFrame({'Accident Type': ['No Data'], 'Count': [0]}), 
                                           x='Accident Type', y='Count', title='No API Data Available')
                else:
                    
                    chart_api = px.bar(pd.DataFrame({'Accident Type': ['No Data'], 'Count': [0]}), 
                                       x='Accident Type', y='Count', title='API Returned Empty Data')

            except ValueError:
                
                print("Error: Invalid JSON response from API.")
                chart_api = px.bar(pd.DataFrame({'Accident Type': ['No Data'], 'Count': [0]}), 
                                   x='Accident Type', y='Count', title='Invalid API Data Format')
                
        else:
            
            print(f"Error: API request failed with status {response.status_code}.")
            chart_api = px.bar(pd.DataFrame({'Accident Type': ['No Data'], 'Count': [0]}), 
                               x='Accident Type', y='Count', title='API Request Failed')
        
        chart_api_div = chart_api.to_html(full_html=False)
       
        return render_template('charts.html', chart_csv_div=chart_csv_div, chart_api_div=chart_api_div)

    except Exception as e:
        print(f"An error occurred: {e}")
        return "Internal Server Error", 500


csv_data = pd.read_csv('etl/Cleandata.csv')
print(csv_data.head())

print(csv_data.columns)  #
print(csv_data['Severity'].head())  

if __name__ == '__main__':
    app.run(debug=True)
