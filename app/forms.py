from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, TextAreaField
from wtforms.validators import DataRequired, Length, EqualTo, Optional

class RegisterForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired(), Length(min=3, max=20)])
    password = PasswordField('Password', validators=[DataRequired(), Length(min=6)])
    confirm_password = PasswordField('Confirm Password', validators=[DataRequired(), EqualTo('password', message='Passwords must match')])
    full_name = StringField('Full Name', validators=[DataRequired(), Length(min=3, max=100)])
    bio = TextAreaField('Bio', validators=[Length(max=300)])

class LoginForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired(), Length(min=3, max=20)])
    password = PasswordField('Password', validators=[DataRequired()])

class PostForm(FlaskForm):
    title = StringField('Title', validators=[DataRequired(), Length(min=3, max=100)])
    desc = TextAreaField('Description', validators=[DataRequired(), Length(min=3, max=500)])

class EditProfileForm(FlaskForm):
    username = StringField(
        'Username',
        validators=[DataRequired(), Length(min=3, max=20, message="Username must be between 3 and 20 characters.")]
    )
    password = PasswordField(
        'Password',
        validators=[Optional(), Length(min=6, max=60, message="Password must be between 6 and 60 characters.")]
    )
    full_name = StringField(
        'Full Name',
        validators=[DataRequired(), Length(min=3, max=30, message="Full name must be between 3 and 30 characters.")]
    )
    bio = TextAreaField(
        'Bio',
        validators=[Optional(), Length(max=60, message="Bio cannot exceed 60 characters.")]
    )

