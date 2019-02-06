from flask_wtf import FlaskForm
from wtforms import StringField, IntegerField, PasswordField, BooleanField, SubmitField, HiddenField
from wtforms.validators import ValidationError, DataRequired, Email, EqualTo
from app.models import User, Proizvod

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

class UnosProizvodaForm(FlaskForm):
	name = StringField('Naziv proizvoda', validators=[DataRequired()])
	kolicina = IntegerField('Kolicina', validators=[DataRequired()])
	zemlja_podrijetla = StringField('Zemlja podrijetla', validators=[DataRequired()])
	oib = IntegerField('OIB', validators=[DataRequired()])
	submit = SubmitField()

class UnosDobavljacaForm(FlaskForm):
	name = StringField('Naziv tvrtke', validators=[DataRequired()])
	oib = IntegerField('OIB', validators=[DataRequired()])
	grad = StringField('Grad', validators=[DataRequired()])
	p_broj = IntegerField('Poštanski broj', validators=[DataRequired()])
	drzava = StringField('Država', validators=[DataRequired()])
	submit = SubmitField()

class UlazRobeForm(FlaskForm):
	promijenjena_kolicina = IntegerField('Kolicina', validators=[DataRequired()])
	oib = IntegerField('OIB', validators=[DataRequired()])
	submit1 = SubmitField()
	
class IzlazRobeForm(FlaskForm):
	promijenjena_kolicina = IntegerField('Kolicina', validators=[DataRequired()])
	oib = IntegerField('OIB', validators=[DataRequired()])
	submit2 = SubmitField()