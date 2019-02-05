from flask import render_template, flash, redirect, url_for, request
from app import app, db
from app.forms import LoginForm, RegistrationForm, UnosProizvodaForm
from flask_login import current_user, login_user, logout_user, login_required
from app.models import User, Proizvod
from werkzeug.urls import url_parse
from datetime import datetime

@app.route('/')
@app.route('/index')
def index():
	return render_template('index.html', title='Home')

@app.route('/login', methods=['GET', 'POST'])
def login():
	if current_user.is_authenticated:
		return redirect(url_for('index'))
	form = LoginForm()
	if form.validate_on_submit():
		user = User.query.filter_by(username=form.username.data).first()
		if user is None or not user.check_password(form.password.data):
			flash('Netočno korisničko ime ili lozinka!')
			return redirect(url_for('login'))
		login_user(user, remember=form.remember_me.data)
		next_page = request.args.get('next')
		if not next_page or url_parse(next_page).netloc != '':
			next_page = url_for('index')
		return redirect(next_page)
	return render_template('login.html', title='Prijavi se', form=form)

@app.route('/logout')
def logout():
	logout_user()
	return redirect(url_for('index'))

@app.route('/register', methods=['GET', 'POST'])
def register():
	if current_user.is_authenticated:
		return redirect(url_for('index'))
	form = RegistrationForm()
	if form.validate_on_submit():
		user = User(username=form.username.data, email=form.email.data)
		user.set_password(form.password.data)
		db.session.add(user)
		db.session.commit()
		flash('Sada ste registrirani korisnik!')
		return redirect(url_for('login'))
	return render_template('register.html', title='Registriraj se', form=form)

@app.route('/user/<username>')
@login_required
def user(username):
	user = User.query.filter_by(username=username).first_or_404()
	return render_template('user.html', user=user)

@app.before_request
def before_request():
	if current_user.is_authenticated:
		current_user.last_seen = datetime.utcnow()
		db.session.commit()

@app.route('/unos_proizvoda', methods=['GET', 'POST'])
@login_required
def unos_proizvoda():
	form = UnosProizvodaForm()
	if form.validate_on_submit():
		proizvod = Proizvod(name=form.name.data, kolicina=form.kolicina.data)
		db.session.add(proizvod)
		db.session.commit()
		flash('Dodali ste proizvod!')
		return redirect(url_for('unos_proizvoda'))
	return render_template('unos_proizvoda.html', title='Dodaj proivod', form=form)

@app.route('/stanje_skladista')
@login_required
def stanje_skladista():
	proizvodi = Proizvod.query.all()
	return render_template('stanje_skladista.html', title='Stanje skladista', proizvodi=proizvodi)