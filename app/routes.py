from flask import render_template, flash, redirect, url_for, request, send_file
from app import app, db
from app.forms import LoginForm, RegistrationForm, UlazRobeForm, IzlazRobeForm, UnosProizvodaForm, SearchForm, EditPasswordForm, UnosTvrtkeForm
from flask_login import current_user, login_user, logout_user, login_required
from app.models import User, Proizvod, Tvrtka, Evidencija
from werkzeug.urls import url_parse
from datetime import datetime
import flask_excel as excel
from sqlalchemy import text
import pdfkit
from flask_paginate import Pagination, get_page_parameter, get_page_args
from sqlalchemy import text

config = pdfkit.configuration(wkhtmltopdf="C:/Program Files/wkhtmltopdf/bin/wkhtmltopdf.exe")

excel.init_excel(app)

@app.route('/index')
def index():
	return render_template('index.html', title='Home')

@app.route('/', methods=['GET', 'POST'])
@app.route('/login', methods=['GET', 'POST'])
def login():
	if current_user.is_authenticated:
		#flash(f'Korisnik { form.username.data } je ulogiran!', 'success')
		return redirect(url_for('index'))
	form = LoginForm()
	if form.validate_on_submit():
		user = User.query.filter_by(username=form.username.data).first()
		if user is None or not user.check_password(form.password.data):
			flash(f'Netočno korisničko ime ili lozinka!', 'danger')
			return redirect(url_for('login'))
		login_user(user, remember=form.remember_me.data)
		next_page = request.args.get('next')
		if not next_page or url_parse(next_page).netloc != '':
			next_page = url_for('index')
			flash(f'Korisnik { form.username.data } je ulogiran!', 'success')
		return redirect(next_page)
	return render_template('login.html', title='Prijavi se', form=form)

@app.route('/logout')
def logout():
	logout_user()
	return redirect(url_for('login'))

@app.route('/register', methods=['GET', 'POST'])
def register():
	if not current_user.is_authenticated:
		return redirect(url_for('login'))
	if current_user.username != "admin":
		return redirect(url_for('index'))
	form = RegistrationForm()
	if form.validate_on_submit():
		user = User(username=form.username.data, email=form.email.data)
		user.set_password(form.password.data)
		db.session.add(user)
		db.session.commit()
		flash(f'Registrirali ste korisnika {form.username.data}!', 'success')
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
		proizvod = Proizvod(name=form.name.data, zemlja_podrijetla=form.zemlja_podrijetla.data, kolicina=form.kolicina.data)
		db.session.add(proizvod)
		db.session.commit()
		proizvod = Proizvod.query.filter_by(name=form.name.data).first()
		tvrtka = Tvrtka.query.filter_by(oib=form.oib.data).first()
		evidencija = Evidencija(proizvod_id=proizvod.id, promijenjena_kolicina=proizvod.kolicina, tvrtka_id=tvrtka.id, user_id=current_user.id, vrsta_unosa='unos', trenutna_kolicina=proizvod.kolicina)
		db.session.add(evidencija)
		db.session.commit()
		tvrtka = Tvrtka.query.all()
		flash(f'Dodali ste proizvod {form.name.data}!', 'success')
		return redirect(url_for('unos_proizvoda'))
	return render_template('unos_proizvoda.html', title='Dodaj proizvod', form=form)

@app.route('/proizvod/<name>', methods=['GET', 'POST'])
@login_required
def proizvod(name):
	proizvod = Proizvod.query.filter_by(name=name).first_or_404()
	evidencijaUlaz = Evidencija.query.filter_by(proizvod_id=proizvod.id, vrsta_unosa='unos').order_by(Evidencija.datum_unosa.desc()).all()
	evidencijaIzlaz = Evidencija.query.filter_by(proizvod_id=proizvod.id, vrsta_unosa='izlaz').order_by(Evidencija.datum_unosa.desc()).all()
	form_ulaz = UlazRobeForm()
	form_izlaz = IzlazRobeForm()
	if form_ulaz.submit1.data and form_ulaz.validate():
			tvrtka = Tvrtka.query.filter_by(oib=form_ulaz.oib.data).first_or_404()
			proizvod.kolicina += form_ulaz.promijenjena_kolicina.data
			evidencija = Evidencija(proizvod_id=proizvod.id, tvrtka_id=tvrtka.id, promijenjena_kolicina=form_ulaz.promijenjena_kolicina.data, user_id=current_user.id, vrsta_unosa='unos', trenutna_kolicina=proizvod.kolicina)
			db.session.add(evidencija)
			db.session.commit()
			flash('Dodali ste kolicinu na stanje!')
			return redirect(url_for('proizvod', name=proizvod.name))
	if form_izlaz.submit2.data and form_izlaz.validate():
			tvrtka = Tvrtka.query.filter_by(oib=form_izlaz.oib.data).first_or_404()
			proizvod.kolicina -= form_izlaz.promijenjena_kolicina.data
			evidencija = Evidencija(proizvod_id=proizvod.id, tvrtka_id=tvrtka.id, promijenjena_kolicina=form_izlaz.promijenjena_kolicina.data, user_id=current_user.id, vrsta_unosa='izlaz', trenutna_kolicina=proizvod.kolicina)
			db.session.add(evidencija)
			db.session.commit()
			flash('Oduzeli ste kolicinu sa stanja!')
			return redirect(url_for('proizvod', name=proizvod.name))
	return render_template('proizvod.html', title=proizvod.name, proizvod=proizvod, evidencijaUlaz=evidencijaUlaz, evidencijaIzlaz=evidencijaIzlaz, form_ulaz=form_ulaz, form_izlaz=form_izlaz)

@app.route('/stanje_skladista/<int:page_num>', methods=['GET', 'POST'])
@login_required
def stanje_skladista(page_num):
	proizvodi = Proizvod.query.order_by(Proizvod.datum_unosa.desc()).paginate(per_page=6, page=page_num, error_out=True)
	form = SearchForm()
	if form.validate_on_submit():
		proizvodi2 = Proizvod.query.filter(Proizvod.name.like("%" + form.search.data + "%")).paginate(per_page=3, page=page_num, error_out=True)
		if not proizvodi2:
			flash('Proizvod ne postoji')
		return render_template("stanje_skladista.html", title='Stanje skladista', form=form, proizvodi=proizvodi2)
	return render_template('stanje_skladista.html', title='Stanje skladista', proizvodi=proizvodi, form=form)

@app.route('/stanje_skladista1', methods=['GET', 'POST'])
@login_required
def stanje_skladista1():
	return redirect(url_for('stanje_skladista', page_num=1))


@app.route('/tvrtke', methods=['GET', 'POST'])
@login_required
def tvrtke():
	form = UnosTvrtkeForm()
	tvrtke = Tvrtka.query.all()
	#dob = Dobavljac.query.all()
	if form.validate_on_submit():
		tvrtka = Tvrtka(name=form.name.data, oib=form.oib.data, grad=form.grad.data, 
			p_broj=form.p_broj.data, drzava=form.drzava.data)
		db.session.add(tvrtka)
		db.session.commit()
		flash(f'Uspješno ste unijeli tvrtku {form.name.data}!')
		tvrtke = Tvrtka.query.all()
		return render_template('tvrtke.html', title='Dodaj tvrtku', form=form, tvrtke=tvrtke)
	return render_template('tvrtke.html', title='Dodaj tvrtku', form=form, tvrtke=tvrtke)

@app.route('/evidencija_unosa')
@login_required
def evidencija_unosa():
	evidencija = Evidencija.query.filter_by(vrsta_unosa='unos').order_by(Evidencija.datum_unosa.desc()).all()
	html = render_template('evidencija_unosa.html', title='Evidencija unosa', evidencija=evidencija)
	
	return render_template('evidencija_unosa.html', title='Evidencija unosa', evidencija=evidencija)

@app.route('/evidencija_izdavanja')
@login_required
def evidencija_izdavanja():
	evidencija = Evidencija.query.filter_by(vrsta_unosa='izlaz').order_by(Evidencija.datum_unosa.desc()).all()
	return render_template('evidencija_izdavanja.html', title='Evidencija izdavanja', evidencija=evidencija)

@app.route('/search', methods=['GET', 'POST'])
@login_required
def search():
	proizvodi = Proizvod.query.all()
	form = SearchForm()
	if form.validate_on_submit():
		search = form.search.data
		proizvodi = Proizvod.query.filter(Proizvod.name.like("%" + search + "%")).all()
		if not proizvodi:
			flash('Nema proizvoda pod tim imenom')
		return render_template("search.html", form=form, proizvodi=proizvodi)
	return render_template("search.html", form=form, proizvodi=proizvodi)

@app.route('/evidencija/<id>')
@login_required
def evidencija(id):
	evidencija = Evidencija.query.filter_by(id=id).first_or_404()
	#render_template_to_pdf('evidencija.html', id=id, download=True, save=False, param='hello')
	return render_template('evidencija.html', id=id, evidencija=evidencija)

@app.route('/evidencija_pdf/<id>')
@login_required
def evidencija_pdf(id):
	evidencija = Evidencija.query.filter_by(id=id).first_or_404()
	#render_template_to_pdf('evidencija.html', id=id, download=True, save=False, param='hello')
	html = render_template('evidencija_pdf.html', id=id, evidencija=evidencija)
	pdfkit.from_string(html, 'evidencija '+id +'.pdf', configuration=config)
	return render_template('evidencija.html', id=id, evidencija=evidencija)


@app.route('/edit_password', methods=['GET', 'POST'])
@login_required
def edit_password():
	form = EditPasswordForm()
	if form.validate_on_submit():
		current_user.set_password(form.password.data)
		db.session.commit()
		flash('Vaše promjene su spremljene')
		return redirect(url_for('edit_password'))
	return render_template('edit_password.html', title='Edit Profile', form=form)


@app.route('/export')
@login_required
def export():
	sql= text('SELECT * FROM Evidencija')
	result= db.engine.execute(sql)
	query_sets = []
	for r in result:
		query_sets.append(r)
	column_names = [
		'id',
		'datum_unosa',
		'vrsta_unosa',
		]
	return excel.make_response_from_query_sets(query_sets, column_names, 'xls')

