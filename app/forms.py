from flask_wtf import FlaskForm
from wtforms import StringField, IntegerField, PasswordField, BooleanField, SubmitField, HiddenField, TextAreaField
from wtforms.validators import ValidationError, DataRequired, Email, EqualTo, Length, NumberRange
from app.models import User, Proizvod, Tvrtka, Evidencija
from flask import request
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import current_user

class LoginForm(FlaskForm):
	username = StringField('Korisnicko ime', validators=[DataRequired('Ovo polje je nužno')])
	password = PasswordField('Lozinka', validators=[DataRequired('Ovo polje je nužno')])
	remember_me = BooleanField('Zapamti me')
	submit = SubmitField('Prijavi se')


class RegistrationForm(FlaskForm):
	username = StringField('Korisnicko ime', validators=[DataRequired('Ovo polje je nužno')])
	email = StringField('Email', validators=[DataRequired('Ovo polje je nužno'), Email('Unesite valjanu email adresu')])
	password = PasswordField('Lozinka', validators=[DataRequired('Ovo polje je nužno'), Length(min=5, max=35)])
	password2 = PasswordField(
		'Ponovite lozinku', validators=[DataRequired('Ovo polje je nužno'), EqualTo('password', message='Lozinke moraju biti jednake')])
	submit = SubmitField('Registriraj se')

	def validate_username(self, username):
		user = User.query.filter_by(username=username.data).first()
		if user is not None:
			raise ValidationError('Korisnicko ime je zauzeto!')

	def validate_email(self, email):
		user = User.query.filter_by(email=email.data).first()
		if user is not None:
			raise ValidationError('Korisnik sa ovom email adresom je vec registriran!')

	def validate_admin(self, email):
		if current_user.username is not "admin":
			raise ValidationError('Niste admin!')


class UnosProizvodaForm(FlaskForm):
	name = StringField('Naziv proizvoda', validators=[DataRequired('Unesi Naziv Proizvoda')])
	#promijenjena_kolicina = IntegerField('Kolicina', validators=[DataRequired('Unesi Količinu (broj)')])
	opis_proizvoda = StringField ('Opis proizvoda')
	zemlja_podrijetla = StringField('Zemlja podrijetla', validators=[DataRequired('Unesi Zemlju Podrijetla')])
	#oib = IntegerField('OIB', validators=[DataRequired('Unesi OIB Tvrtke (broj)')])
	#dodaj_jos = SubmitField('Dodaj jos')
	submit2 = SubmitField('Dodaj Proizvod')
	def validate(self):
		rv = FlaskForm.validate(self)
		if not rv:
			return False
		proizvod = Proizvod.query.filter_by(name=self.name.data).first()
		if proizvod is not None:
			self.name.errors.append('Proizvod pod tim imenom već postoji')
			return False
		#tvrtka = Tvrtka.query.filter_by(oib=self.oib.data).first()
		#if tvrtka is None:
			#self.oib.errors.append('Tvrtka ne postoji')
			#return False
		else:
			return True

class UnosTvrtkeForm(FlaskForm):
	name = StringField('Naziv tvrtke', validators=[DataRequired('Unesi ime tvrtke')])
	oib = IntegerField('OIB', validators=[DataRequired('Unesi OIB tvrtke'), NumberRange(min=10000000000, max=99999999999, message='Invalid length')])
	adresa = StringField('Adresa', validators=[DataRequired('Unesi adresu')])
	grad = StringField('Grad', validators=[DataRequired('Unesi grad')])
	p_broj = IntegerField('Poštanski broj', validators=[DataRequired('Unesi poštanski broj')])
	drzava = StringField('Država', validators=[DataRequired('Unesi državu')])
	submit = SubmitField('Stvori Tvrtku')
	def validate(self):
		rv = FlaskForm.validate(self)
		if not rv:
			return False
		tvrtka = Tvrtka.query.filter_by(oib=self.oib.data).first()
		if tvrtka is not None:
			self.oib.errors.append('Tvrtka pod tim oib-om već postoji')
			return False
		else:
			return True

class UrediTvrtkuForm(FlaskForm):
	name = StringField('Naziv tvrtke', validators=[DataRequired('Unesi ime tvrtke')])
	oib = IntegerField('OIB', validators=[DataRequired('Unesi OIB tvrtke'), NumberRange(min=10000000000, max=99999999999, message='Invalid length')])
	adresa = StringField('Adresa', validators=[DataRequired('Unesi adresu')])
	grad = StringField('Grad', validators=[DataRequired('Unesi grad')])
	p_broj = IntegerField('Poštanski broj', validators=[DataRequired('Unesi poštanski broj')])
	drzava = StringField('Država', validators=[DataRequired('Unesi državu')])
	submit3 = SubmitField('Uredi')
	def validate(self):
		rv = FlaskForm.validate(self)
		if not rv:
			return False		
		return True

class UlazRobeForm(FlaskForm):
	promijenjena_kolicina = IntegerField('Kolicina', validators=[DataRequired('Unesi količinu')])
	oib = IntegerField('OIB', validators=[DataRequired('Unesi OIB tvrtke')])
	submit1 = SubmitField('Dodaj')
	def validate(self):
		rv = FlaskForm.validate(self)
		if not rv:
			return False
		tvrtka = Tvrtka.query.filter_by(
			oib=self.oib.data).first()
		if tvrtka is None:
			self.oib.errors.append('Tvrtka ne postoji')
			return False
		else:
			return True

class IzlazRobeForm(FlaskForm):
	promijenjena_kolicina = IntegerField('Kolicina', validators=[DataRequired('Unesi količinu')])
	oib = IntegerField('OIB', validators=[DataRequired('Unesi OIB tvrtke')])
	proizvod_id = HiddenField()
	submit2 = SubmitField('Oduzmi')
	def validate(self):
		rv = FlaskForm.validate(self)
		if not rv:
			return False

		proizvod = Proizvod.query.get(self.proizvod_id.data)
		if proizvod.kolicina < self.promijenjena_kolicina.data:
			self.promijenjena_kolicina.errors.append('Nema dovoljno artikla na stanju')
			return False

		tvrtka = Tvrtka.query.filter_by(oib=self.oib.data).first()
		if tvrtka is None:
			self.oib.errors.append('Tvrtka ne postoji')
			return False
		else:
			return True

class UrediProizvodForm(FlaskForm):
	name = StringField('Naziv proizvoda', validators=[DataRequired('Unesi Naziv Proizvoda')])
	zemlja_podrijetla = StringField('Zemlja podrijetla')
	opis_proizvoda = TextAreaField('Opis proizvoda')
	submit3 = SubmitField('Uredi')
	def validate(self):
		rv = FlaskForm.validate(self)
		if not rv:
			return False		
		return True

class SearchForm(FlaskForm):
	search = StringField(('Pronađi Proizvod'), validators=[DataRequired('Unesi ime proizvoda')])
	submit = SubmitField('Pronađi')

class SearchFormKorisnik(FlaskForm):
	search = StringField(('Pronađi Proizvod'), validators=[DataRequired('Unesi ime korisnika')])
	submit = SubmitField('Pronađi')

class SearchFormTvrtka(FlaskForm):
	search = StringField(('Pronađi Tvrtku'), validators=[DataRequired('Unesi ime tvrtke')])
	submit2 = SubmitField('Pronađi')


class EditPasswordForm(FlaskForm):
	old_password = PasswordField('Stara Lozinka', validators=[DataRequired()])
	username = HiddenField()
	password = PasswordField('Lozinka', validators=[DataRequired()])
	password2 = PasswordField(
		'Ponovite lozinku', validators=[DataRequired(), EqualTo('password')])
	
	def validate(self):
		user1 = User.query.filter_by(username=self.username.data).first()
		rv = FlaskForm.validate(self)
		if not rv:
			return False
		if not check_password_hash(user1.password_hash, self.old_password.data):
			self.old_password.errors.append('Krivi password')
			return False
		else:
			return True
	submit = SubmitField()

class ListForm(FlaskForm):
	listaProizvoda=HiddenField(validators=[DataRequired()])
	submit = SubmitField('Potvrdi')