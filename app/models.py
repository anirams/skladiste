from app import db, login
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin
from app.search import add_to_index, remove_from_index, query_index

class User(UserMixin, db.Model):
	id = db.Column(db.Integer, primary_key=True)
	username = db.Column(db.String(64), index=True, unique=True)
	email = db.Column(db.String(120), index=True, unique=True)
	password_hash = db.Column(db.String(128))
	last_seen = db.Column(db.DateTime, default=datetime.utcnow)
	evidencija_unosa = db.relationship('EvidencijaUnosa', backref='user', lazy='dynamic')
	evidencija_izdavanja = db.relationship('EvidencijaIzdavanja', backref='user', lazy='dynamic')

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
	kolicina = db.Column(db.Integer)
	zemlja_podrijetla = db.Column(db.String(64))
	datum_unosa = db.Column(db.DateTime, default=datetime.utcnow)
	evidencija_unosa = db.relationship('EvidencijaUnosa', backref='proizvod', lazy='dynamic')
	evidencija_izdavanja = db.relationship('EvidencijaIzdavanja', backref='proizvod', lazy='dynamic')

class Dobavljac(db.Model):
	id = db.Column(db.Integer, primary_key=True)
	name = db.Column(db.String(64), unique=True)
	oib = db.Column(db.Integer, unique=True)
	grad = db.Column(db.String(64))
	p_broj = db.Column(db.Integer)
	drzava = db.Column(db.String(64))
	evidencija = db.relationship('EvidencijaUnosa', backref='dobavljac', lazy='dynamic')

class EvidencijaUnosa(db.Model):
	id = db.Column(db.Integer, primary_key=True)
	proizvod_id = db.Column(db.Integer, db.ForeignKey('proizvod.id'))
	dobavljac_id = db.Column(db.Integer, db.ForeignKey('dobavljac.id'))
	promijenjena_kolicina = db.Column(db.Integer)
	datum_unosa = db.Column(db.DateTime, default=datetime.utcnow)
	user_id = db.Column(db.Integer, db.ForeignKey('user.id'))

class Kupac(db.Model):
	id = db.Column(db.Integer, primary_key=True)
	name = db.Column(db.String(64), unique=True)
	oib = db.Column(db.Integer, unique=True)
	grad = db.Column(db.String(64))
	p_broj = db.Column(db.Integer)
	drzava = db.Column(db.String(64))
	evidencija = db.relationship('EvidencijaIzdavanja', backref='kupac', lazy='dynamic')

class EvidencijaIzdavanja(db.Model):
	id = db.Column(db.Integer, primary_key=True)
	proizvod_id = db.Column(db.Integer, db.ForeignKey('proizvod.id'))
	kupac_id = db.Column(db.Integer, db.ForeignKey('kupac.id'))
	promijenjena_kolicina = db.Column(db.Integer)
	datum_unosa = db.Column(db.DateTime, default=datetime.utcnow)
	user_id = db.Column(db.Integer, db.ForeignKey('user.id'))