from whatSticksWebApp import db, login_manager
from datetime import datetime, date
from itsdangerous import TimedJSONWebSignatureSerializer as Serializer
from flask import current_app
from flask_login import UserMixin

from flask_script import Manager

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))
    

class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.Text, unique=True)
    email = db.Column(db.Text, unique=True, nullable=False)
    image_file = db.Column(db.Text,nullable=False, default='default.jpg')
    password = db.Column(db.Text, nullable=False)
    user_timezone = db.Column(db.Text, default='US/Eastern')
    permission = db.Column(db.Text)
    theme = db.Column(db.Text)
    time_stamp = db.Column(db.DateTime, default=datetime.now)
    posts = db.relationship('Post', backref='author', lazy=True)
    variable = db.relationship('Health_description', backref='users_health_data', lazy=True)
    # track_inv = db.relationship('Tracking_inv', backref='updator_inv', lazy=True)


    def get_reset_token(self, expires_sec=1800):
        s=Serializer(current_app.config['SECRET_KEY'], expires_sec)
        return s.dumps({'user_id': self.id}).decode('utf-8')

    @staticmethod
    def verify_reset_token(token):
        s=Serializer(current_app.config['SECRET_KEY'])
        try:
            user_id = s.loads(token)['user_id']
        except:
            return None
        return User.query.get(user_id)

    def __repr__(self):
        return f"User('{self.id}', email:'{self.email}', permission:'{self.permission}', user_timezone: '{self.user_timezone}')"

class Post(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title= db.Column(db.String(100), nullable=False)
    date_posted = db.Column(db.DateTime, nullable=False, default=datetime.now)
    content = db.Column(db.Text)
    screenshot = db.Column(db.String(100))
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

    def __repr__(self):
        return f"Post('{self.title}','{self.date_posted}')"


class Health_description(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    datetime_of_activity=db.Column(db.DateTime)
    var_activity = db.Column(db.Text) #walking, running, empty is ok for something like mood
    var_type = db.Column(db.Text) #heart rate, mood, weight, etc.
    var_periodicity = db.Column(db.Text)
    var_timezone_utc_delta_in_mins = db.Column(db.Float) #difference bewteen utc and timezone of exercise
    time_stamp_utc = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    user_id=db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    source_filename =db.Column(db.Text)
    metric1_carido=db.Column(db.Float)
    metric2_session_duration=db.Column(db.Float)
    metric3=db.Column(db.Float)
    metric4=db.Column(db.Float)
    metric5=db.Column(db.Float)
    note=db.Column(db.Text)

    def __repr__(self):
        return f"Health_description('{self.id}',var_activity:'{self.var_activity}'," \
        f"'var_type: {self.var_type}', datetime_of_activity: '{self.datetime_of_activity}', time_stamp_utc: '{self.time_stamp_utc}')"
    


class Health_measure(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    description_id=db.Column(db.Integer, db.ForeignKey('health_description.id'), nullable=False)
    var_datetime_utc = db.Column(db.DateTime, nullable=True)
    var_value = db.Column(db.Text)
    var_unit = db.Column(db.Text)
    var_type = db.Column(db.Text)
    heart_rate = db.Column(db.Integer)
    speed=db.Column(db.Float)
    distance=db.Column(db.Float)
    longitude=db.Column(db.Float)
    latitude=db.Column(db.Float)
    altitude=db.Column(db.Float)
    
    def __repr__(self):
        return f"Variables('{self.id}',description_id:'{self.description_id}'," \
        f"'var_datetime_utc: {self.var_datetime_utc}', var_value: '{self.var_value}')"
        
        
        
        

