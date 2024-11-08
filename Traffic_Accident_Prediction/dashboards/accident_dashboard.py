import plotly.express as px
import pandas as pd
from models import db, Accident

def get_accident_data():
    accidents = Accident.query.all()
    data = [{'latitude': acc.latitude, 'longitude': acc.longitude} for acc in accidents]
    return pd.DataFrame(data)

def create_accident_heatmap():
    df = get_accident_data()
    fig = px.density_mapbox(df, lat='latitude', lon='longitude', z='density', radius=10)
    return fig
