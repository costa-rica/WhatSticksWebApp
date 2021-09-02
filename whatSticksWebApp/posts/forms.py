from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed #used for image uploading
from wtforms import StringField, PasswordField, SubmitField, BooleanField\
    , TextAreaField, DateTimeField, FloatField, DateField, TimeField
from wtforms.validators import DataRequired, Length, Email, EqualTo, ValidationError
from wtforms_sqlalchemy.fields import QuerySelectField
# from dmrApp.models import User, Restaurants, Employeeroles
from flask_login import current_user
from datetime import datetime
from whatSticksWebApp import db

from flask_wtf.file import FileField, FileAllowed #used for image uploading

placeholderMessage="""Enter error or new featuer request here...
"""

class PostForm(FlaskForm):
    title = StringField('Title',validators=[DataRequired()])
    content = TextAreaField('Content',validators=[DataRequired()], render_kw={'placeholder':placeholderMessage})
    picture = FileField('Upload Screenshot', validators = [FileAllowed(['jpg','png'])])
    submit = SubmitField('Post')
    