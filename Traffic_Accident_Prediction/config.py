class Config:
    SECRET_KEY = '77ba28f566eb984e43d93e49bdbf2f3e'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_DATABASE_URI = 'postgresql://postgres:new_password@localhost/traffic_db'
    #SQLALCHEMY_DATABASE_URI = 'sqlite:///traffic_db.sqlite'  # SQLite connection URI