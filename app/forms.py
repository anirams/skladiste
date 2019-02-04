from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, SubmitField
from wtforms.validators import ValidationError, DataRequired, Email, EqualTo
from app.models import User

class LoginForm(FlaskForm):
	username = StringField('Korisnicko ime', validators=[DataRequired()])
	password = PasswordField('Lozinka', validators=[DataRequired()])
	remember_me = BooleanField('Zapamti me')
	submit = SubmitField('Prijavi se')

class RegistrationForm(FlaskForm):
	username = StringField('Korisnicko ime', validators=[DataRequired()])
	email = StringField('Email', validators=[DataRequired(), Email()])
	password = PasswordField('Lozinka', validators=[DataRequired()])
	password2 = PasswordField(
		'Ponovite lozinku', validators=[DataRequired(), EqualTo('password')])
	submit = SubmitField('Registriraj se')

	def validate_username(self, username):
		user = User.query.filter_by(username=username.data).first()
		if user is not None:
			raise ValidationError('Korisnicko ime je zauzeto!')

	def validate_email(self, email):
		user = User.query.filter_by(email=email.data).first()
		if user is not None:
			raise ValidationError('Korisnik sa ovom email adresom je vec registriran!')