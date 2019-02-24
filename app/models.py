from app import db, login
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin

class User(UserMixin, db.Model):
	id = db.Column(db.Integer, primary_key=True)
	username = db.Column(db.String(64), index=True, unique=True)
	email = db.Column(db.String(120), index=True, unique=True)
	password_hash = db.Column(db.String(128))
	last_seen = db.Column(db.DateTime, default=datetime.utcnow)
	evidencija = db.relationship('Evidencija', backref='user', lazy='dynamic')

	def __repr__(self):
		return '<User {}>'.format(self.username)  

	def set_password(self, password):
		self.password_hash = generate_password_hash(password)

	def check_password(self, password):
		return check_password_hash(self.password_hash, password)

@login.user_loader
def load_user(id):
	return User.query.get(int(id))

class Proizvod(db.Model):
	__searchable__ = ['name']
	id = db.Column(db.Integer, primary_key=True)
	name = db.Column(db.String(64))
	kolicina = db.Column(db.Integer, default=0)
	zemlja_podrijetla = db.Column(db.String(64))
	opis_proizvoda = db.Column(db.String(300))
	datum_unosa = db.Column(db.DateTime, default=datetime.utcnow)
	evidencija = db.relationship('Evidencija', backref='proizvod', lazy='dynamic')

class Tvrtka(db.Model):
	__searchable__ = ['name']
	id = db.Column(db.Integer, primary_key=True)
	name = db.Column(db.String(64))
	oib = db.Column(db.Integer, unique=True)
	grad = db.Column(db.String(64))
	p_broj = db.Column(db.Integer)
	drzava = db.Column(db.String(64))
	evidencija = db.relationship('Evidencija', backref='tvrtka', lazy='dynamic')

class Evidencija(db.Model):
	id = db.Column(db.Integer, primary_key=True)
	proizvod_id = db.Column(db.Integer, db.ForeignKey('proizvod.id'))
	tvrtka_id = db.Column(db.Integer, db.ForeignKey('tvrtka.id'))
	promijenjena_kolicina = db.Column(db.Integer)
	trenutna_kolicina = db.Column(db.Integer)
	datum_unosa = db.Column(db.DateTime, default=datetime.utcnow)
	vrsta_unosa = db.Column(db.String(64))
	user_id = db.Column(db.Integer, db.ForeignKey('user.id'))


#class Receipt(db.Model):
	#evidencija_id = db.Column(db.Integer, db.ForeignKey('evidencija.id'))
	#user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
	#receipt_type = db.Column(db.String(64))