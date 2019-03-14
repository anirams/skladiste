from flask import render_template, flash, redirect, url_for, request, send_file, send_from_directory, make_response
from app import app, db
from app.forms import LoginForm, RegistrationForm, UlazRobeForm, IzlazRobeForm, UrediProizvodForm, UnosProizvodaForm, SearchForm, EditPasswordForm, UnosTvrtkeForm, SearchFormTvrtka, SearchFormKorisnik, ListForm, UrediTvrtkuForm, Storno, SearchFormEvidencija, SearchReceiptNumber, Deactivate, SetRank, SearchFormReceipt, SearchFormReceiptStorno
from flask_login import current_user, login_user, logout_user, login_required
from app.models import User, Proizvod, Tvrtka, Evidencija, Receipt
from werkzeug.urls import url_parse
from datetime import datetime, timedelta
import flask_excel as excel
from sqlalchemy import text
import pdfkit
from flask_paginate import Pagination, get_page_parameter, get_page_args
from sqlalchemy import text
import os, json
#from flask_weasyprint import HTML, render_pdf

config = pdfkit.configuration(wkhtmltopdf="C:/Program Files/wkhtmltopdf/bin/wkhtmltopdf.exe")

excel.init_excel(app)

@app.route('/index')
@login_required
def index():
	return render_template('index.html', title='Home')

@app.route('/', methods=['GET', 'POST'])
@app.route('/login', methods=['GET', 'POST'])
def login():
	if current_user.is_authenticated:
		return redirect(url_for('index'))
	form = LoginForm()
	if form.validate_on_submit():
		user = User.query.filter_by(username=form.username.data).first()
		if user is None or not user.check_password(form.password.data):
			flash(f'Netočno korisničko ime ili lozinka!', 'danger')
			return redirect(url_for('login'))
		if user.status =="deactivated":
			flash(f'Korisnik je deaktiviran', 'danger')
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

@app.route('/registracija2', methods=['GET', 'POST'])
@login_required
def register():
	if not current_user.is_authenticated:
		return redirect(url_for('login'))
	if current_user.rank != "admin":
		return redirect(url_for('index'))
	form = RegistrationForm()
	if form.validate_on_submit():
		user = User(username=form.username.data, email=form.email.data, rank="korisnik", status="active")
		user.set_password(form.password.data)
		db.session.add(user)
		db.session.commit()
		flash(f'Registrirali ste korisnika {form.username.data}!', 'success')
		return redirect(url_for('login'))
	return render_template('registracija2.html', title='Registriraj se', form=form)

@app.route('/user/<username>', methods=['GET', 'POST'])
@login_required
def user(username):
	form = Deactivate()
	form2= SetRank()
	user = User.query.filter_by(username=username).first_or_404()
	if form.submit.data:
		if form.validate_on_submit():
			if form.activate.data=="deactivate" and user.status=="active":
				user.status="deactivated"
			elif form.activate.data=="activate" and user.status=="deactivated":
				user.status ="active"
			db.session.add(user)
			db.session.commit()
	if form2.submit2.data:
		if form2.validate_on_submit():
			user.rank=form2.rank.data
			db.session.add(user)
			db.session.commit()
	return render_template('user.html', user=user, form=form, form2=form2)

@app.before_request
def before_request():
	if current_user.is_authenticated:
		current_user.last_seen = datetime.utcnow()
		db.session.commit()

@app.route('/unos_proizvoda', methods=['GET', 'POST'])
@login_required
def unos_proizvoda():
	form = UnosProizvodaForm()
	if form.submit.data:
		return redirect(url_for('stanje_skladista', page_num=1, s=' '))
	while form.dodaj_jos.data:
		proizvod = Proizvod.query.filter_by(name=form.name.data).first()
		proizvod.kolicina += form.promijenjena_kolicina.data
		tvrtka = Tvrtka.query.filter_by(oib=form.oib.data).first()
		evidencija = Evidencija(proizvod_id=proizvod.id, promijenjena_kolicina=form.promijenjena_kolicina.data, tvrtka_id=tvrtka.id, user_id=current_user.id, vrsta_unosa='unos', trenutna_kolicina=proizvod.kolicina)
		db.session.add(evidencija)
		db.session.commit()
		flash(f'Dodali ste proizvod {form.name.data}!', 'success')
		return redirect(url_for('unos_proizvoda'))
	return render_template('unos_proizvoda.html', title='Dodaj proizvod', form=form)

@app.route('/proizvod/<name>', methods=['GET', 'POST'])
@login_required
def proizvod(name):
	proizvod = Proizvod.query.filter_by(name=name).first_or_404()
	lista = []
	sveTvrtke=Tvrtka.query.all()
	for tvrtka in sveTvrtke:
		lista.append(tvrtka.name)
	#yesterday=datetime.today() - timedelta(days = 1)
	todays_datetime = datetime(datetime.today().year, datetime.today().month, datetime.today().day)
	evidencijaUlaz = Evidencija.query.filter(Evidencija.proizvod_id==proizvod.id, Evidencija.vrsta_unosa=='unos', Evidencija.datum_unosa >= todays_datetime).order_by(Evidencija.datum_unosa.desc()).all()
	evidencijaIzlaz = Evidencija.query.filter(Evidencija.proizvod_id==proizvod.id, Evidencija.vrsta_unosa=='izlaz', Evidencija.datum_unosa >= todays_datetime).order_by(Evidencija.datum_unosa.desc()).all()
	form_ulaz = UlazRobeForm()
	form_izlaz = IzlazRobeForm()
	form_uredi = UrediProizvodForm()
	#form_uredi.opis_proizvoda.data=proizvod.opis_proizvoda
	if form_ulaz.submit1.data and form_ulaz.validate():
			#tvrtka = Tvrtka.query.filter_by(oib=form_ulaz.oib.data).first_or_404()
			tvrtka = Tvrtka.query.filter_by(name=form_ulaz.name.data).first()
			proizvod.kolicina += form_ulaz.promijenjena_kolicina.data
			evidencija = Evidencija(proizvod_id=proizvod.id, tvrtka_id=tvrtka.id, promijenjena_kolicina=form_ulaz.promijenjena_kolicina.data, user_id=current_user.id, vrsta_unosa='unos', trenutna_kolicina=proizvod.kolicina)
			db.session.add(evidencija)
			db.session.commit()
			flash('Dodali ste kolicinu na stanje!')
			return redirect(url_for('proizvod', name=proizvod.name))
	if form_izlaz.submit2.data and form_izlaz.validate():
			#tvrtka = Tvrtka.query.filter_by(oib=form_izlaz.oib.data).first_or_404()
			tvrtka = Tvrtka.query.filter_by(name=form_ulaz.name.data).first()
			proizvod.kolicina -= form_ulaz.promijenjena_kolicina.data
			evidencija = Evidencija(proizvod_id=proizvod.id, tvrtka_id=tvrtka.id, promijenjena_kolicina=form_ulaz.promijenjena_kolicina.data, user_id=current_user.id, vrsta_unosa='izlaz', trenutna_kolicina=proizvod.kolicina)
			db.session.add(evidencija)
			db.session.commit()
			flash('Dodali ste kolicinu na stanje!')
			return redirect(url_for('proizvod', name=proizvod.name))
	if form_uredi.submit3.data and form_uredi.validate():
			proizvod = Proizvod.query.filter_by(name=name).first_or_404()
			proizvod.name = form_uredi.name.data
			proizvod.zemlja_podrijetla = form_uredi.zemlja_podrijetla.data
			proizvod.opis_proizvoda = form_uredi.opis_proizvoda.data
			barkod = str(form_uredi.barkod.data)
			if barkod[0] == '0':
				proizvod.bar_kod = 'leadingZero'+form_uredi.barkod.data
			else:
				proizvod.bar_kod = form_uredi.barkod.data
			db.session.add(proizvod)
			db.session.commit()
			flash('Uspjesno ste uredili proizvod!')
			return redirect(url_for('proizvod', name=proizvod.name))
	return render_template('proizvod.html', title=proizvod.name, proizvod=proizvod, evidencijaUlaz=evidencijaUlaz, evidencijaIzlaz=evidencijaIzlaz, form_ulaz=form_ulaz, form_izlaz=form_izlaz, form_uredi=form_uredi, name=proizvod.name, lista=lista)

@app.route('/stanje_skladista/<int:page_num>+<s>', methods=['GET', 'POST'])
@login_required
def stanje_skladista(page_num, s):
	form = SearchForm()
	form2 = UnosProizvodaForm()
	lista = []
	lista2 = []
	sviProizvodi = Proizvod.query.all()
	for proizvod in sviProizvodi:
		lista.append(proizvod.name)
	
	if s == ' ':
		proizvodi = Proizvod.query.order_by(Proizvod.datum_unosa.desc()).paginate(per_page=3, page=page_num, error_out=True)
	elif not form.submit.data:
		proizvodi2 = Proizvod.query.filter(Proizvod.name.like("%" + s + "%")).paginate(per_page=3, page=page_num, error_out=True)
		return render_template("stanje_skladista.html", title='Stanje skladista', form=form, proizvodi=proizvodi2, search=s, form2=form2, lista=lista )
	if form.submit.data:
		if form.validate_on_submit():
			search = form.search.data
			if search.isdigit():
				if search[0] == '0':
					search='leadingZero'+search
				proizvodi2= Proizvod.query.filter_by(bar_kod=search).paginate(per_page=3, page=1, error_out=True)
			else:
				proizvodi2 = Proizvod.query.filter(Proizvod.name.like("%" + form.search.data + "%")).paginate(per_page=3, page=1, error_out=True)
			return render_template("stanje_skladista.html", title='Stanje skladista', form=form, proizvodi=proizvodi2, search=form.search.data, form2=form2, lista=lista )

	if form2.submit2.data:
		if form2.validate_on_submit():
			proizvod = Proizvod(name=form2.name.data, opis_proizvoda=form2.opis_proizvoda.data, zemlja_podrijetla=form2.zemlja_podrijetla.data)
			barkod = str(form2.barkod.data)
			#import pdb; pdb.set_trace();
			if barkod[0] == '0':
				proizvod.bar_kod='leadingZero'+form2.barkod.data
			else:
				proizvod.bar_kod = form2.barkod.data

			db.session.add(proizvod)
			db.session.commit()
			flash(f'Dodali ste proizvod {form2.name.data}!', 'success')
			return redirect(url_for('stanje_skladista1'))
	return render_template('stanje_skladista.html', title='Stanje skladista', proizvodi=proizvodi, form=form, form2=form2, search=' ', lista=lista)

@app.route('/stanje_skladista1', methods=['GET', 'POST'])
@login_required
def stanje_skladista1():
	return redirect(url_for('stanje_skladista', page_num=1, s=' '))


@app.route('/tvrtke/<int:page_num>+<s>', methods=['GET', 'POST'])
@login_required
def tvrtke(page_num, s):
	form = UnosTvrtkeForm()
	form2 = SearchFormTvrtka()
	tvrtke = Tvrtka.query.all()
	lista = []
	sve_tvrtke = Tvrtka.query.all() 
	for tvrtka in sve_tvrtke:
		lista.append(tvrtka.name)

	if s == ' ':
		tvrtke = Tvrtka.query.order_by(Tvrtka.name).paginate(per_page=5, page=page_num, error_out=True)
		
	elif not form2.submit2.data:
		tvrtke2 = Tvrtka.query.filter(Tvrtka.name.like("%" + s + "%")).paginate(per_page=3, page=page_num, error_out=True)
		return render_template("tvrtke.html", title='Tvrtke', form=form, form2=form2, tvrtke=tvrtke2, search=s , lista=lista)
	if  form2.submit2.data:
		if form2.validate_on_submit():
			tvrtke2 = Tvrtka.query.filter(Tvrtka.name.like("%" + form2.search.data + "%")).paginate(per_page=3, page=1, error_out=True)
			tvrtke_lista=Tvrtka.query.filter(Tvrtka.name.like("%" + form2.search.data + "%"))
			return render_template("tvrtke.html", title='Tvrtke', form=form, form2=form2, tvrtke=tvrtke2, search=form2.search.data, tvrtke_lista=tvrtke_lista, lista=lista)
	
	if form.submit.data:
		if form.validate_on_submit():
			tvrtka = Tvrtka(name=form.name.data, oib=form.oib.data, adresa=form.adresa.data, grad=form.grad.data, 
				p_broj=form.p_broj.data, drzava=form.drzava.data)
			db.session.add(tvrtka)
			db.session.commit()
			flash(f'Uspješno ste unijeli tvrtku {form.name.data}!')
			tvrtke = Tvrtka.query.order_by(Tvrtka.name.desc()).paginate(per_page=5, page=page_num, error_out=True)
			#return render_template('tvrtke.html', title='Dodaj tvrtku', form=form, form2=form2, tvrtke=tvrtke, search=' ')
		else:
			form_error=True
			return render_template('tvrtke.html', title='Tvrtke', tvrtke=tvrtke, form=form, form2= form2, search=' ', lista=lista, form_error=form_error)
	return render_template('tvrtke.html', title='Tvrtke', tvrtke=tvrtke, form=form, form2= form2, search=' ', lista=lista)

@app.route('/tvrtka/<name>', methods=['GET', 'POST'])
@login_required
def tvrtka(name):
	form_uredi = UrediTvrtkuForm()
	tvrtka = Tvrtka.query.filter_by(name=name).first_or_404()
	if form_uredi.submit3.data:
		if form_uredi.validate_on_submit():
			tvrtka = Tvrtka.query.filter_by(name=name).first_or_404()
			tvrtka.name = form_uredi.name.data
			tvrtka.oib = form_uredi.oib.data
			tvrtka.adresa = form_uredi.adresa.data
			tvrtka.grad = form_uredi.grad.data
			tvrtka.p_broj = form_uredi.p_broj.data
			tvrtka.drzava = form_uredi.drzava.data
			db.session.add(tvrtka)
			db.session.commit()
			flash(f'Uspješno ste izmijenili podatke tvrtke {form_uredi.name.data}!')
			return redirect(url_for('tvrtka', name=tvrtka.name))		
	return render_template('tvrtka.html', user=user, tvrtka=tvrtka, form_uredi=form_uredi)

@app.route('/tvrtke1', methods=['GET', 'POST'])
@login_required
def tvrtke1():
	return redirect(url_for('tvrtke', page_num=1, s=' '))

@app.route('/svi_korisnici/<int:page_num>+<s>', methods=['GET', 'POST'])
@login_required
def svi_korisnici(page_num, s):
	form = SearchFormKorisnik()
	lista = []
	sviKorisnici = User.query.all()
	for korisnik in sviKorisnici:
		lista.append(korisnik.username)
	if s == ' ':
		svi_korisnici = User.query.order_by(User.username.desc()).paginate(per_page=7, page=page_num, error_out=True)
		
	elif not form.submit.data:
		svi_korisnici2 = User.query.filter(User.username.like("%" + s + "%")).paginate(per_page=3, page=page_num, error_out=True)
		return render_template("svi_korisnici.html", title='Svi korisnici', form=form, svi_korisnici=svi_korisnici2, search=s )
	if form.validate_on_submit():
		svi_korisnici2 = User.query.filter(User.username.like("%" + form.search.data + "%")).paginate(per_page=3, page=1, error_out=True)
		if not svi_korisnici2:
			flash('Korisnik ne postoji')
		return render_template("svi_korisnici.html", title='Svi korisnici', form=form, svi_korisnici=svi_korisnici2, search=form.search.data, lista=lista )
	return render_template('svi_korisnici.html', title='Svi korisnici', svi_korisnici=svi_korisnici, form=form, search=' ', lista=lista)

@app.route('/svi_korisnici1', methods=['GET', 'POST'])
@login_required
def svi_korisnici1():
	return redirect(url_for('svi_korisnici', page_num=1, s=' '))

@app.route('/evidencija_unosa/<int:page_num>+<s>+<b>+<e>+<u>', methods=['GET', 'POST'])
@login_required
def evidencija_unosa(page_num, s, b, e, u):
	form = SearchFormEvidencija()
	lista = []
	lista2= []
	evidencija = Evidencija.query.filter_by(vrsta_unosa='unos').order_by(Evidencija.datum_unosa.desc()).paginate(per_page=3, page=page_num, error_out=True)
	sviProizvodi = Proizvod.query.all()
	for proizvod in sviProizvodi:
		lista.append(proizvod.name)
	sviUseri = User.query.all()
	for user in sviUseri:
		lista2.append(user.username)
	if s == ' ':
		if u==' ':
			if b ==' ' and e==' ':
				evidencija = Evidencija.query.filter_by(vrsta_unosa='unos').order_by(Evidencija.datum_unosa.desc()).paginate(per_page=3, page=page_num, error_out=True)
			elif b ==' ':
				evidencija = Evidencija.query.filter( Evidencija.vrsta_unosa=="unos", Evidencija.datum_unosa <= e).order_by(Evidencija.datum_unosa.desc()).paginate(per_page=3, page=page_num, error_out=True)
			elif e==' ':
				evidencija = Evidencija.query.filter( Evidencija.vrsta_unosa=="unos", Evidencija.datum_unosa >= b).order_by(Evidencija.datum_unosa.desc()).paginate(per_page=3, page=page_num, error_out=True)
			else:
				evidencija = Evidencija.query.filter( Evidencija.vrsta_unosa=="unos", Evidencija.datum_unosa >= b, Evidencija.datum_unosa <=e).order_by(Evidencija.datum_unosa.desc()).paginate(per_page=3, page=page_num, error_out=True)
		else:
			user = User.query.filter_by(username=u).first()
			if b ==' ' and e==' ':
				evidencija = Evidencija.query.filter( Evidencija.vrsta_unosa=="unos", Evidencija.user_id==user.id).order_by(Evidencija.datum_unosa.desc()).paginate(per_page=3, page=page_num, error_out=True)
			elif b ==' ':
				evidencija = Evidencija.query.filter( Evidencija.vrsta_unosa=="unos", Evidencija.datum_unosa <= e, Evidencija.user_id==user.id).order_by(Evidencija.datum_unosa.desc()).paginate(per_page=3, page=page_num, error_out=True)
			elif e==' ':
				evidencija = Evidencija.query.filter( Evidencija.vrsta_unosa=="unos", Evidencija.datum_unosa >= b, Evidencija.user_id==user.id).order_by(Evidencija.datum_unosa.desc()).paginate(per_page=3, page=page_num, error_out=True)
			else:
				evidencija = Evidencija.query.filter( Evidencija.vrsta_unosa=="unos", Evidencija.datum_unosa >= b, Evidencija.datum_unosa <=e, Evidencija.user_id==user.id).order_by(Evidencija.datum_unosa.desc()).paginate(per_page=3, page=page_num, error_out=True)

	elif not form.submit.data:
		proizvod = Proizvod.query.filter(Proizvod.name.like("%" + s + "%")).first()
		if u == ' ':
			if b ==' ' and e==' ':
				evidencija = Evidencija.query.filter( Evidencija.proizvod_id==proizvod.id, Evidencija.vrsta_unosa=="unos").order_by(Evidencija.datum_unosa.desc()).paginate(per_page=3, page=page_num, error_out=True)
			elif b ==' ':
				evidencija = Evidencija.query.filter(Evidencija.proizvod_id==proizvod.id, Evidencija.vrsta_unosa=="unos", Evidencija.datum_unosa <= e).order_by(Evidencija.datum_unosa.desc()).paginate(per_page=3, page=page_num, error_out=True)
			elif e ==' ':
				evidencija = Evidencija.query.filter(Evidencija.proizvod_id==proizvod.id, Evidencija.vrsta_unosa=="unos", Evidencija.datum_unosa >= b).order_by(Evidencija.datum_unosa.desc()).paginate(per_page=3, page=page_num, error_out=True)
			else:
				evidencija = Evidencija.query.filter(Evidencija.proizvod_id==proizvod.id, Evidencija.vrsta_unosa=="unos", Evidencija.datum_unosa >= b, Evidencija.datum_unosa <= e).order_by(Evidencija.datum_unosa.desc()).paginate(per_page=3, page=page_num, error_out=True)
			return render_template('evidencija_unosa.html', title='Evidencija unosa', form=form, evidencija=evidencija, search=s, begin=b, end=e, user=u, lista=lista, lista2=lista2)
		else:
			user = User.query.filter_by(username=u).first()
			if b ==' ' and e==' ':
				evidencija = Evidencija.query.filter( Evidencija.proizvod_id==proizvod.id, Evidencija.vrsta_unosa=="unos", Evidencija.user_id==user.id).order_by(Evidencija.datum_unosa.desc()).paginate(per_page=3, page=page_num, error_out=True)
			elif b ==' ':
				evidencija = Evidencija.query.filter(Evidencija.proizvod_id==proizvod.id, Evidencija.vrsta_unosa=="unos", Evidencija.datum_unosa <= e, Evidencija.user_id==user.id).order_by(Evidencija.datum_unosa.desc()).paginate(per_page=3, page=page_num, error_out=True)
			elif e ==' ':
				evidencija = Evidencija.query.filter(Evidencija.proizvod_id==proizvod.id, Evidencija.vrsta_unosa=="unos", Evidencija.datum_unosa >= b, Evidencija.user_id==user.id).order_by(Evidencija.datum_unosa.desc()).paginate(per_page=3, page=page_num, error_out=True)
			else:
				evidencija = Evidencija.query.filter(Evidencija.proizvod_id==proizvod.id, Evidencija.vrsta_unosa=="unos", Evidencija.datum_unosa >= b, Evidencija.datum_unosa <= e, Evidencija.user_id==user.id).order_by(Evidencija.datum_unosa.desc()).paginate(per_page=3, page=page_num, error_out=True)
			return render_template('evidencija_unosa.html', title='Evidencija unosa', form=form, evidencija=evidencija, search=s, begin=b, end=e, user=u, lista=lista, lista2=lista2)
	if form.submit.data:
		if form.validate_on_submit():

			proizvod = Proizvod.query.filter(Proizvod.name.like("%" + form.search.data + "%")).first()
			#import pdb; pdb.set_trace();
			if form.search.data != "" and form.search.data != " " and proizvod is None:
				flash(f'Proizvod '+form.search.data+ ' ne postoji!', 'danger')
				return redirect(url_for('evidencija_unosa1'))
			user = User.query.filter_by(username=form.user.data).first()
			if form.user.data != "" and form.user.data != " " and user is None:
				flash(f'Korisnik '+form.user.data+ ' ne postoji!', 'danger')
				return redirect(url_for('evidencija_unosa1'))
			if user is None:
				form.user.data=" "
				if form.begin.data is None and form.end.data is None:
					if form.search.data == "" or form.search.data == " ":
						evidencija = Evidencija.query.filter(Evidencija.vrsta_unosa=="unos").order_by(Evidencija.datum_unosa.desc()).paginate(per_page=3, page=1, error_out=True)
						form.search.data= " "
					else:
						evidencija = Evidencija.query.filter(Evidencija.proizvod_id==proizvod.id, Evidencija.vrsta_unosa=="unos").order_by(Evidencija.datum_unosa.desc()).paginate(per_page=3, page=1, error_out=True)
					form.begin.data = ' '
					form.end.data = ' '
					form.user.data=' '
				elif form.begin.data is None:
					if form.search.data == "" or form.search.data == " ":
						evidencija = Evidencija.query.filter(Evidencija.vrsta_unosa=="unos", Evidencija.datum_unosa <= form.end.data).order_by(Evidencija.datum_unosa.desc()).paginate(per_page=3, page=1, error_out=True)
						form.search.data= " "
					else:
						evidencija = Evidencija.query.filter(Evidencija.proizvod_id==proizvod.id, Evidencija.vrsta_unosa=="unos", Evidencija.datum_unosa <= form.end.data).order_by(Evidencija.datum_unosa.desc()).paginate(per_page=3, page=1, error_out=True)
					form.begin.data = ' '
					form.user.data=' '
				elif form.end.data is None:
					if form.search.data == "" or form.search.data == " ":
						evidencija = Evidencija.query.filter(Evidencija.vrsta_unosa=="unos", Evidencija.datum_unosa >= form.begin.data).order_by(Evidencija.datum_unosa.desc()).paginate(per_page=3, page=1, error_out=True)
						form.search.data= " "
					else:
						evidencija = Evidencija.query.filter(Evidencija.proizvod_id==proizvod.id, Evidencija.vrsta_unosa=="unos", Evidencija.datum_unosa >= form.begin.data).order_by(Evidencija.datum_unosa.desc()).paginate(per_page=3, page=1, error_out=True)
					form.end.data = ' '
					form.user.data=' '
				else:

					form.user.data=' '
					if form.search.data == "" or form.search.data == " ":
						evidencija = Evidencija.query.filter(Evidencija.vrsta_unosa=="unos", Evidencija.datum_unosa >= form.begin.data, Evidencija.datum_unosa <= form.end.data).order_by(Evidencija.datum_unosa.desc()).paginate(per_page=3, page=1, error_out=True)
						form.search.data= " "
					else:
						evidencija = Evidencija.query.filter(Evidencija.proizvod_id==proizvod.id, Evidencija.vrsta_unosa=="unos", Evidencija.datum_unosa >= form.begin.data, Evidencija.datum_unosa <= form.end.data).order_by(Evidencija.datum_unosa.desc()).paginate(per_page=3, page=1, error_out=True)
			else:
				
				if form.begin.data is None and form.end.data is None:
					#import pdb; pdb.set_trace();
					if form.search.data == "" or form.search.data == " ":
						evidencija = Evidencija.query.filter(Evidencija.vrsta_unosa=="unos", Evidencija.user_id==user.id).order_by(Evidencija.datum_unosa.desc()).paginate(per_page=3, page=1, error_out=True)
						form.search.data= " "
					else:
						evidencija = Evidencija.query.filter(Evidencija.proizvod_id==proizvod.id, Evidencija.vrsta_unosa=="unos", Evidencija.user_id==user.id).order_by(Evidencija.datum_unosa.desc()).paginate(per_page=3, page=1, error_out=True)
					form.begin.data = ' '
					form.end.data = ' '
				elif form.begin.data is None:
					if form.search.data == "" or form.search.data == " ":
						evidencija = Evidencija.query.filter(Evidencija.vrsta_unosa=="unos", Evidencija.datum_unosa <= form.end.data, Evidencija.user_id==user.id).order_by(Evidencija.datum_unosa.desc()).paginate(per_page=3, page=1, error_out=True)
						form.search.data= " "
					else:
						evidencija = Evidencija.query.filter(Evidencija.proizvod_id==proizvod.id, Evidencija.vrsta_unosa=="unos", Evidencija.datum_unosa <= form.end.data, Evidencija.user_id==user.id).order_by(Evidencija.datum_unosa.desc()).paginate(per_page=3, page=1, error_out=True)
					form.begin.data = ' '
				elif form.end.data is None:
					if form.search.data == "" or form.search.data == " ":
						evidencija = Evidencija.query.filter(Evidencija.vrsta_unosa=="unos", Evidencija.datum_unosa >= form.begin.data, Evidencija.user_id==user.id).order_by(Evidencija.datum_unosa.desc()).paginate(per_page=3, page=1, error_out=True)
						form.search.data= " "
					else:
						evidencija = Evidencija.query.filter(Evidencija.proizvod_id==proizvod.id, Evidencija.vrsta_unosa=="unos", Evidencija.datum_unosa >= form.begin.data, Evidencija.user_id==user.id).order_by(Evidencija.datum_unosa.desc()).paginate(per_page=3, page=1, error_out=True)
					form.end.data = ' '
				else:
					if form.search.data == "" or form.search.data == " ":
						evidencija = Evidencija.query.filter(Evidencija.vrsta_unosa=="unos", Evidencija.datum_unosa >= form.begin.data, Evidencija.datum_unosa <= form.end.data, Evidencija.user_id==user.id).order_by(Evidencija.datum_unosa.desc()).paginate(per_page=3, page=1, error_out=True)
						form.search.data= " "
					else:
						evidencija = Evidencija.query.filter(Evidencija.proizvod_id==proizvod.id, Evidencija.vrsta_unosa=="unos", Evidencija.datum_unosa >= form.begin.data, Evidencija.datum_unosa <= form.end.data, Evidencija.user_id==user.id).order_by(Evidencija.datum_unosa.desc()).paginate(per_page=3, page=1, error_out=True)
			return render_template('evidencija_unosa.html', title='Evidencija unosa', form=form, evidencija=evidencija, search=form.search.data, begin=form.begin.data, end=form.end.data, lista=lista, lista2=lista2, user=form.user.data, page=1)
		return redirect(url_for('evidencija_unosa1'))
	return render_template('evidencija_unosa.html', title='Evidencija unosa', form=form, evidencija=evidencija, search=s, begin=b, end=e, user=u, lista=lista, lista2=lista2)

@app.route('/evidencija_unosa1', methods=['GET', 'POST'])
@login_required
def evidencija_unosa1():
	return redirect(url_for('evidencija_unosa', page_num=1, s=' ', b=' ', e=' ', u=' '))

@app.route('/evidencija_izdavanja/<int:page_num>+<s>+<b>+<e>+<u>', methods=['GET', 'POST'])
@login_required
def evidencija_izdavanja(page_num, s, b, e, u):
	form = SearchFormEvidencija()
	lista = []
	lista2 = []
	evidencija = Evidencija.query.filter_by(vrsta_unosa='izlaz').order_by(Evidencija.datum_unosa.desc()).paginate(per_page=3, page=page_num, error_out=True)
	sviProizvodi = Proizvod.query.all()
	for proizvod in sviProizvodi:
		lista.append(proizvod.name)
	sviUseri = User.query.all()
	for user in sviUseri:
		lista2.append(user.username)
	if s == ' ':
		if u==' ':
			if b ==' ' and e==' ':
				evidencija = Evidencija.query.filter_by(vrsta_unosa='izlaz').order_by(Evidencija.datum_unosa.desc()).paginate(per_page=3, page=page_num, error_out=True)
			elif b ==' ':
				evidencija = Evidencija.query.filter( Evidencija.vrsta_unosa=='izlaz', Evidencija.datum_unosa <= e).order_by(Evidencija.datum_unosa.desc()).paginate(per_page=3, page=page_num, error_out=True)
			elif e==' ':
				evidencija = Evidencija.query.filter( Evidencija.vrsta_unosa=='izlaz', Evidencija.datum_unosa >= b).order_by(Evidencija.datum_unosa.desc()).paginate(per_page=3, page=page_num, error_out=True)
			else:
				evidencija = Evidencija.query.filter( Evidencija.vrsta_unosa=='izlaz', Evidencija.datum_unosa >= b, Evidencija.datum_unosa <=e).order_by(Evidencija.datum_unosa.desc()).paginate(per_page=3, page=page_num, error_out=True)
		else:
			user = User.query.filter_by(username=u).first()
			if b ==' ' and e==' ':
				evidencija = Evidencija.query.filter( Evidencija.vrsta_unosa=='izlaz', Evidencija.user_id==user.id).order_by(Evidencija.datum_unosa.desc()).paginate(per_page=3, page=page_num, error_out=True)
			elif b ==' ':
				evidencija = Evidencija.query.filter( Evidencija.vrsta_unosa=='izlaz', Evidencija.datum_unosa <= e, Evidencija.user_id==user.id).order_by(Evidencija.datum_unosa.desc()).paginate(per_page=3, page=page_num, error_out=True)
			elif e==' ':
				evidencija = Evidencija.query.filter( Evidencija.vrsta_unosa=='izlaz', Evidencija.datum_unosa >= b, Evidencija.user_id==user.id).order_by(Evidencija.datum_unosa.desc()).paginate(per_page=3, page=page_num, error_out=True)
			else:
				evidencija = Evidencija.query.filter( Evidencija.vrsta_unosa=='izlaz', Evidencija.datum_unosa >= b, Evidencija.datum_unosa <=e, Evidencija.user_id==user.id).order_by(Evidencija.datum_unosa.desc()).paginate(per_page=3, page=page_num, error_out=True)

	elif not form.submit.data:
		proizvod = Proizvod.query.filter(Proizvod.name.like("%" + s + "%")).first()
		if u == ' ':
			if b ==' ' and e==' ':
				evidencija = Evidencija.query.filter( Evidencija.proizvod_id==proizvod.id, Evidencija.vrsta_unosa=='izlaz').order_by(Evidencija.datum_unosa.desc()).paginate(per_page=3, page=page_num, error_out=True)
			elif b ==' ':
				evidencija = Evidencija.query.filter(Evidencija.proizvod_id==proizvod.id, Evidencija.vrsta_unosa=='izlaz', Evidencija.datum_unosa <= e).order_by(Evidencija.datum_unosa.desc()).paginate(per_page=3, page=page_num, error_out=True)
			elif e ==' ':
				evidencija = Evidencija.query.filter(Evidencija.proizvod_id==proizvod.id, Evidencija.vrsta_unosa=='izlaz', Evidencija.datum_unosa >= b).order_by(Evidencija.datum_unosa.desc()).paginate(per_page=3, page=page_num, error_out=True)
			else:
				evidencija = Evidencija.query.filter(Evidencija.proizvod_id==proizvod.id, Evidencija.vrsta_unosa=='izlaz', Evidencija.datum_unosa >= b, Evidencija.datum_unosa <= e).order_by(Evidencija.datum_unosa.desc()).paginate(per_page=3, page=page_num, error_out=True)
			return render_template('evidencija_izdavanja.html', title='Evidencija izdavanja', form=form, evidencija=evidencija, search=s, begin=b, end=e, user=u, lista=lista, lista2=lista2)
		else:
			user = User.query.filter_by(username=u).first()
			if b ==' ' and e==' ':
				evidencija = Evidencija.query.filter( Evidencija.proizvod_id==proizvod.id, Evidencija.vrsta_unosa=='izlaz', Evidencija.user_id==user.id).order_by(Evidencija.datum_unosa.desc()).paginate(per_page=3, page=page_num, error_out=True)
			elif b ==' ':
				evidencija = Evidencija.query.filter(Evidencija.proizvod_id==proizvod.id, Evidencija.vrsta_unosa=='izlaz', Evidencija.datum_unosa <= e, Evidencija.user_id==user.id).order_by(Evidencija.datum_unosa.desc()).paginate(per_page=3, page=page_num, error_out=True)
			elif e ==' ':
				evidencija = Evidencija.query.filter(Evidencija.proizvod_id==proizvod.id, Evidencija.vrsta_unosa=='izlaz', Evidencija.datum_unosa >= b, Evidencija.user_id==user.id).order_by(Evidencija.datum_unosa.desc()).paginate(per_page=3, page=page_num, error_out=True)
			else:
				evidencija = Evidencija.query.filter(Evidencija.proizvod_id==proizvod.id, Evidencija.vrsta_unosa=='izlaz', Evidencija.datum_unosa >= b, Evidencija.datum_unosa <= e, Evidencija.user_id==user.id).order_by(Evidencija.datum_unosa.desc()).paginate(per_page=3, page=page_num, error_out=True)
			return render_template('evidencija_izdavanja.html', title='Evidencija izdavanja', form=form, evidencija=evidencija, search=s, begin=b, end=e, user=u, lista=lista, lista2=lista2)
	if form.submit.data:
		#import pdb; pdb.set_trace();
		if form.validate_on_submit():

			proizvod = Proizvod.query.filter(Proizvod.name.like("%" + form.search.data + "%")).first()
			if form.search.data != "" and form.search.data != " " and proizvod is None:
				flash(f'Proizvod '+form.search.data+ ' ne postoji!', 'danger')
				return redirect(url_for('evidencija_unosa1'))
			user = User.query.filter_by(username=form.user.data).first()
			if form.user.data != "" and form.user.data != " " and user is None:
				flash(f'Korisnik '+form.user.data+ ' ne postoji!', 'danger')
				return redirect(url_for('evidencija_unosa1'))
			if user is None:
				form.user.data=" "
				if form.begin.data is None and form.end.data is None:
					if form.search.data == "" or form.search.data == " ":
						evidencija = Evidencija.query.filter(Evidencija.vrsta_unosa=='izlaz').order_by(Evidencija.datum_unosa.desc()).paginate(per_page=3, page=1, error_out=True)
						form.search.data= " "
					else:
						evidencija = Evidencija.query.filter(Evidencija.proizvod_id==proizvod.id, Evidencija.vrsta_unosa=='izlaz').order_by(Evidencija.datum_unosa.desc()).paginate(per_page=3, page=1, error_out=True)
					form.begin.data = ' '
					form.end.data = ' '
					form.user.data=' '
				elif form.begin.data is None:
					if form.search.data == "" or form.search.data == " ":
						evidencija = Evidencija.query.filter(Evidencija.vrsta_unosa=='izlaz', Evidencija.datum_unosa <= form.end.data).order_by(Evidencija.datum_unosa.desc()).paginate(per_page=3, page=1, error_out=True)
						form.search.data= " "
					else:
						evidencija = Evidencija.query.filter(Evidencija.proizvod_id==proizvod.id, Evidencija.vrsta_unosa=='izlaz', Evidencija.datum_unosa <= form.end.data).order_by(Evidencija.datum_unosa.desc()).paginate(per_page=3, page=1, error_out=True)
					form.begin.data = ' '
					form.user.data=' '
				elif form.end.data is None:
					if form.search.data == "" or form.search.data == " ":
						evidencija = Evidencija.query.filter(Evidencija.vrsta_unosa=='izlaz', Evidencija.datum_unosa >= form.begin.data).order_by(Evidencija.datum_unosa.desc()).paginate(per_page=3, page=1, error_out=True)
						form.search.data= " "
					else:
						evidencija = Evidencija.query.filter(Evidencija.proizvod_id==proizvod.id, Evidencija.vrsta_unosa=='izlaz', Evidencija.datum_unosa >= form.begin.data).order_by(Evidencija.datum_unosa.desc()).paginate(per_page=3, page=1, error_out=True)
					form.end.data = ' '
					form.user.data=' '
				else:
					form.user.data=' '
					if form.search.data == "" or form.search.data == " ":
						evidencija = Evidencija.query.filter(Evidencija.vrsta_unosa=='izlaz', Evidencija.datum_unosa >= form.begin.data, Evidencija.datum_unosa <= form.end.data).order_by(Evidencija.datum_unosa.desc()).paginate(per_page=3, page=1, error_out=True)
						form.search.data= " "
					else:
						evidencija = Evidencija.query.filter(Evidencija.proizvod_id==proizvod.id, Evidencija.vrsta_unosa=='izlaz', Evidencija.datum_unosa >= form.begin.data, Evidencija.datum_unosa <= form.end.data).order_by(Evidencija.datum_unosa.desc()).paginate(per_page=3, page=1, error_out=True)	
			else:
				#import pdb; pdb.set_trace();
				user = User.query.filter_by(username=form.user.data).first()
				if form.begin.data is None and form.end.data is None:
					if form.search.data == "" or form.search.data == " ":
						evidencija = Evidencija.query.filter(Evidencija.vrsta_unosa=='izlaz', Evidencija.user_id==user.id).order_by(Evidencija.datum_unosa.desc()).paginate(per_page=3, page=1, error_out=True)
						form.search.data= " "
					else:
						evidencija = Evidencija.query.filter(Evidencija.proizvod_id==proizvod.id, Evidencija.vrsta_unosa=='izlaz', Evidencija.user_id==user.id).order_by(Evidencija.datum_unosa.desc()).paginate(per_page=3, page=1, error_out=True)
					form.begin.data = ' '
					form.end.data = ' '
				elif form.begin.data is None:
					if form.search.data == "" or form.search.data == " ":
						evidencija = Evidencija.query.filter(Evidencija.vrsta_unosa=='izlaz', Evidencija.datum_unosa <= form.end.data, Evidencija.user_id==user.id).order_by(Evidencija.datum_unosa.desc()).paginate(per_page=3, page=1, error_out=True)
						form.search.data= " "
					else:
						evidencija = Evidencija.query.filter(Evidencija.proizvod_id==proizvod.id, Evidencija.vrsta_unosa=='izlaz', Evidencija.datum_unosa <= form.end.data, Evidencija.user_id==user.id).order_by(Evidencija.datum_unosa.desc()).paginate(per_page=3, page=1, error_out=True)
					form.begin.data = ' '
				elif form.end.data is None:
					if form.search.data == "" or form.search.data == " ":
						evidencija = Evidencija.query.filter(Evidencija.vrsta_unosa=='izlaz', Evidencija.datum_unosa >= form.begin.data, Evidencija.user_id==user.id).order_by(Evidencija.datum_unosa.desc()).paginate(per_page=3, page=1, error_out=True)
						form.search.data= " "
					else:
						evidencija = Evidencija.query.filter(Evidencija.proizvod_id==proizvod.id, Evidencija.vrsta_unosa=='izlaz', Evidencija.datum_unosa >= form.begin.data, Evidencija.user_id==user.id).order_by(Evidencija.datum_unosa.desc()).paginate(per_page=3, page=1, error_out=True)
					form.end.data = ' '
				else:
					if form.search.data == "" or form.search.data == " ":
						evidencija = Evidencija.query.filter(Evidencija.vrsta_unosa=='izlaz', Evidencija.datum_unosa >= form.begin.data, Evidencija.datum_unosa <= form.end.data, Evidencija.user_id==user.id).order_by(Evidencija.datum_unosa.desc()).paginate(per_page=3, page=1, error_out=True)
						form.search.data= " "
					else:
						evidencija = Evidencija.query.filter(Evidencija.proizvod_id==proizvod.id, Evidencija.vrsta_unosa=='izlaz', Evidencija.datum_unosa >= form.begin.data, Evidencija.datum_unosa <= form.end.data, Evidencija.user_id==user.id).order_by(Evidencija.datum_unosa.desc()).paginate(per_page=3, page=1, error_out=True)
			return render_template('evidencija_izdavanja.html', title='Evidencija izdavanja', form=form, evidencija=evidencija, search=form.search.data, begin=form.begin.data, end=form.end.data, lista=lista, lista2=lista2, user=form.user.data, page=1)
		return redirect(url_for('evidencija_izdavanja1'))
	return render_template('evidencija_izdavanja.html', title='Evidencija izdavanja', form=form, evidencija=evidencija, search=s, begin=b, end=e, user=u, lista=lista, lista2=lista2)

@app.route('/evidencija_izdavanja1', methods=['GET', 'POST'])
@login_required
def evidencija_izdavanja1():
	return redirect(url_for('evidencija_izdavanja', page_num=1, s=' ', b=' ', e=' ', u=' '))


@app.route('/evidencija/<id>')
@login_required
def evidencija(id):
	evidencija = Evidencija.query.filter_by(id=id).first_or_404()
	return render_template('evidencija.html', id=id, evidencija=evidencija)

@app.route('/evidencija_pdf/<id>')
@login_required
def evidencija_pdf(id):
	evidencija = Evidencija.query.filter_by(id=id).first_or_404()
	receipt = Receipt.query.get(evidencija.receipt_id)
	html = render_template('evidencija_pdf.html', id=id, evidencija=evidencija, receipt=receipt)
	pdf= pdfkit.from_string(html, False, configuration=config)
	response = make_response(pdf)
	response.headers['Content-Type']='application/pdf'
	if evidencija.vrsta_unosa == "izlaz":
		response.headers['Content-Disposition']= 'inline; filename="{}"'.format('evidencija izdavanja '+id+'.pdf')
	else:
		response.headers['Content-Disposition']= 'inline; filename="{}"'.format('evidencija unosa '+id+'.pdf')
	return response
	

@app.route('/edit_password/<username>', methods=['GET', 'POST'])
@login_required
def edit_password(username):
	if current_user.rank != "admin":
		return redirect(url_for('index'))
	user=User.query.filter_by(username=username).first_or_404()
	form = EditPasswordForm()
	if form.validate_on_submit():
		user.set_password(form.password.data)
		db.session.commit()
		flash('Lozinka je promijenjena!')
	return render_template('edit_password.html', title='Edit Profile', form=form, user=user)


@app.route('/export_stanje_skladista')
@login_required
def export_stanje_skladista():
	sql= text('SELECT proizvod.name AS Proizvod, proizvod.kolicina AS Kolicina FROM proizvod')
	result= db.engine.execute(sql)
	query_sets = []
	for r in result:
		query_sets.append(r)
	column_names = [
		'Proizvod',
		'Kolicina'
		]
	return excel.make_response_from_query_sets(query_sets, column_names, 'xls')



@app.route('/export_proizvod_unos/<s>+<b>+<e>+<u>')
@login_required
def export_proizvod_unos(s, b, e, u):
	if s== " ":
		if u== " ":
			if b==" " and e==" ":
				sql= text('SELECT evidencija.datum_unosa AS "Datum Unosa", evidencija.promijenjena_kolicina AS "Promijenjena Kolicina", proizvod.name AS Proizvod, proizvod.id AS "ID Proizvoda", tvrtka.name AS Tvrtka, user.username AS Korisnik, receipt.id AS "ID Racuna", receipt.status AS "Status" FROM evidencija INNER JOIN proizvod ON evidencija.proizvod_id=proizvod.id INNER JOIN tvrtka ON evidencija.tvrtka_id=tvrtka.id INNER JOIN user ON evidencija.user_id=user.id INNER JOIN receipt ON evidencija.receipt_id=receipt.id WHERE evidencija.vrsta_unosa="unos" AND receipt.status="active"')
			elif b==" ":
				sql= text('SELECT evidencija.datum_unosa AS "Datum Unosa", evidencija.promijenjena_kolicina AS "Promijenjena Kolicina", proizvod.name AS Proizvod, proizvod.id AS "ID Proizvoda", tvrtka.name AS Tvrtka, user.username AS Korisnik, receipt.id AS "ID Racuna", receipt.status AS "Status" FROM evidencija INNER JOIN proizvod ON evidencija.proizvod_id=proizvod.id INNER JOIN tvrtka ON evidencija.tvrtka_id=tvrtka.id INNER JOIN user ON evidencija.user_id=user.id INNER JOIN receipt ON evidencija.receipt_id=receipt.id WHERE evidencija.datum_unosa <= "{}" AND evidencija.vrsta_unosa="unos" AND receipt.status="active"'.format(e))
			elif e==" ":
				sql= text('SELECT evidencija.datum_unosa AS "Datum Unosa", evidencija.promijenjena_kolicina AS "Promijenjena Kolicina", proizvod.name AS Proizvod, proizvod.id AS "ID Proizvoda", tvrtka.name AS Tvrtka, user.username AS Korisnik, receipt.id AS "ID Racuna", receipt.status AS "Status" FROM evidencija INNER JOIN proizvod ON evidencija.proizvod_id=proizvod.id INNER JOIN tvrtka ON evidencija.tvrtka_id=tvrtka.id INNER JOIN user ON evidencija.user_id=user.id INNER JOIN receipt ON evidencija.receipt_id=receipt.id WHERE evidencija.datum_unosa >= "{}" AND evidencija.vrsta_unosa="unos" AND receipt.status="active"'.format(b))
			else:
				sql= text('SELECT evidencija.datum_unosa AS "Datum Unosa", evidencija.promijenjena_kolicina AS "Promijenjena Kolicina", proizvod.name AS Proizvod, proizvod.id AS "ID Proizvoda", tvrtka.name AS Tvrtka, user.username AS Korisnik, receipt.id AS "ID Racuna", receipt.status AS "Status" FROM evidencija INNER JOIN proizvod ON evidencija.proizvod_id=proizvod.id INNER JOIN tvrtka ON evidencija.tvrtka_id=tvrtka.id INNER JOIN user ON evidencija.user_id=user.id INNER JOIN receipt ON evidencija.receipt_id=receipt.id WHERE evidencija.datum_unosa >= "{}" AND evidencija.datum_unosa <= "{}" AND evidencija.vrsta_unosa="unos" AND receipt.status="active"'.format(b, e))
		else:
			if b==" " and e==" ":
				sql= text('SELECT evidencija.datum_unosa AS "Datum Unosa", evidencija.promijenjena_kolicina AS "Promijenjena Kolicina", proizvod.name AS Proizvod, proizvod.id AS "ID Proizvoda", tvrtka.name AS Tvrtka, user.username AS Korisnik, receipt.id AS "ID Racuna", receipt.status AS "Status" FROM evidencija INNER JOIN proizvod ON evidencija.proizvod_id=proizvod.id INNER JOIN tvrtka ON evidencija.tvrtka_id=tvrtka.id INNER JOIN user ON evidencija.user_id=user.id INNER JOIN receipt ON evidencija.receipt_id=receipt.id WHERE  user.username= "{}" AND evidencija.vrsta_unosa="unos" AND receipt.status="active"'.format(u))
			elif b==" ":
				sql= text('SELECT evidencija.datum_unosa AS "Datum Unosa", evidencija.promijenjena_kolicina AS "Promijenjena Kolicina", proizvod.name AS Proizvod, proizvod.id AS "ID Proizvoda", tvrtka.name AS Tvrtka, user.username AS Korisnik, receipt.id AS "ID Racuna", receipt.status AS "Status" FROM evidencija INNER JOIN proizvod ON evidencija.proizvod_id=proizvod.id INNER JOIN tvrtka ON evidencija.tvrtka_id=tvrtka.id INNER JOIN user ON evidencija.user_id=user.id INNER JOIN receipt ON evidencija.receipt_id=receipt.id WHERE  user.username= "{}" AND evidencija.datum_unosa <= "{}" AND evidencija.vrsta_unosa="unos" AND receipt.status="active"'.format(u, e))
			elif e==" ":
				sql= text('SELECT evidencija.datum_unosa AS "Datum Unosa", evidencija.promijenjena_kolicina AS "Promijenjena Kolicina", proizvod.name AS Proizvod, proizvod.id AS "ID Proizvoda", tvrtka.name AS Tvrtka, user.username AS Korisnik, receipt.id AS "ID Racuna", receipt.status AS "Status" FROM evidencija INNER JOIN proizvod ON evidencija.proizvod_id=proizvod.id INNER JOIN tvrtka ON evidencija.tvrtka_id=tvrtka.id INNER JOIN user ON evidencija.user_id=user.id INNER JOIN receipt ON evidencija.receipt_id=receipt.id WHERE  user.username= "{}" AND evidencija.datum_unosa >= "{}" AND evidencija.vrsta_unosa="unos" AND receipt.status="active"'.format(u, b))
			else:
				sql= text('SELECT evidencija.datum_unosa AS "Datum Unosa", evidencija.promijenjena_kolicina AS "Promijenjena Kolicina", proizvod.name AS Proizvod, proizvod.id AS "ID Proizvoda", tvrtka.name AS Tvrtka, user.username AS Korisnik, receipt.id AS "ID Racuna", receipt.status AS "Status" FROM evidencija INNER JOIN proizvod ON evidencija.proizvod_id=proizvod.id INNER JOIN tvrtka ON evidencija.tvrtka_id=tvrtka.id INNER JOIN user ON evidencija.user_id=user.id INNER JOIN receipt ON evidencija.receipt_id=receipt.id WHERE  user.username= "{}" AND evidencija.datum_unosa >= "{}" AND evidencija.datum_unosa <= "{}" AND evidencija.vrsta_unosa="unos" AND receipt.status="active"'.format(u, b, e))
	else:
		if u== " ":
			if b==" " and e==" ":
				sql= text('SELECT evidencija.datum_unosa AS "Datum Unosa", evidencija.promijenjena_kolicina AS "Promijenjena Kolicina", proizvod.name AS Proizvod, proizvod.id AS "ID Proizvoda", tvrtka.name AS Tvrtka, user.username AS Korisnik, receipt.id AS "ID Racuna", receipt.status AS "Status" FROM evidencija INNER JOIN proizvod ON evidencija.proizvod_id=proizvod.id INNER JOIN tvrtka ON evidencija.tvrtka_id=tvrtka.id INNER JOIN user ON evidencija.user_id=user.id INNER JOIN receipt ON evidencija.receipt_id=receipt.id WHERE  proizvod.name= "{}" AND evidencija.vrsta_unosa="unos" AND receipt.status="active"'.format(s))
			elif b==" ":
				sql= text('SELECT evidencija.datum_unosa AS "Datum Unosa", evidencija.promijenjena_kolicina AS "Promijenjena Kolicina", proizvod.name AS Proizvod, proizvod.id AS "ID Proizvoda", tvrtka.name AS Tvrtka, user.username AS Korisnik, receipt.id AS "ID Racuna", receipt.status AS "Status" FROM evidencija INNER JOIN proizvod ON evidencija.proizvod_id=proizvod.id INNER JOIN tvrtka ON evidencija.tvrtka_id=tvrtka.id INNER JOIN user ON evidencija.user_id=user.id INNER JOIN receipt ON evidencija.receipt_id=receipt.id WHERE  proizvod.name= "{}" AND evidencija.datum_unosa <= "{}" AND evidencija.vrsta_unosa="unos" AND receipt.status="active"'.format(s, e))
			elif e==" ":
				sql= text('SELECT evidencija.datum_unosa AS "Datum Unosa", evidencija.promijenjena_kolicina AS "Promijenjena Kolicina", proizvod.name AS Proizvod, proizvod.id AS "ID Proizvoda", tvrtka.name AS Tvrtka, user.username AS Korisnik, receipt.id AS "ID Racuna", receipt.status AS "Status" FROM evidencija INNER JOIN proizvod ON evidencija.proizvod_id=proizvod.id INNER JOIN tvrtka ON evidencija.tvrtka_id=tvrtka.id INNER JOIN user ON evidencija.user_id=user.id INNER JOIN receipt ON evidencija.receipt_id=receipt.id WHERE  proizvod.name= "{}" AND evidencija.datum_unosa >= "{}" AND evidencija.vrsta_unosa="unos" AND receipt.status="active"'.format(s, b))
			else:
				sql= text('SELECT evidencija.datum_unosa AS "Datum Unosa", evidencija.promijenjena_kolicina AS "Promijenjena Kolicina", proizvod.name AS Proizvod, proizvod.id AS "ID Proizvoda", tvrtka.name AS Tvrtka, user.username AS Korisnik, receipt.id AS "ID Racuna", receipt.status AS "Status" FROM evidencija INNER JOIN proizvod ON evidencija.proizvod_id=proizvod.id INNER JOIN tvrtka ON evidencija.tvrtka_id=tvrtka.id INNER JOIN user ON evidencija.user_id=user.id INNER JOIN receipt ON evidencija.receipt_id=receipt.id WHERE  proizvod.name= "{}" AND evidencija.datum_unosa >= "{}" AND evidencija.datum_unosa <= "{}" AND evidencija.vrsta_unosa="unos" AND receipt.status="active"'.format(s, b, e))
		else:
			if b==" " and e==" ":
				sql= text('SELECT evidencija.datum_unosa AS "Datum Unosa", evidencija.promijenjena_kolicina AS "Promijenjena Kolicina", proizvod.name AS Proizvod, proizvod.id AS "ID Proizvoda", tvrtka.name AS Tvrtka, user.username AS Korisnik, receipt.id AS "ID Racuna", receipt.status AS "Status" FROM evidencija INNER JOIN proizvod ON evidencija.proizvod_id=proizvod.id INNER JOIN tvrtka ON evidencija.tvrtka_id=tvrtka.id INNER JOIN user ON evidencija.user_id=user.id INNER JOIN receipt ON evidencija.receipt_id=receipt.id WHERE  proizvod.name= "{}" AND user.username= "{}" AND evidencija.vrsta_unosa="unos" AND receipt.status="active"'.format(s, u))
			elif b==" ":
				sql= text('SELECT evidencija.datum_unosa AS "Datum Unosa", evidencija.promijenjena_kolicina AS "Promijenjena Kolicina", proizvod.name AS Proizvod, proizvod.id AS "ID Proizvoda", tvrtka.name AS Tvrtka, user.username AS Korisnik, receipt.id AS "ID Racuna", receipt.status AS "Status" FROM evidencija INNER JOIN proizvod ON evidencija.proizvod_id=proizvod.id INNER JOIN tvrtka ON evidencija.tvrtka_id=tvrtka.id INNER JOIN user ON evidencija.user_id=user.id INNER JOIN receipt ON evidencija.receipt_id=receipt.id WHERE  proizvod.name= "{}" AND user.username= "{}" AND evidencija.datum_unosa <= "{}" AND evidencija.vrsta_unosa="unos" AND receipt.status="active"'.format(s, u, e))
			elif e==" ":
				sql= text('SELECT evidencija.datum_unosa AS "Datum Unosa", evidencija.promijenjena_kolicina AS "Promijenjena Kolicina", proizvod.name AS Proizvod, proizvod.id AS "ID Proizvoda", tvrtka.name AS Tvrtka, user.username AS Korisnik, receipt.id AS "ID Racuna", receipt.status AS "Status" FROM evidencija INNER JOIN proizvod ON evidencija.proizvod_id=proizvod.id INNER JOIN tvrtka ON evidencija.tvrtka_id=tvrtka.id INNER JOIN user ON evidencija.user_id=user.id INNER JOIN receipt ON evidencija.receipt_id=receipt.id WHERE  proizvod.name= "{}" AND user.username= "{}" AND evidencija.datum_unosa >= "{}" AND evidencija.vrsta_unosa="unos" AND receipt.status="active"'.format(s, u, b))				
			else:
				sql= text('SELECT evidencija.datum_unosa AS "Datum Unosa", evidencija.promijenjena_kolicina AS "Promijenjena Kolicina", proizvod.name AS Proizvod, proizvod.id AS "ID Proizvoda", tvrtka.name AS Tvrtka, user.username AS Korisnik, receipt.id AS "ID Racuna", receipt.status AS "Status" FROM evidencija INNER JOIN proizvod ON evidencija.proizvod_id=proizvod.id INNER JOIN tvrtka ON evidencija.tvrtka_id=tvrtka.id INNER JOIN user ON evidencija.user_id=user.id INNER JOIN receipt ON evidencija.receipt_id=receipt.id WHERE  proizvod.name= "{}" AND user.username= "{}" AND evidencija.datum_unosa >= "{}" AND evidencija.datum_unosa <= "{}" AND evidencija.vrsta_unosa="unos" AND receipt.status="active"'.format(s, u, b, e))

	
	result= db.engine.execute(sql)
	query_sets = []
	for r in result:
		query_sets.append(r)
	column_names = [
		'Datum Unosa',
		'Promijenjena Kolicina',
		'Proizvod',
		'ID Proizvoda',
		'Tvrtka',
		'Korisnik',
		'ID Racuna'
		]
	return excel.make_response_from_query_sets(query_sets, column_names, 'xls', file_name="Ulazna evidencija "+ "proizvoda "+s+" od "+b+" do "+e+" korisnik "+u)

@app.route('/export_proizvod_unos_storno/<s>+<b>+<e>+<u>')
@login_required
def export_proizvod_unos_storno(s, b, e, u):
	if s== " ":
		if u== " ":
			if b==" " and e==" ":
				sql= text('SELECT evidencija.datum_unosa AS "Datum Unosa", evidencija.promijenjena_kolicina AS "Promijenjena Kolicina", proizvod.name AS Proizvod, proizvod.id AS "ID Proizvoda", tvrtka.name AS Tvrtka, u.username AS Korisnik, receipt.id AS "ID Racuna", receipt.status AS "Status", receipt.storno_date AS "Datum Storniranja", s.username AS "Stornirao" FROM evidencija INNER JOIN proizvod ON evidencija.proizvod_id=proizvod.id INNER JOIN tvrtka ON evidencija.tvrtka_id=tvrtka.id INNER JOIN user u ON evidencija.user_id=u.id INNER JOIN user s ON receipt.storno_user=s.id INNER JOIN receipt ON evidencija.receipt_id=receipt.id WHERE evidencija.vrsta_unosa="unos" AND receipt.status="storno"')
			elif b==" ":
				sql= text('SELECT evidencija.datum_unosa AS "Datum Unosa", evidencija.promijenjena_kolicina AS "Promijenjena Kolicina", proizvod.name AS Proizvod, proizvod.id AS "ID Proizvoda", tvrtka.name AS Tvrtka, u.username AS Korisnik, receipt.id AS "ID Racuna", receipt.status AS "Status", receipt.storno_date AS "Datum Storniranja", s.username AS "Stornirao" FROM evidencija INNER JOIN proizvod ON evidencija.proizvod_id=proizvod.id INNER JOIN tvrtka ON evidencija.tvrtka_id=tvrtka.id INNER JOIN user u ON evidencija.user_id=u.id INNER JOIN user s ON receipt.storno_user=s.id INNER JOIN receipt ON evidencija.receipt_id=receipt.id WHERE evidencija.datum_unosa <= "{}" AND evidencija.vrsta_unosa="unos" AND receipt.status="storno"'.format(e))
			elif e==" ":
				sql= text('SELECT evidencija.datum_unosa AS "Datum Unosa", evidencija.promijenjena_kolicina AS "Promijenjena Kolicina", proizvod.name AS Proizvod, proizvod.id AS "ID Proizvoda", tvrtka.name AS Tvrtka, u.username AS Korisnik, receipt.id AS "ID Racuna", receipt.status AS "Status", receipt.storno_date AS "Datum Storniranja", s.username AS "Stornirao" FROM evidencija INNER JOIN proizvod ON evidencija.proizvod_id=proizvod.id INNER JOIN tvrtka ON evidencija.tvrtka_id=tvrtka.id INNER JOIN user u ON evidencija.user_id=u.id INNER JOIN user s ON receipt.storno_user=s.id INNER JOIN receipt ON evidencija.receipt_id=receipt.id WHERE evidencija.datum_unosa >= "{}" AND evidencija.vrsta_unosa="unos" AND receipt.status="storno"'.format(b))
			else:
				sql= text('SELECT evidencija.datum_unosa AS "Datum Unosa", evidencija.promijenjena_kolicina AS "Promijenjena Kolicina", proizvod.name AS Proizvod, proizvod.id AS "ID Proizvoda", tvrtka.name AS Tvrtka, u.username AS Korisnik, receipt.id AS "ID Racuna", receipt.status AS "Status", receipt.storno_date AS "Datum Storniranja", s.username AS "Stornirao" FROM evidencija INNER JOIN proizvod ON evidencija.proizvod_id=proizvod.id INNER JOIN tvrtka ON evidencija.tvrtka_id=tvrtka.id INNER JOIN user u ON evidencija.user_id=u.id INNER JOIN user s ON receipt.storno_user=s.id INNER JOIN receipt ON evidencija.receipt_id=receipt.id WHERE evidencija.datum_unosa >= "{}" AND evidencija.datum_unosa <= "{}" AND evidencija.vrsta_unosa="unos" AND receipt.status="storno"'.format(b, e))
		else:
			if b==" " and e==" ":
				sql= text('SELECT evidencija.datum_unosa AS "Datum Unosa", evidencija.promijenjena_kolicina AS "Promijenjena Kolicina", proizvod.name AS Proizvod, proizvod.id AS "ID Proizvoda", tvrtka.name AS Tvrtka, u.username AS Korisnik, receipt.id AS "ID Racuna", receipt.status AS "Status", receipt.storno_date AS "Datum Storniranja", s.username AS "Stornirao" FROM evidencija INNER JOIN proizvod ON evidencija.proizvod_id=proizvod.id INNER JOIN tvrtka ON evidencija.tvrtka_id=tvrtka.id INNER JOIN user u ON evidencija.user_id=u.id INNER JOIN user s ON receipt.storno_user=s.id INNER JOIN receipt ON evidencija.receipt_id=receipt.id WHERE  u.username= "{}" AND evidencija.vrsta_unosa="unos" AND receipt.status="storno"'.format(u))
			elif b==" ":
				sql= text('SELECT evidencija.datum_unosa AS "Datum Unosa", evidencija.promijenjena_kolicina AS "Promijenjena Kolicina", proizvod.name AS Proizvod, proizvod.id AS "ID Proizvoda", tvrtka.name AS Tvrtka, u.username AS Korisnik, receipt.id AS "ID Racuna", receipt.status AS "Status", receipt.storno_date AS "Datum Storniranja", s.username AS "Stornirao" FROM evidencija INNER JOIN proizvod ON evidencija.proizvod_id=proizvod.id INNER JOIN tvrtka ON evidencija.tvrtka_id=tvrtka.id INNER JOIN user u ON evidencija.user_id=u.id INNER JOIN user s ON receipt.storno_user=s.id INNER JOIN receipt ON evidencija.receipt_id=receipt.id WHERE  u.username= "{}" AND evidencija.datum_unosa <= "{}" AND evidencija.vrsta_unosa="unos" AND receipt.status="storno"'.format(u, e))
			elif e==" ":
				sql= text('SELECT evidencija.datum_unosa AS "Datum Unosa", evidencija.promijenjena_kolicina AS "Promijenjena Kolicina", proizvod.name AS Proizvod, proizvod.id AS "ID Proizvoda", tvrtka.name AS Tvrtka, u.username AS Korisnik, receipt.id AS "ID Racuna", receipt.status AS "Status", receipt.storno_date AS "Datum Storniranja", s.username AS "Stornirao" FROM evidencija INNER JOIN proizvod ON evidencija.proizvod_id=proizvod.id INNER JOIN tvrtka ON evidencija.tvrtka_id=tvrtka.id INNER JOIN user u ON evidencija.user_id=u.id INNER JOIN user s ON receipt.storno_user=s.id INNER JOIN receipt ON evidencija.receipt_id=receipt.id WHERE  u.username= "{}" AND evidencija.datum_unosa >= "{}" AND evidencija.vrsta_unosa="unos" AND receipt.status="storno"'.format(u, b))
			else:
				sql= text('SELECT evidencija.datum_unosa AS "Datum Unosa", evidencija.promijenjena_kolicina AS "Promijenjena Kolicina", proizvod.name AS Proizvod, proizvod.id AS "ID Proizvoda", tvrtka.name AS Tvrtka, u.username AS Korisnik, receipt.id AS "ID Racuna", receipt.status AS "Status", receipt.storno_date AS "Datum Storniranja", s.username AS "Stornirao" FROM evidencija INNER JOIN proizvod ON evidencija.proizvod_id=proizvod.id INNER JOIN tvrtka ON evidencija.tvrtka_id=tvrtka.id INNER JOIN user u ON evidencija.user_id=u.id INNER JOIN user s ON receipt.storno_user=s.id INNER JOIN receipt ON evidencija.receipt_id=receipt.id WHERE  u.username= "{}" AND evidencija.datum_unosa >= "{}" AND evidencija.datum_unosa <= "{}" AND evidencija.vrsta_unosa="unos" AND receipt.status="storno"'.format(u, b, e))
	else:
		if u== " ":
			if b==" " and e==" ":
				sql= text('SELECT evidencija.datum_unosa AS "Datum Unosa", evidencija.promijenjena_kolicina AS "Promijenjena Kolicina", proizvod.name AS Proizvod, proizvod.id AS "ID Proizvoda", tvrtka.name AS Tvrtka, u.username AS Korisnik, receipt.id AS "ID Racuna", receipt.status AS "Status", receipt.storno_date AS "Datum Storniranja", s.username AS "Stornirao" FROM evidencija INNER JOIN proizvod ON evidencija.proizvod_id=proizvod.id INNER JOIN tvrtka ON evidencija.tvrtka_id=tvrtka.id INNER JOIN user u ON evidencija.user_id=u.id INNER JOIN user s ON receipt.storno_user=s.id INNER JOIN receipt ON evidencija.receipt_id=receipt.id WHERE  proizvod.name= "{}" AND evidencija.vrsta_unosa="unos" AND receipt.status="storno"'.format(s))
			elif b==" ":
				sql= text('SELECT evidencija.datum_unosa AS "Datum Unosa", evidencija.promijenjena_kolicina AS "Promijenjena Kolicina", proizvod.name AS Proizvod, proizvod.id AS "ID Proizvoda", tvrtka.name AS Tvrtka, u.username AS Korisnik, receipt.id AS "ID Racuna", receipt.status AS "Status", receipt.storno_date AS "Datum Storniranja", s.username AS "Stornirao" FROM evidencija INNER JOIN proizvod ON evidencija.proizvod_id=proizvod.id INNER JOIN tvrtka ON evidencija.tvrtka_id=tvrtka.id INNER JOIN user u ON evidencija.user_id=u.id INNER JOIN user s ON receipt.storno_user=s.id INNER JOIN receipt ON evidencija.receipt_id=receipt.id WHERE  proizvod.name= "{}" AND evidencija.datum_unosa <= "{}" AND evidencija.vrsta_unosa="unos" AND receipt.status="storno"'.format(s, e))
			elif e==" ":
				sql= text('SELECT evidencija.datum_unosa AS "Datum Unosa", evidencija.promijenjena_kolicina AS "Promijenjena Kolicina", proizvod.name AS Proizvod, proizvod.id AS "ID Proizvoda", tvrtka.name AS Tvrtka, u.username AS Korisnik, receipt.id AS "ID Racuna", receipt.status AS "Status", receipt.storno_date AS "Datum Storniranja", s.username AS "Stornirao" FROM evidencija INNER JOIN proizvod ON evidencija.proizvod_id=proizvod.id INNER JOIN tvrtka ON evidencija.tvrtka_id=tvrtka.id INNER JOIN user u ON evidencija.user_id=u.id INNER JOIN user s ON receipt.storno_user=s.id INNER JOIN receipt ON evidencija.receipt_id=receipt.id WHERE  proizvod.name= "{}" AND evidencija.datum_unosa >= "{}" AND evidencija.vrsta_unosa="unos" AND receipt.status="storno"'.format(s, b))
			else:
				sql= text('SELECT evidencija.datum_unosa AS "Datum Unosa", evidencija.promijenjena_kolicina AS "Promijenjena Kolicina", proizvod.name AS Proizvod, proizvod.id AS "ID Proizvoda", tvrtka.name AS Tvrtka, u.username AS Korisnik, receipt.id AS "ID Racuna", receipt.status AS "Status", receipt.storno_date AS "Datum Storniranja", s.username AS "Stornirao" FROM evidencija INNER JOIN proizvod ON evidencija.proizvod_id=proizvod.id INNER JOIN tvrtka ON evidencija.tvrtka_id=tvrtka.id INNER JOIN user u ON evidencija.user_id=u.id INNER JOIN user s ON receipt.storno_user=s.id INNER JOIN receipt ON evidencija.receipt_id=receipt.id WHERE  proizvod.name= "{}" AND evidencija.datum_unosa >= "{}" AND evidencija.datum_unosa <= "{}" AND evidencija.vrsta_unosa="unos" AND receipt.status="storno"'.format(s, b, e))
		else:
			if b==" " and e==" ":
				sql= text('SELECT evidencija.datum_unosa AS "Datum Unosa", evidencija.promijenjena_kolicina AS "Promijenjena Kolicina", proizvod.name AS Proizvod, proizvod.id AS "ID Proizvoda", tvrtka.name AS Tvrtka, u.username AS Korisnik, receipt.id AS "ID Racuna", receipt.status AS "Status", receipt.storno_date AS "Datum Storniranja", s.username AS "Stornirao" FROM evidencija INNER JOIN proizvod ON evidencija.proizvod_id=proizvod.id INNER JOIN tvrtka ON evidencija.tvrtka_id=tvrtka.id INNER JOIN user u ON evidencija.user_id=u.id INNER JOIN user s ON receipt.storno_user=s.id INNER JOIN receipt ON evidencija.receipt_id=receipt.id WHERE  proizvod.name= "{}" AND u.username= "{}" AND evidencija.vrsta_unosa="unos" AND receipt.status="storno"'.format(s, u))
			elif b==" ":
				sql= text('SELECT evidencija.datum_unosa AS "Datum Unosa", evidencija.promijenjena_kolicina AS "Promijenjena Kolicina", proizvod.name AS Proizvod, proizvod.id AS "ID Proizvoda", tvrtka.name AS Tvrtka, u.username AS Korisnik, receipt.id AS "ID Racuna", receipt.status AS "Status", receipt.storno_date AS "Datum Storniranja", s.username AS "Stornirao" FROM evidencija INNER JOIN proizvod ON evidencija.proizvod_id=proizvod.id INNER JOIN tvrtka ON evidencija.tvrtka_id=tvrtka.id INNER JOIN user u ON evidencija.user_id=u.id INNER JOIN user s ON receipt.storno_user=s.id INNER JOIN receipt ON evidencija.receipt_id=receipt.id WHERE  proizvod.name= "{}" AND u.username= "{}" AND evidencija.datum_unosa <= "{}" AND evidencija.vrsta_unosa="unos" AND receipt.status="storno"'.format(s, u, e))
			elif e==" ":
				sql= text('SELECT evidencija.datum_unosa AS "Datum Unosa", evidencija.promijenjena_kolicina AS "Promijenjena Kolicina", proizvod.name AS Proizvod, proizvod.id AS "ID Proizvoda", tvrtka.name AS Tvrtka, u.username AS Korisnik, receipt.id AS "ID Racuna", receipt.status AS "Status", receipt.storno_date AS "Datum Storniranja", s.username AS "Stornirao" FROM evidencija INNER JOIN proizvod ON evidencija.proizvod_id=proizvod.id INNER JOIN tvrtka ON evidencija.tvrtka_id=tvrtka.id INNER JOIN user u ON evidencija.user_id=u.id INNER JOIN user s ON receipt.storno_user=s.id INNER JOIN receipt ON evidencija.receipt_id=receipt.id WHERE  proizvod.name= "{}" AND u.username= "{}" AND evidencija.datum_unosa >= "{}" AND evidencija.vrsta_unosa="unos" AND receipt.status="storno"'.format(s, u, b))				
			else:
				sql= text('SELECT evidencija.datum_unosa AS "Datum Unosa", evidencija.promijenjena_kolicina AS "Promijenjena Kolicina", proizvod.name AS Proizvod, proizvod.id AS "ID Proizvoda", tvrtka.name AS Tvrtka, u.username AS Korisnik, receipt.id AS "ID Racuna", receipt.status AS "Status", receipt.storno_date AS "Datum Storniranja", s.username AS "Stornirao" FROM evidencija INNER JOIN proizvod ON evidencija.proizvod_id=proizvod.id INNER JOIN tvrtka ON evidencija.tvrtka_id=tvrtka.id INNER JOIN user u ON evidencija.user_id=u.id INNER JOIN user s ON receipt.storno_user=s.id INNER JOIN receipt ON evidencija.receipt_id=receipt.id WHERE  proizvod.name= "{}" AND u.username= "{}" AND evidencija.datum_unosa >= "{}" AND evidencija.datum_unosa <= "{}" AND evidencija.vrsta_unosa="unos" AND receipt.status="storno"'.format(s, u, b, e))

	result= db.engine.execute(sql)
	query_sets = []
	for r in result:
		query_sets.append(r)
	column_names = [
		'Datum Unosa',
		'Promijenjena Kolicina',
		'Proizvod',
		'ID Proizvoda',
		'Tvrtka',
		'Korisnik',
		'ID Racuna',
		'Datum Storniranja',
		'Stornirao'
		]
	return excel.make_response_from_query_sets(query_sets, column_names, 'xls', file_name="Ulazna evidencija storno "+ "proizvoda "+s+" od "+b+" do "+e+" korisnik "+u)

@app.route('/export_proizvod_izlaz/<s>+<b>+<e>+<u>')
@login_required
def export_proizvod_izlaz(s, b, e, u):
	if s== " ":
		if u== " ":
			if b==" " and e==" ":
				sql= text('SELECT evidencija.datum_unosa AS "Datum Izdavanja", evidencija.promijenjena_kolicina AS "Promijenjena Kolicina", proizvod.name AS Proizvod, proizvod.id AS "ID Proizvoda", tvrtka.name AS Tvrtka, user.username AS Korisnik, receipt.id AS "ID Racuna", receipt.status AS "Status" FROM evidencija INNER JOIN proizvod ON evidencija.proizvod_id=proizvod.id INNER JOIN tvrtka ON evidencija.tvrtka_id=tvrtka.id INNER JOIN user ON evidencija.user_id=user.id INNER JOIN receipt ON evidencija.receipt_id=receipt.id WHERE evidencija.vrsta_unosa="izlaz" AND receipt.status="active"')
			elif b==" ":
				sql= text('SELECT evidencija.datum_unosa AS "Datum Izdavanja", evidencija.promijenjena_kolicina AS "Promijenjena Kolicina", proizvod.name AS Proizvod, proizvod.id AS "ID Proizvoda", tvrtka.name AS Tvrtka, user.username AS Korisnik, receipt.id AS "ID Racuna", receipt.status AS "Status" FROM evidencija INNER JOIN proizvod ON evidencija.proizvod_id=proizvod.id INNER JOIN tvrtka ON evidencija.tvrtka_id=tvrtka.id INNER JOIN user ON evidencija.user_id=user.id INNER JOIN receipt ON evidencija.receipt_id=receipt.id WHERE evidencija.datum_unosa <= "{}" AND evidencija.vrsta_unosa="izlaz" AND receipt.status="active"'.format(e))
			elif e==" ":
				sql= text('SELECT evidencija.datum_unosa AS "Datum Izdavanja", evidencija.promijenjena_kolicina AS "Promijenjena Kolicina", proizvod.name AS Proizvod, proizvod.id AS "ID Proizvoda", tvrtka.name AS Tvrtka, user.username AS Korisnik, receipt.id AS "ID Racuna", receipt.status AS "Status" FROM evidencija INNER JOIN proizvod ON evidencija.proizvod_id=proizvod.id INNER JOIN tvrtka ON evidencija.tvrtka_id=tvrtka.id INNER JOIN user ON evidencija.user_id=user.id INNER JOIN receipt ON evidencija.receipt_id=receipt.id WHERE evidencija.datum_unosa >= "{}" AND evidencija.vrsta_unosa="izlaz" AND receipt.status="active"'.format(b))
			else:
				sql= text('SELECT evidencija.datum_unosa AS "Datum Izdavanja", evidencija.promijenjena_kolicina AS "Promijenjena Kolicina", proizvod.name AS Proizvod, proizvod.id AS "ID Proizvoda", tvrtka.name AS Tvrtka, user.username AS Korisnik, receipt.id AS "ID Racuna", receipt.status AS "Status" FROM evidencija INNER JOIN proizvod ON evidencija.proizvod_id=proizvod.id INNER JOIN tvrtka ON evidencija.tvrtka_id=tvrtka.id INNER JOIN user ON evidencija.user_id=user.id INNER JOIN receipt ON evidencija.receipt_id=receipt.id WHERE evidencija.datum_unosa >= "{}" AND evidencija.datum_unosa <= "{}" AND evidencija.vrsta_unosa="izlaz" AND receipt.status="active"'.format(b, e))
		else:
			if b==" " and e==" ":
				sql= text('SELECT evidencija.datum_unosa AS "Datum Izdavanja", evidencija.promijenjena_kolicina AS "Promijenjena Kolicina", proizvod.name AS Proizvod, proizvod.id AS "ID Proizvoda", tvrtka.name AS Tvrtka, user.username AS Korisnik, receipt.id AS "ID Racuna", receipt.status AS "Status" FROM evidencija INNER JOIN proizvod ON evidencija.proizvod_id=proizvod.id INNER JOIN tvrtka ON evidencija.tvrtka_id=tvrtka.id INNER JOIN user ON evidencija.user_id=user.id INNER JOIN receipt ON evidencija.receipt_id=receipt.id WHERE  user.username= "{}" AND evidencija.vrsta_unosa="izlaz" AND receipt.status="active"'.format(u))
			elif b==" ":
				sql= text('SELECT evidencija.datum_unosa AS "Datum Izdavanja", evidencija.promijenjena_kolicina AS "Promijenjena Kolicina", proizvod.name AS Proizvod, proizvod.id AS "ID Proizvoda", tvrtka.name AS Tvrtka, user.username AS Korisnik, receipt.id AS "ID Racuna", receipt.status AS "Status" FROM evidencija INNER JOIN proizvod ON evidencija.proizvod_id=proizvod.id INNER JOIN tvrtka ON evidencija.tvrtka_id=tvrtka.id INNER JOIN user ON evidencija.user_id=user.id INNER JOIN receipt ON evidencija.receipt_id=receipt.id WHERE  user.username= "{}" AND evidencija.datum_unosa <= "{}" AND evidencija.vrsta_unosa="izlaz" AND receipt.status="active"'.format(u, e))
			elif e==" ":
				sql= text('SELECT evidencija.datum_unosa AS "Datum Izdavanja", evidencija.promijenjena_kolicina AS "Promijenjena Kolicina", proizvod.name AS Proizvod, proizvod.id AS "ID Proizvoda", tvrtka.name AS Tvrtka, user.username AS Korisnik, receipt.id AS "ID Racuna", receipt.status AS "Status" FROM evidencija INNER JOIN proizvod ON evidencija.proizvod_id=proizvod.id INNER JOIN tvrtka ON evidencija.tvrtka_id=tvrtka.id INNER JOIN user ON evidencija.user_id=user.id INNER JOIN receipt ON evidencija.receipt_id=receipt.id WHERE  user.username= "{}" AND evidencija.datum_unosa >= "{}" AND evidencija.vrsta_unosa="izlaz" AND receipt.status="active"'.format(u, b))
			else:
				sql= text('SELECT evidencija.datum_unosa AS "Datum Izdavanja", evidencija.promijenjena_kolicina AS "Promijenjena Kolicina", proizvod.name AS Proizvod, proizvod.id AS "ID Proizvoda", tvrtka.name AS Tvrtka, user.username AS Korisnik, receipt.id AS "ID Racuna", receipt.status AS "Status" FROM evidencija INNER JOIN proizvod ON evidencija.proizvod_id=proizvod.id INNER JOIN tvrtka ON evidencija.tvrtka_id=tvrtka.id INNER JOIN user ON evidencija.user_id=user.id INNER JOIN receipt ON evidencija.receipt_id=receipt.id WHERE  user.username= "{}" AND evidencija.datum_unosa >= "{}" AND evidencija.datum_unosa <= "{}" AND evidencija.vrsta_unosa="izlaz" AND receipt.status="active"'.format(u, b, e))
	else:
		if u== " ":
			if b==" " and e==" ":
				sql= text('SELECT evidencija.datum_unosa AS "Datum Izdavanja", evidencija.promijenjena_kolicina AS "Promijenjena Kolicina", proizvod.name AS Proizvod, proizvod.id AS "ID Proizvoda", tvrtka.name AS Tvrtka, user.username AS Korisnik, receipt.id AS "ID Racuna", receipt.status AS "Status" FROM evidencija INNER JOIN proizvod ON evidencija.proizvod_id=proizvod.id INNER JOIN tvrtka ON evidencija.tvrtka_id=tvrtka.id INNER JOIN user ON evidencija.user_id=user.id INNER JOIN receipt ON evidencija.receipt_id=receipt.id WHERE  proizvod.name= "{}" AND evidencija.vrsta_unosa="izlaz" AND receipt.status="active"'.format(s))
			elif b==" ":
				sql= text('SELECT evidencija.datum_unosa AS "Datum Izdavanja", evidencija.promijenjena_kolicina AS "Promijenjena Kolicina", proizvod.name AS Proizvod, proizvod.id AS "ID Proizvoda", tvrtka.name AS Tvrtka, user.username AS Korisnik, receipt.id AS "ID Racuna", receipt.status AS "Status" FROM evidencija INNER JOIN proizvod ON evidencija.proizvod_id=proizvod.id INNER JOIN tvrtka ON evidencija.tvrtka_id=tvrtka.id INNER JOIN user ON evidencija.user_id=user.id INNER JOIN receipt ON evidencija.receipt_id=receipt.id WHERE  proizvod.name= "{}" AND evidencija.datum_unosa <= "{}" AND evidencija.vrsta_unosa="izlaz" AND receipt.status="active"'.format(s, e))
			elif e==" ":
				sql= text('SELECT evidencija.datum_unosa AS "Datum Izdavanja", evidencija.promijenjena_kolicina AS "Promijenjena Kolicina", proizvod.name AS Proizvod, proizvod.id AS "ID Proizvoda", tvrtka.name AS Tvrtka, user.username AS Korisnik, receipt.id AS "ID Racuna", receipt.status AS "Status" FROM evidencija INNER JOIN proizvod ON evidencija.proizvod_id=proizvod.id INNER JOIN tvrtka ON evidencija.tvrtka_id=tvrtka.id INNER JOIN user ON evidencija.user_id=user.id INNER JOIN receipt ON evidencija.receipt_id=receipt.id WHERE  proizvod.name= "{}" AND evidencija.datum_unosa >= "{}" AND evidencija.vrsta_unosa="izlaz" AND receipt.status="active"'.format(s, b))
			else:
				sql= text('SELECT evidencija.datum_unosa AS "Datum Izdavanja", evidencija.promijenjena_kolicina AS "Promijenjena Kolicina", proizvod.name AS Proizvod, proizvod.id AS "ID Proizvoda", tvrtka.name AS Tvrtka, user.username AS Korisnik, receipt.id AS "ID Racuna", receipt.status AS "Status" FROM evidencija INNER JOIN proizvod ON evidencija.proizvod_id=proizvod.id INNER JOIN tvrtka ON evidencija.tvrtka_id=tvrtka.id INNER JOIN user ON evidencija.user_id=user.id INNER JOIN receipt ON evidencija.receipt_id=receipt.id WHERE  proizvod.name= "{}" AND evidencija.datum_unosa >= "{}" AND evidencija.datum_unosa <= "{}" AND evidencija.vrsta_unosa="unos" AND receipt.status="active"'.format(s, b, e))
		else:
			if b==" " and e==" ":
				sql= text('SELECT evidencija.datum_unosa AS "Datum Izdavanja", evidencija.promijenjena_kolicina AS "Promijenjena Kolicina", proizvod.name AS Proizvod, proizvod.id AS "ID Proizvoda", tvrtka.name AS Tvrtka, user.username AS Korisnik, receipt.id AS "ID Racuna", receipt.status AS "Status" FROM evidencija INNER JOIN proizvod ON evidencija.proizvod_id=proizvod.id INNER JOIN tvrtka ON evidencija.tvrtka_id=tvrtka.id INNER JOIN user ON evidencija.user_id=user.id INNER JOIN receipt ON evidencija.receipt_id=receipt.id WHERE  proizvod.name= "{}" AND user.username= "{}" AND evidencija.vrsta_unosa="izlaz" AND receipt.status="active"'.format(s, u))
			elif b==" ":
				sql= text('SELECT evidencija.datum_unosa AS "Datum Izdavanja", evidencija.promijenjena_kolicina AS "Promijenjena Kolicina", proizvod.name AS Proizvod, proizvod.id AS "ID Proizvoda", tvrtka.name AS Tvrtka, user.username AS Korisnik, receipt.id AS "ID Racuna", receipt.status AS "Status" FROM evidencija INNER JOIN proizvod ON evidencija.proizvod_id=proizvod.id INNER JOIN tvrtka ON evidencija.tvrtka_id=tvrtka.id INNER JOIN user ON evidencija.user_id=user.id INNER JOIN receipt ON evidencija.receipt_id=receipt.id WHERE  proizvod.name= "{}" AND user.username= "{}" AND evidencija.datum_unosa <= "{}" AND evidencija.vrsta_unosa="izlaz" AND receipt.status="active"'.format(s, u, e))
			elif e==" ":
				sql= text('SELECT evidencija.datum_unosa AS "Datum Izdavanja", evidencija.promijenjena_kolicina AS "Promijenjena Kolicina", proizvod.name AS Proizvod, proizvod.id AS "ID Proizvoda", tvrtka.name AS Tvrtka, user.username AS Korisnik, receipt.id AS "ID Racuna", receipt.status AS "Status" FROM evidencija INNER JOIN proizvod ON evidencija.proizvod_id=proizvod.id INNER JOIN tvrtka ON evidencija.tvrtka_id=tvrtka.id INNER JOIN user ON evidencija.user_id=user.id INNER JOIN receipt ON evidencija.receipt_id=receipt.id WHERE  proizvod.name= "{}" AND user.username= "{}" AND evidencija.datum_unosa >= "{}" AND evidencija.vrsta_unosa="izlaz" AND receipt.status="active"'.format(s, u, b))				
			else:
				sql= text('SELECT evidencija.datum_unosa AS "Datum Izdavanja", evidencija.promijenjena_kolicina AS "Promijenjena Kolicina", proizvod.name AS Proizvod, proizvod.id AS "ID Proizvoda", tvrtka.name AS Tvrtka, user.username AS Korisnik, receipt.id AS "ID Racuna", receipt.status AS "Status" FROM evidencija INNER JOIN proizvod ON evidencija.proizvod_id=proizvod.id INNER JOIN tvrtka ON evidencija.tvrtka_id=tvrtka.id INNER JOIN user ON evidencija.user_id=user.id INNER JOIN receipt ON evidencija.receipt_id=receipt.id WHERE  proizvod.name= "{}" AND user.username= "{}" AND evidencija.datum_unosa >= "{}" AND evidencija.datum_unosa <= "{}" AND evidencija.vrsta_unosa="izlaz" AND receipt.status="active"'.format(s, u, b, e))

	
	result= db.engine.execute(sql)
	query_sets = []
	for r in result:
		query_sets.append(r)
	column_names = [
		'Datum Izdavanja',
		'Promijenjena Kolicina',
		'Proizvod',
		'ID Proizvoda',
		'Tvrtka',
		'Korisnik',
		'ID Racuna'
		]
	return excel.make_response_from_query_sets(query_sets, column_names, 'xls', file_name="Izlazna evidencija "+ "proizvoda "+s+" od "+b+" do "+e+" korisnik "+u)

@app.route('/export_proizvod_izlaz_storno/<s>+<b>+<e>+<u>')
@login_required
def export_proizvod_izlaz_storno(s, b, e, u):
	if s== " ":
		if u== " ":
			if b==" " and e==" ":
				sql= text('SELECT evidencija.datum_unosa AS "Datum Izdavanja", evidencija.promijenjena_kolicina AS "Promijenjena Kolicina", proizvod.name AS Proizvod, proizvod.id AS "ID Proizvoda", tvrtka.name AS Tvrtka, u.username AS Korisnik, receipt.id AS "ID Racuna", receipt.status AS "Status", receipt.storno_date AS "Datum Storniranja", s.username AS "Stornirao" FROM evidencija INNER JOIN proizvod ON evidencija.proizvod_id=proizvod.id INNER JOIN tvrtka ON evidencija.tvrtka_id=tvrtka.id INNER JOIN user u ON evidencija.user_id=u.id INNER JOIN user s ON receipt.storno_user=s.id INNER JOIN receipt ON evidencija.receipt_id=receipt.id WHERE evidencija.vrsta_unosa="izlaz" AND receipt.status="storno"')
			elif b==" ":
				sql= text('SELECT evidencija.datum_unosa AS "Datum Izdavanja", evidencija.promijenjena_kolicina AS "Promijenjena Kolicina", proizvod.name AS Proizvod, proizvod.id AS "ID Proizvoda", tvrtka.name AS Tvrtka, u.username AS Korisnik, receipt.id AS "ID Racuna", receipt.status AS "Status", receipt.storno_date AS "Datum Storniranja", s.username AS "Stornirao" FROM evidencija INNER JOIN proizvod ON evidencija.proizvod_id=proizvod.id INNER JOIN tvrtka ON evidencija.tvrtka_id=tvrtka.id INNER JOIN user u ON evidencija.user_id=u.id INNER JOIN user s ON receipt.storno_user=s.id INNER JOIN receipt ON evidencija.receipt_id=receipt.id WHERE evidencija.datum_unosa <= "{}" AND evidencija.vrsta_unosa="izlaz" AND receipt.status="storno"'.format(e))
			elif e==" ":
				sql= text('SELECT evidencija.datum_unosa AS "Datum Izdavanja", evidencija.promijenjena_kolicina AS "Promijenjena Kolicina", proizvod.name AS Proizvod, proizvod.id AS "ID Proizvoda", tvrtka.name AS Tvrtka, u.username AS Korisnik, receipt.id AS "ID Racuna", receipt.status AS "Status", receipt.storno_date AS "Datum Storniranja", s.username AS "Stornirao" FROM evidencija INNER JOIN proizvod ON evidencija.proizvod_id=proizvod.id INNER JOIN tvrtka ON evidencija.tvrtka_id=tvrtka.id INNER JOIN user u ON evidencija.user_id=u.id INNER JOIN user s ON receipt.storno_user=s.id INNER JOIN receipt ON evidencija.receipt_id=receipt.id WHERE evidencija.datum_unosa >= "{}" AND evidencija.vrsta_unosa="izlaz" AND receipt.status="storno"'.format(b))
			else:
				sql= text('SELECT evidencija.datum_unosa AS "Datum Izdavanja", evidencija.promijenjena_kolicina AS "Promijenjena Kolicina", proizvod.name AS Proizvod, proizvod.id AS "ID Proizvoda", tvrtka.name AS Tvrtka, u.username AS Korisnik, receipt.id AS "ID Racuna", receipt.status AS "Status", receipt.storno_date AS "Datum Storniranja", s.username AS "Stornirao" FROM evidencija INNER JOIN proizvod ON evidencija.proizvod_id=proizvod.id INNER JOIN tvrtka ON evidencija.tvrtka_id=tvrtka.id INNER JOIN user u ON evidencija.user_id=u.id INNER JOIN user s ON receipt.storno_user=s.id INNER JOIN receipt ON evidencija.receipt_id=receipt.id WHERE evidencija.datum_unosa >= "{}" AND evidencija.datum_unosa <= "{}" AND evidencija.vrsta_unosa="izlaz" AND receipt.status="storno"'.format(b, e))
		else:
			if b==" " and e==" ":
				sql= text('SELECT evidencija.datum_unosa AS "Datum Izdavanja", evidencija.promijenjena_kolicina AS "Promijenjena Kolicina", proizvod.name AS Proizvod, proizvod.id AS "ID Proizvoda", tvrtka.name AS Tvrtka, u.username AS Korisnik, receipt.id AS "ID Racuna", receipt.status AS "Status", receipt.storno_date AS "Datum Storniranja", s.username AS "Stornirao" FROM evidencija INNER JOIN proizvod ON evidencija.proizvod_id=proizvod.id INNER JOIN tvrtka ON evidencija.tvrtka_id=tvrtka.id INNER JOIN user u ON evidencija.user_id=u.id INNER JOIN user s ON receipt.storno_user=s.id INNER JOIN receipt ON evidencija.receipt_id=receipt.id WHERE  u.username= "{}" AND evidencija.vrsta_unosa="izlaz" AND receipt.status="storno"'.format(u))
			elif b==" ":
				sql= text('SELECT evidencija.datum_unosa AS "Datum Izdavanja", evidencija.promijenjena_kolicina AS "Promijenjena Kolicina", proizvod.name AS Proizvod, proizvod.id AS "ID Proizvoda", tvrtka.name AS Tvrtka, u.username AS Korisnik, receipt.id AS "ID Racuna", receipt.status AS "Status", receipt.storno_date AS "Datum Storniranja", s.username AS "Stornirao" FROM evidencija INNER JOIN proizvod ON evidencija.proizvod_id=proizvod.id INNER JOIN tvrtka ON evidencija.tvrtka_id=tvrtka.id INNER JOIN user u ON evidencija.user_id=u.id INNER JOIN user s ON receipt.storno_user=s.id INNER JOIN receipt ON evidencija.receipt_id=receipt.id WHERE  u.username= "{}" AND evidencija.datum_unosa <= "{}" AND evidencija.vrsta_unosa="izlaz" AND receipt.status="storno"'.format(u, e))
			elif e==" ":
				sql= text('SELECT evidencija.datum_unosa AS "Datum Izdavanja", evidencija.promijenjena_kolicina AS "Promijenjena Kolicina", proizvod.name AS Proizvod, proizvod.id AS "ID Proizvoda", tvrtka.name AS Tvrtka, u.username AS Korisnik, receipt.id AS "ID Racuna", receipt.status AS "Status", receipt.storno_date AS "Datum Storniranja", s.username AS "Stornirao" FROM evidencija INNER JOIN proizvod ON evidencija.proizvod_id=proizvod.id INNER JOIN tvrtka ON evidencija.tvrtka_id=tvrtka.id INNER JOIN user u ON evidencija.user_id=u.id INNER JOIN user s ON receipt.storno_user=s.id INNER JOIN receipt ON evidencija.receipt_id=receipt.id WHERE  u.username= "{}" AND evidencija.datum_unosa >= "{}" AND evidencija.vrsta_unosa="izlaz" AND receipt.status="storno"'.format(u, b))
			else:
				sql= text('SELECT evidencija.datum_unosa AS "Datum Izdavanja", evidencija.promijenjena_kolicina AS "Promijenjena Kolicina", proizvod.name AS Proizvod, proizvod.id AS "ID Proizvoda", tvrtka.name AS Tvrtka, u.username AS Korisnik, receipt.id AS "ID Racuna", receipt.status AS "Status", receipt.storno_date AS "Datum Storniranja", s.username AS "Stornirao" FROM evidencija INNER JOIN proizvod ON evidencija.proizvod_id=proizvod.id INNER JOIN tvrtka ON evidencija.tvrtka_id=tvrtka.id INNER JOIN user u ON evidencija.user_id=u.id INNER JOIN user s ON receipt.storno_user=s.id INNER JOIN receipt ON evidencija.receipt_id=receipt.id WHERE  u.username= "{}" AND evidencija.datum_unosa >= "{}" AND evidencija.datum_unosa <= "{}" AND evidencija.vrsta_unosa="izlaz" AND receipt.status="storno"'.format(u, b, e))
	else:
		if u== " ":
			if b==" " and e==" ":
				sql= text('SELECT evidencija.datum_unosa AS "Datum Izdavanja", evidencija.promijenjena_kolicina AS "Promijenjena Kolicina", proizvod.name AS Proizvod, proizvod.id AS "ID Proizvoda", tvrtka.name AS Tvrtka, u.username AS Korisnik, receipt.id AS "ID Racuna", receipt.status AS "Status", receipt.storno_date AS "Datum Storniranja", s.username AS "Stornirao" FROM evidencija INNER JOIN proizvod ON evidencija.proizvod_id=proizvod.id INNER JOIN tvrtka ON evidencija.tvrtka_id=tvrtka.id INNER JOIN user u ON evidencija.user_id=u.id INNER JOIN user s ON receipt.storno_user=s.id INNER JOIN receipt ON evidencija.receipt_id=receipt.id WHERE  proizvod.name= "{}" AND evidencija.vrsta_unosa="izlaz" AND receipt.status="storno"'.format(s))
			elif b==" ":
				sql= text('SELECT evidencija.datum_unosa AS "Datum Izdavanja", evidencija.promijenjena_kolicina AS "Promijenjena Kolicina", proizvod.name AS Proizvod, proizvod.id AS "ID Proizvoda", tvrtka.name AS Tvrtka, u.username AS Korisnik, receipt.id AS "ID Racuna", receipt.status AS "Status", receipt.storno_date AS "Datum Storniranja", s.username AS "Stornirao" FROM evidencija INNER JOIN proizvod ON evidencija.proizvod_id=proizvod.id INNER JOIN tvrtka ON evidencija.tvrtka_id=tvrtka.id INNER JOIN user u ON evidencija.user_id=u.id INNER JOIN user s ON receipt.storno_user=s.id INNER JOIN receipt ON evidencija.receipt_id=receipt.id WHERE  proizvod.name= "{}" AND evidencija.datum_unosa <= "{}" AND evidencija.vrsta_unosa="izlaz" AND receipt.status="storno"'.format(s, e))
			elif e==" ":
				sql= text('SELECT evidencija.datum_unosa AS "Datum Izdavanja", evidencija.promijenjena_kolicina AS "Promijenjena Kolicina", proizvod.name AS Proizvod, proizvod.id AS "ID Proizvoda", tvrtka.name AS Tvrtka, u.username AS Korisnik, receipt.id AS "ID Racuna", receipt.status AS "Status", receipt.storno_date AS "Datum Storniranja", s.username AS "Stornirao" FROM evidencija INNER JOIN proizvod ON evidencija.proizvod_id=proizvod.id INNER JOIN tvrtka ON evidencija.tvrtka_id=tvrtka.id INNER JOIN user u ON evidencija.user_id=u.id INNER JOIN user s ON receipt.storno_user=s.id INNER JOIN receipt ON evidencija.receipt_id=receipt.id WHERE  proizvod.name= "{}" AND evidencija.datum_unosa >= "{}" AND evidencija.vrsta_unosa="izlaz" AND receipt.status="storno"'.format(s, b))
			else:
				sql= text('SELECT evidencija.datum_unosa AS "Datum Izdavanja", evidencija.promijenjena_kolicina AS "Promijenjena Kolicina", proizvod.name AS Proizvod, proizvod.id AS "ID Proizvoda", tvrtka.name AS Tvrtka, u.username AS Korisnik, receipt.id AS "ID Racuna", receipt.status AS "Status", receipt.storno_date AS "Datum Storniranja", s.username AS "Stornirao" FROM evidencija INNER JOIN proizvod ON evidencija.proizvod_id=proizvod.id INNER JOIN tvrtka ON evidencija.tvrtka_id=tvrtka.id INNER JOIN user u ON evidencija.user_id=u.id INNER JOIN user s ON receipt.storno_user=s.id INNER JOIN receipt ON evidencija.receipt_id=receipt.id WHERE  proizvod.name= "{}" AND evidencija.datum_unosa >= "{}" AND evidencija.datum_unosa <= "{}" AND evidencija.vrsta_unosa="izlaz" AND receipt.status="storno"'.format(s, b, e))
		else:
			if b==" " and e==" ":
				sql= text('SELECT evidencija.datum_unosa AS "Datum Izdavanja", evidencija.promijenjena_kolicina AS "Promijenjena Kolicina", proizvod.name AS Proizvod, proizvod.id AS "ID Proizvoda", tvrtka.name AS Tvrtka, u.username AS Korisnik, receipt.id AS "ID Racuna", receipt.status AS "Status", receipt.storno_date AS "Datum Storniranja", s.username AS "Stornirao" FROM evidencija INNER JOIN proizvod ON evidencija.proizvod_id=proizvod.id INNER JOIN tvrtka ON evidencija.tvrtka_id=tvrtka.id INNER JOIN user u ON evidencija.user_id=u.id INNER JOIN user s ON receipt.storno_user=s.id INNER JOIN receipt ON evidencija.receipt_id=receipt.id WHERE  proizvod.name= "{}" AND u.username= "{}" AND evidencija.vrsta_unosa="izlaz" AND receipt.status="storno"'.format(s, u))
			elif b==" ":
				sql= text('SELECT evidencija.datum_unosa AS "Datum Izdavanja", evidencija.promijenjena_kolicina AS "Promijenjena Kolicina", proizvod.name AS Proizvod, proizvod.id AS "ID Proizvoda", tvrtka.name AS Tvrtka, u.username AS Korisnik, receipt.id AS "ID Racuna", receipt.status AS "Status", receipt.storno_date AS "Datum Storniranja", s.username AS "Stornirao" FROM evidencija INNER JOIN proizvod ON evidencija.proizvod_id=proizvod.id INNER JOIN tvrtka ON evidencija.tvrtka_id=tvrtka.id INNER JOIN user u ON evidencija.user_id=u.id INNER JOIN user s ON receipt.storno_user=s.id INNER JOIN receipt ON evidencija.receipt_id=receipt.id WHERE  proizvod.name= "{}" AND u.username= "{}" AND evidencija.datum_unosa <= "{}" AND evidencija.vrsta_unosa="izlaz" AND receipt.status="storno"'.format(s, u, e))
			elif e==" ":
				sql= text('SELECT evidencija.datum_unosa AS "Datum Izdavanja", evidencija.promijenjena_kolicina AS "Promijenjena Kolicina", proizvod.name AS Proizvod, proizvod.id AS "ID Proizvoda", tvrtka.name AS Tvrtka, u.username AS Korisnik, receipt.id AS "ID Racuna", receipt.status AS "Status", receipt.storno_date AS "Datum Storniranja", s.username AS "Stornirao" FROM evidencija INNER JOIN proizvod ON evidencija.proizvod_id=proizvod.id INNER JOIN tvrtka ON evidencija.tvrtka_id=tvrtka.id INNER JOIN user u ON evidencija.user_id=u.id INNER JOIN user s ON receipt.storno_user=s.id INNER JOIN receipt ON evidencija.receipt_id=receipt.id WHERE  proizvod.name= "{}" AND u.username= "{}" AND evidencija.datum_unosa >= "{}" AND evidencija.vrsta_unosa="izlaz" AND receipt.status="storno"'.format(s, u, b))				
			else:
				sql= text('SELECT evidencija.datum_unosa AS "Datum Izdavanja", evidencija.promijenjena_kolicina AS "Promijenjena Kolicina", proizvod.name AS Proizvod, proizvod.id AS "ID Proizvoda", tvrtka.name AS Tvrtka, u.username AS Korisnik, receipt.id AS "ID Racuna", receipt.status AS "Status", receipt.storno_date AS "Datum Storniranja", s.username AS "Stornirao" FROM evidencija INNER JOIN proizvod ON evidencija.proizvod_id=proizvod.id INNER JOIN tvrtka ON evidencija.tvrtka_id=tvrtka.id INNER JOIN user u ON evidencija.user_id=u.id INNER JOIN user s ON receipt.storno_user=s.id INNER JOIN receipt ON evidencija.receipt_id=receipt.id WHERE  proizvod.name= "{}" AND u.username= "{}" AND evidencija.datum_unosa >= "{}" AND evidencija.datum_unosa <= "{}" AND evidencija.vrsta_unosa="izlaz" AND receipt.status="storno"'.format(s, u, b, e))

	result= db.engine.execute(sql)
	query_sets = []
	for r in result:
		query_sets.append(r)
	column_names = [
		'Datum Izdavanja',
		'Promijenjena Kolicina',
		'Proizvod',
		'ID Proizvoda',
		'Tvrtka',
		'Korisnik',
		'ID Racuna',
		'Datum Storniranja',
		'Stornirao'
		]
	return excel.make_response_from_query_sets(query_sets, column_names, 'xls', file_name="Izlazna evidencija storno "+ "proizvoda "+s+" od "+b+" do "+e+" korisnik "+u)

@app.route('/export_receipt_unos/<id>')
@login_required
def export_receipt_unos(id):
	receipt= Receipt.query.get(id)
	if receipt.status == 'active':
		sql= text('SELECT evidencija.datum_unosa AS "Datum Unosa", evidencija.promijenjena_kolicina AS "Promijenjena Kolicina", proizvod.name AS Proizvod, proizvod.id AS "ID Proizvoda", tvrtka.name AS Tvrtka, user.username AS Korisnik FROM evidencija INNER JOIN proizvod ON evidencija.proizvod_id=proizvod.id INNER JOIN tvrtka ON evidencija.tvrtka_id=tvrtka.id INNER JOIN user ON evidencija.user_id=user.id WHERE evidencija.receipt_id = "{}"'.format(id))
		result= db.engine.execute(sql)
		query_sets = []
		for r in result:
			query_sets.append(r)
		column_names = [
			'Datum Unosa',
			'Promijenjena Kolicina',
			'Proizvod',
			'ID Proizvoda',
			'Tvrtka',
			'Korisnik'
			]
		return excel.make_response_from_query_sets(query_sets, column_names, 'xls', file_name="Ulazni racun "+str(id))
	else:
		sql= text('SELECT evidencija.datum_unosa AS "Datum Unosa", evidencija.promijenjena_kolicina AS "Promijenjena Kolicina", proizvod.name AS Proizvod, proizvod.id AS "ID Proizvoda", tvrtka.name AS Tvrtka, u.username AS Korisnik, receipt.id AS "ID Racuna", receipt.status AS "Status", receipt.storno_date AS "Datum Storniranja", s.username AS "Stornirao" FROM evidencija INNER JOIN proizvod ON evidencija.proizvod_id=proizvod.id INNER JOIN tvrtka ON evidencija.tvrtka_id=tvrtka.id INNER JOIN user u ON evidencija.user_id=u.id INNER JOIN user s ON receipt.storno_user=s.id INNER JOIN receipt ON evidencija.receipt_id=receipt.id WHERE evidencija.receipt_id = "{}"'.format(id))
		result= db.engine.execute(sql)
		query_sets = []
		for r in result:
			query_sets.append(r)
		column_names = [
			'Datum Unosa',
			'Promijenjena Kolicina',
			'Proizvod',
			'ID Proizvoda',
			'Tvrtka',
			'Korisnik',
			'Datum Storniranja',
			'Stornirao'
			]
		return excel.make_response_from_query_sets(query_sets, column_names, 'xls', file_name="Ulazni racun storno "+str(id))

@app.route('/export_receipt_izlaz/<id>')
@login_required
def export_receipt_izlaz(id):
	receipt= Receipt.query.get(id)
	if receipt.status == 'active':
		sql= text('SELECT evidencija.datum_unosa AS "Datum Izdavanja", evidencija.promijenjena_kolicina AS "Promijenjena Kolicina", proizvod.name AS Proizvod, proizvod.id AS "ID Proizvoda", tvrtka.name AS Tvrtka, user.username AS Korisnik FROM evidencija INNER JOIN proizvod ON evidencija.proizvod_id=proizvod.id INNER JOIN tvrtka ON evidencija.tvrtka_id=tvrtka.id INNER JOIN user ON evidencija.user_id=user.id WHERE evidencija.receipt_id = "{}"'.format(id))
		result= db.engine.execute(sql)
		query_sets = []
		for r in result:
			query_sets.append(r)
		column_names = [
			'Datum Izdavanja',
			'Promijenjena Kolicina',
			'Proizvod',
			'ID Proizvoda',
			'Tvrtka',
			'Korisnik'
			]
		return excel.make_response_from_query_sets(query_sets, column_names, 'xls', file_name="Izlazni racun "+str(id))
	else:
		sql= text('SELECT evidencija.datum_unosa AS "Datum Izdavanja", evidencija.promijenjena_kolicina AS "Promijenjena Kolicina", proizvod.name AS Proizvod, proizvod.id AS "ID Proizvoda", tvrtka.name AS Tvrtka, u.username AS Korisnik, receipt.id AS "ID Racuna", receipt.status AS "Status", receipt.storno_date AS "Datum Storniranja", s.username AS "Stornirao" FROM evidencija INNER JOIN proizvod ON evidencija.proizvod_id=proizvod.id INNER JOIN tvrtka ON evidencija.tvrtka_id=tvrtka.id INNER JOIN user u ON evidencija.user_id=u.id INNER JOIN user s ON receipt.storno_user=s.id INNER JOIN receipt ON evidencija.receipt_id=receipt.id WHERE evidencija.receipt_id = "{}"'.format(id))
		result= db.engine.execute(sql)
		query_sets = []
		for r in result:
			query_sets.append(r)
		column_names = [
			'Datum Izdavanja',
			'Promijenjena Kolicina',
			'Proizvod',
			'ID Proizvoda',
			'Tvrtka',
			'Korisnik',
			'Datum Storniranja',
			'Stornirao'
			]
		return excel.make_response_from_query_sets(query_sets, column_names, 'xls', file_name="Izlazni racun storno"+str(id))

@app.route('/ulaz', methods=['GET', 'POST'])
@login_required
def ulaz():
	tvrtke = Tvrtka.query.all()
	form = ListForm()
	lista = []
	lista2 = []
	sve_tvrtke = Tvrtka.query.all() 
	svi_proizvodi = Proizvod.query.all()
	kodovi  = {}
	for proizvod in svi_proizvodi:
		kodovi[str(proizvod.bar_kod)]= proizvod.name
		lista2.append(proizvod.name)
	for tvrtka in sve_tvrtke:
		lista.append(tvrtka.name)
	error=False
	empty=True
	products=[]
	companies=[]
	amounts=[]
	if form.submit.data:
		if form.validate_on_submit():
			productList= json.loads(form.listaProizvoda.data)
			for product in productList:
				if product != None:
					empty=False
			for productData in productList:
				if productData is not None:
					proizvod = Proizvod.query.filter_by(name=productData[0]).first()
					if proizvod is None:
						flash(f'Proizvod '+productData[0]+ ' ne postoji!', 'danger')
						error=True
						#return redirect(url_for('ulaz'))
					tvrtka = Tvrtka.query.filter_by(name=productData[2]).first()
					if tvrtka is None:
						flash(f'Tvrtka '+ productData[2]+' ne postoji!', 'danger')
						error=True
					if (int(productData[1])<1): 
						flash(f'Pogresna kolicina za proizvod '+productData[0]+'!', 'danger')
						error=True
					if error is False:
						if proizvod in products:
							index = products.index(proizvod)
							amounts[index]+=int(productData[1]);
						else:
							products.append(proizvod)
							companies.append(tvrtka)
							amounts.append(int(productData[1]))

			if error is False and empty is False:
				receipt = Receipt(status="active", receipt_type="unos", receipt_user=current_user.id, receipt_tvrtka=companies[0].id)
				db.session.add(receipt)
				db.session.commit()
				for i in range(0, len(products)):
					products[i].kolicina+= amounts[i]
					evidencija = Evidencija(proizvod_id=products[i].id, tvrtka_id=companies[i].id, promijenjena_kolicina=amounts[i], user_id=current_user.id, vrsta_unosa='unos', trenutna_kolicina=products[i].kolicina, receipt_id=receipt.id)
					db.session.add(evidencija)
					db.session.commit()
				return redirect(url_for('receipt', id=receipt.id))
	return render_template("ulaz.html", title='Ulaz', tvrtke=tvrtke, lista=lista, lista2=lista2, form=form, kodovi=kodovi)



@app.route('/izlaz', methods=['GET', 'POST'])
@login_required
def izlaz():
	tvrtke = Tvrtka.query.all()
	form = ListForm()
	lista = []
	lista2 = []
	sve_tvrtke = Tvrtka.query.all() 
	svi_proizvodi = Proizvod.query.all()
	error=False
	empty=True
	products=[]
	companies=[]
	amounts=[]
	kodovi  = {}
	for proizvod in svi_proizvodi:
		kodovi[str(proizvod.bar_kod)]= proizvod.name
		lista2.append(proizvod.name)
	for tvrtka in sve_tvrtke:
		lista.append(tvrtka.name)
	if form.submit.data:
		if form.validate_on_submit():
			productList= json.loads(form.listaProizvoda.data)
			for product in productList:
				if product != None:
					empty=False
			for productData in productList:
				if productData is not None:
					proizvod = Proizvod.query.filter_by(name=productData[0]).first()
					if proizvod is None:
						flash(f'Proizvod '+productData[0]+ ' ne postoji!', 'danger')
						error=True
						#return redirect(url_for('izlaz'))
					tvrtka = Tvrtka.query.filter_by(name=productData[2]).first()
					if tvrtka is None:
						flash(f'Tvrtka '+ productData[2]+' ne postoji!', 'danger')
						error=True
					if (int(productData[1])<1): 
						flash(f'Pogresna kolicina za proizvod '+productData[0]+'!', 'danger')
						error=True
					if proizvod is not None:
						if (int(productData[1])>proizvod.kolicina): 
							flash(f'Nema dovoljno kolicine na stanju za proizvod '+productData[0]+'!', 'danger')
							error=True
					if error is False:
						if proizvod in products:
							index = products.index(proizvod)
							amounts[index]+=int(productData[1]);
							if amounts[index]>proizvod.kolicina:
								error=True
								flash(f'Nema dovoljno kolicine na stanju za proizvod '+productData[0]+'!', 'danger')
						else:
							products.append(proizvod)
							companies.append(tvrtka)
							amounts.append(int(productData[1]))
			if error is False and empty is False:
				receipt = Receipt(status="active", receipt_type="izlaz", receipt_user=current_user.id, receipt_tvrtka=companies[0].id)
				db.session.add(receipt)
				db.session.commit()
				for i in range(0, len(products)):
					products[i].kolicina-= amounts[i]
					evidencija = Evidencija(proizvod_id=products[i].id, tvrtka_id=companies[i].id, promijenjena_kolicina=amounts[i], user_id=current_user.id, vrsta_unosa='izlaz', trenutna_kolicina=products[i].kolicina, receipt_id=receipt.id)
					db.session.add(evidencija)
					db.session.commit()
				return redirect(url_for('receipt', id=receipt.id))
	return render_template("izlaz.html", title='Izlaz', tvrtke=tvrtke, lista=lista, lista2=lista2, form=form, kodovi=kodovi)



@app.route('/receipts_unosa/<int:page_num>+<s>+<b>+<e>+<u>', methods=['GET', 'POST'])
@login_required
def receipts_unosa(page_num, s, b, e, u):
	form = SearchFormReceipt()
	lista = []
	lista2 = []
	sveTvrtke = Tvrtka.query.all()
	for tvrtka in sveTvrtke:
		lista.append(tvrtka.name)
	sviUseri = User.query.all()
	for user in sviUseri:
		lista2.append(user.username)
	if s == ' ':
		if u==' ':
			if b ==' ' and e==' ':
				receipts = Receipt.query.filter( Receipt.receipt_type=='unos', Receipt.status=='active').order_by(Receipt.date.desc()).paginate(per_page=3, page=page_num, error_out=True)
			elif b ==' ':
				receipts = Receipt.query.filter( Receipt.receipt_type=='unos', Receipt.status=='active', Receipt.date <= e).order_by(Receipt.date.desc()).paginate(per_page=3, page=page_num, error_out=True)
			elif e==' ':
				receipts = Receipt.query.filter( Receipt.receipt_type=='unos', Receipt.status=='active', Receipt.date >= b).order_by(Receipt.date.desc()).paginate(per_page=3, page=page_num, error_out=True)
			else:
				receipts = Receipt.query.filter( Receipt.receipt_type=='unos', Receipt.status=='active', Receipt.date >= b, Receipt.date <=e).order_by(Receipt.date.desc()).paginate(per_page=3, page=page_num, error_out=True)
		else:
			user = User.query.filter_by(username=u).first()
			if b ==' ' and e==' ':
				receipts = Receipt.query.filter( Receipt.receipt_type=='unos', Receipt.status=='active', Receipt.receipt_user==user.id).order_by(Receipt.date.desc()).paginate(per_page=3, page=page_num, error_out=True)
			elif b ==' ':
				receipts = Receipt.query.filter( Receipt.receipt_type=='unos', Receipt.status=='active', Receipt.date <= e, Receipt.receipt_user==user.id).order_by(Receipt.date.desc()).paginate(per_page=3, page=page_num, error_out=True)
			elif e==' ':
				receipts = Receipt.query.filter( Receipt.receipt_type=='unos', Receipt.status=='active', Receipt.date >= b, Receipt.receipt_user==user.id).order_by(Receipt.date.desc()).paginate(per_page=3, page=page_num, error_out=True)
			else:
				receipts = Receipt.query.filter( Receipt.receipt_type=='unos', Receipt.status=='active', Receipt.date >= b, Receipt.date <=e, Receipt.receipt_user==user.id).order_by(Receipt.date.desc()).paginate(per_page=3, page=page_num, error_out=True)

	elif not form.submit.data:
		tvrtka=Tvrtka.query.filter(Tvrtka.name.like("%"+s+"%")).first()
		if u == ' ':
			if b ==' ' and e==' ':
				receipts = Receipt.query.filter( Receipt.receipt_tvrtka==tvrtka.id, Receipt.receipt_type=='unos', Receipt.status=='active').order_by(Receipt.date.desc()).paginate(per_page=3, page=page_num, error_out=True)
			elif b ==' ':
				receipts = Receipt.query.filter(Receipt.receipt_tvrtka==tvrtka.id, Receipt.receipt_type=='unos', Receipt.status=='active', Receipt.date <= e).order_by(Receipt.date.desc()).paginate(per_page=3, page=page_num, error_out=True)
			elif e ==' ':
				receipts = Receipt.query.filter(Receipt.receipt_tvrtka==tvrtka.id, Receipt.receipt_type=='unos', Receipt.status=='active', Receipt.date >= b).order_by(Receipt.date.desc()).paginate(per_page=3, page=page_num, error_out=True)
			else:
				receipts = Receipt.query.filter(Receipt.receipt_tvrtka==tvrtka.id, Receipt.receipt_type=='unos', Receipt.status=='active', Receipt.date >= b, Receipt.date <= e).order_by(Receipt.date.desc()).paginate(per_page=3, page=page_num, error_out=True)
			return render_template('receipts_unosa.html', title='Primke', form=form, receipts=receipts, search=s, begin=b, end=e, user=u, lista=lista, lista2=lista2)
		else:
			user = User.query.filter_by(username=u).first()
			if b ==' ' and e==' ':
				receipts = Receipt.query.filter( Receipt.receipt_tvrtka==tvrtka.id, Receipt.receipt_type=='unos', Receipt.status=='active', Receipt.receipt_user==user.id).order_by(Receipt.date.desc()).paginate(per_page=3, page=page_num, error_out=True)
			elif b ==' ':
				receipts = Receipt.query.filter(Receipt.receipt_tvrtka==tvrtka.id, Receipt.receipt_type=='unos', Receipt.status=='active', Receipt.date <= e, Receipt.receipt_user==user.id).order_by(Receipt.date.desc()).paginate(per_page=3, page=page_num, error_out=True)
			elif e ==' ':
				receipts = Receipt.query.filter(Receipt.receipt_tvrtka==tvrtka.id, Receipt.receipt_type=='unos', Receipt.status=='active', Receipt.date >= b, Receipt.receipt_user==user.id).order_by(Receipt.date.desc()).paginate(per_page=3, page=page_num, error_out=True)
			else:
				receipts = Receipt.query.filter(Receipt.receipt_tvrtka==tvrtka.id, Receipt.receipt_type=='unos', Receipt.status=='active', Receipt.date >= b, Receipt.date <= e, Receipt.receipt_user==user.id).order_by(Receipt.date.desc()).paginate(per_page=3, page=page_num, error_out=True)
			return render_template('receipts_unosa.html', title='Primke', form=form, receipts=receipts, search=s, begin=b, end=e, user=u, lista=lista, lista2=lista2)
	if form.submit.data:
		#import pdb; pdb.set_trace();
		if form.validate_on_submit():
			number = form.search.data
			if number.isdigit():
				receipts= Receipt.query.filter_by(id =number, status='active', receipt_type='unos').paginate(per_page=3, page=1, error_out=True)
				return render_template('receipts_unosa.html', title='Primke', form=form, receipts=receipts, search=" ", begin=" ", end=" ", user=" ", lista=lista, lista2=lista2)
			tvrtka = Tvrtka.query.filter(Tvrtka.name.like("%" + form.search.data + "%")).first()
			if form.search.data != "" and form.search.data != " " and tvrtka is None:
				flash(f'Tvrtka '+form.search.data+ ' ne postoji!', 'danger')
				return redirect(url_for('receipts_unosa1'))
				import pdb; pdb.set_trace();
			user = User.query.filter_by(username=form.user.data).first()
			if form.user.data != "" and form.user.data != " " and user is None:
				flash(f'Korisnik '+form.user.data+ ' ne postoji!', 'danger')
				return redirect(url_for('receipts_unosa1'))
			if user is None:
				form.user.data=" "
				if form.begin.data is None and form.end.data is None:
					if form.search.data == "" or form.search.data == " ":
						receipts = Receipt.query.filter(Receipt.receipt_type=='unos').order_by(Receipt.date.desc()).paginate(per_page=3, page=1, error_out=True)
						form.search.data= " "
					else:
						receipts = Receipt.query.filter(Receipt.receipt_tvrtka==tvrtka.id, Receipt.receipt_type=='unos', Receipt.status=='active').order_by(Receipt.date.desc()).paginate(per_page=3, page=1, error_out=True)
					form.begin.data = ' '
					form.end.data = ' '
					form.user.data=' '
				elif form.begin.data is None:
					if form.search.data == "" or form.search.data == " ":
						receipts = Receipt.query.filter(Receipt.receipt_type=='unos', Receipt.status=='active', Receipt.date <= form.end.data).order_by(Receipt.date.desc()).paginate(per_page=3, page=1, error_out=True)
						form.search.data= " "
					else:
						receipts = Receipt.query.filter(Receipt.receipt_tvrtka==tvrtka.id, Receipt.receipt_type=='unos', Receipt.status=='active', Receipt.date <= form.end.data).order_by(Receipt.date.desc()).paginate(per_page=3, page=1, error_out=True)
					form.begin.data = ' '
					form.user.data=' '
				elif form.end.data is None:
					if form.search.data == "" or form.search.data == " ":
						receipts = Receipt.query.filter(Receipt.receipt_type=='unos', Receipt.status=='active', Receipt.date >= form.begin.data).order_by(Receipt.date.desc()).paginate(per_page=3, page=1, error_out=True)
						form.search.data= " "
					else:
						receipts = Receipt.query.filter(Receipt.receipt_tvrtka==tvrtka.id, Receipt.receipt_type=='unos', Receipt.status=='active', Receipt.date >= form.begin.data).order_by(Receipt.date.desc()).paginate(per_page=3, page=1, error_out=True)
					form.end.data = ' '
					form.user.data=' '
				else:
					form.user.data=' '
					if form.search.data == "" or form.search.data == " ":
						receipts = Receipt.query.filter(Receipt.receipt_type=='unos', Receipt.status=='active', Receipt.date >= form.begin.data, Receipt.date <= form.end.data).order_by(Receipt.date.desc()).paginate(per_page=3, page=1, error_out=True)
						form.search.data= " "
					else:
						receipts = Receipt.query.filter(Receipt.receipt_tvrtka==tvrtka.id, Receipt.receipt_type=='unos', Receipt.status=='active', Receipt.date >= form.begin.data, Receipt.date <= form.end.data).order_by(Receipt.date.desc()).paginate(per_page=3, page=1, error_out=True)	
			else:
				#import pdb; pdb.set_trace();
				user = User.query.filter_by(username=form.user.data).first()
				if form.begin.data is None and form.end.data is None:
					if form.search.data == "" or form.search.data == " ":
						receipts = Receipt.query.filter( Receipt.receipt_type=='unos', Receipt.status=='active', Receipt.receipt_user==user.id).order_by(Receipt.date.desc()).paginate(per_page=3, page=1, error_out=True)
						#import pdb; pdb.set_trace();
						form.search.data= " "
					else:
						receipts = Receipt.query.filter(Receipt.receipt_tvrtka==tvrtka.id, Receipt.receipt_type=='unos', Receipt.status=='active', Receipt.receipt_user==user.id).order_by(Receipt.date.desc()).paginate(per_page=3, page=1, error_out=True)
					form.begin.data = ' '
					form.end.data = ' '
				elif form.begin.data is None:
					if form.search.data == "" or form.search.data == " ":
						receipts = Receipt.query.filter(Receipt.receipt_type=='unos', Receipt.status=='active', Receipt.date <= form.end.data, Receipt.receipt_user==user.id).order_by(Receipt.date.desc()).paginate(per_page=3, page=1, error_out=True)
						form.search.data= " "
					else:
						receipts = Receipt.query.filter(Receipt.receipt_tvrtka==tvrtka.id, Receipt.receipt_type=='unos', Receipt.status=='active', Receipt.date <= form.end.data, Receipt.receipt_user==user.id).order_by(Receipt.date.desc()).paginate(per_page=3, page=1, error_out=True)
					form.begin.data = ' '
				elif form.end.data is None:
					if form.search.data == "" or form.search.data == " ":
						receipts = Receipt.query.filter(Receipt.receipt_type=='unos', Receipt.status=='active', Receipt.date >= form.begin.data, Receipt.receipt_user==user.id).order_by(Receipt.date.desc()).paginate(per_page=3, page=1, error_out=True)
						form.search.data= " "
					else:
						receipts = Receipt.query.filter(Receipt.receipt_tvrtka==tvrtka.id, Receipt.receipt_type=='unos', Receipt.status=='active', Receipt.date >= form.begin.data, Receipt.receipt_user==user.id).order_by(Receipt.date.desc()).paginate(per_page=3, page=1, error_out=True)
					form.end.data = ' '
				else:
					if form.search.data == "" or form.search.data == " ":
						receipts = Receipt.query.filter(Receipt.receipt_type=='unos', Receipt.status=='active', Receipt.date >= form.begin.data, Receipt.date <= form.end.data, Receipt.receipt_user==user.id).order_by(Receipt.date.desc()).paginate(per_page=3, page=1, error_out=True)
						form.search.data= " "
					else:
						receipts = Receipt.query.filter(Receipt.receipt_tvrtka==tvrtka.id, Receipt.receipt_type=='unos', Receipt.status=='active', Receipt.date >= form.begin.data, Receipt.date <= form.end.data, Receipt.receipt_user==user.id).order_by(Receipt.date.desc()).paginate(per_page=3, page=1, error_out=True)
			return render_template('receipts_unosa.html', title='Primke', form=form, receipts=receipts, search=form.search.data, begin=form.begin.data, end=form.end.data, lista=lista, lista2=lista2, user=form.user.data, page=1)
		return redirect(url_for('receipts_unosa1'))
	return render_template('receipts_unosa.html', title='Primke', form=form, receipts=receipts, search=s, begin=b, end=e, user=u, lista=lista, lista2=lista2)

@app.route('/receipts_unosa1', methods=['GET', 'POST'])
@login_required
def receipts_unosa1():
	return redirect(url_for('receipts_unosa', page_num=1, s=" ", b=" ", e=" ", u=" "))


@app.route('/receipts_izlaz/<int:page_num>+<s>+<b>+<e>+<u>', methods=['GET', 'POST'])
@login_required
def receipts_izlaz(page_num, s, b, e, u):
	form = SearchFormReceipt()
	#receipts = Receipt.query.filter_by(receipt_type="izlaz", status="active").order_by(Receipt.date.desc()).paginate(per_page=7, page=page_num, error_out=True)
	lista = []
	lista2 = []
	sveTvrtke = Tvrtka.query.all()
	for tvrtka in sveTvrtke:
		lista.append(tvrtka.name)
	sviUseri = User.query.all()
	for user in sviUseri:
		lista2.append(user.username)
	if s == ' ':
		if u==' ':
			if b ==' ' and e==' ':
				receipts = Receipt.query.filter( Receipt.receipt_type=='izlaz', Receipt.status=='active').order_by(Receipt.date.desc()).paginate(per_page=3, page=page_num, error_out=True)
			elif b ==' ':
				receipts = Receipt.query.filter( Receipt.receipt_type=='izlaz', Receipt.status=='active', Receipt.date <= e).order_by(Receipt.date.desc()).paginate(per_page=3, page=page_num, error_out=True)
			elif e==' ':
				receipts = Receipt.query.filter( Receipt.receipt_type=='izlaz', Receipt.status=='active', Receipt.date >= b).order_by(Receipt.date.desc()).paginate(per_page=3, page=page_num, error_out=True)
			else:
				receipts = Receipt.query.filter( Receipt.receipt_type=='izlaz', Receipt.status=='active', Receipt.date >= b, Receipt.date <=e).order_by(Receipt.date.desc()).paginate(per_page=3, page=page_num, error_out=True)
		else:
			user = User.query.filter_by(username=u).first()
			if b ==' ' and e==' ':
				receipts = Receipt.query.filter( Receipt.receipt_type=='izlaz', Receipt.status=='active', Receipt.receipt_user==user.id).order_by(Receipt.date.desc()).paginate(per_page=3, page=page_num, error_out=True)
			elif b ==' ':
				receipts = Receipt.query.filter( Receipt.receipt_type=='izlaz', Receipt.status=='active', Receipt.date <= e, Receipt.receipt_user==user.id).order_by(Receipt.date.desc()).paginate(per_page=3, page=page_num, error_out=True)
			elif e==' ':
				receipts = Receipt.query.filter( Receipt.receipt_type=='izlaz', Receipt.status=='active', Receipt.date >= b, Receipt.receipt_user==user.id).order_by(Receipt.date.desc()).paginate(per_page=3, page=page_num, error_out=True)
			else:
				receipts = Receipt.query.filter( Receipt.receipt_type=='izlaz', Receipt.status=='active', Receipt.date >= b, Receipt.date <=e, Receipt.receipt_user==user.id).order_by(Receipt.date.desc()).paginate(per_page=3, page=page_num, error_out=True)

	elif not form.submit.data:
		tvrtka=Tvrtka.query.filter(Tvrtka.name.like("%"+s+"%")).first()
		if u == ' ':
			if b ==' ' and e==' ':
				receipts = Receipt.query.filter( Receipt.receipt_tvrtka==tvrtka.id, Receipt.receipt_type=='izlaz', Receipt.status=='active').order_by(Receipt.date.desc()).paginate(per_page=3, page=page_num, error_out=True)
			elif b ==' ':
				receipts = Receipt.query.filter(Receipt.receipt_tvrtka==tvrtka.id, Receipt.receipt_type=='izlaz', Receipt.status=='active', Receipt.date <= e).order_by(Receipt.date.desc()).paginate(per_page=3, page=page_num, error_out=True)
			elif e ==' ':
				receipts = Receipt.query.filter(Receipt.receipt_tvrtka==tvrtka.id, Receipt.receipt_type=='izlaz', Receipt.status=='active', Receipt.date >= b).order_by(Receipt.date.desc()).paginate(per_page=3, page=page_num, error_out=True)
			else:
				receipts = Receipt.query.filter(Receipt.receipt_tvrtka==tvrtka.id, Receipt.receipt_type=='izlaz', Receipt.status=='active', Receipt.date >= b, Receipt.date <= e).order_by(Receipt.date.desc()).paginate(per_page=3, page=page_num, error_out=True)
			return render_template('receipts_izlaz.html', title='Otpremnice', form=form, receipts=receipts, search=s, begin=b, end=e, user=u, lista=lista, lista2=lista2)
		else:
			user = User.query.filter_by(username=u).first()
			if b ==' ' and e==' ':
				receipts = Receipt.query.filter( Receipt.receipt_tvrtka==tvrtka.id, Receipt.receipt_type=='izlaz', Receipt.status=='active', Receipt.receipt_user==user.id).order_by(Receipt.date.desc()).paginate(per_page=3, page=page_num, error_out=True)
			elif b ==' ':
				receipts = Receipt.query.filter(Receipt.receipt_tvrtka==tvrtka.id, Receipt.receipt_type=='izlaz', Receipt.status=='active', Receipt.date <= e, Receipt.receipt_user==user.id).order_by(Receipt.date.desc()).paginate(per_page=3, page=page_num, error_out=True)
			elif e ==' ':
				receipts = Receipt.query.filter(Receipt.receipt_tvrtka==tvrtka.id, Receipt.receipt_type=='izlaz', Receipt.status=='active', Receipt.date >= b, Receipt.receipt_user==user.id).order_by(Receipt.date.desc()).paginate(per_page=3, page=page_num, error_out=True)
			else:
				receipts = Receipt.query.filter(Receipt.receipt_tvrtka==tvrtka.id, Receipt.receipt_type=='izlaz', Receipt.status=='active', Receipt.date >= b, Receipt.date <= e, Receipt.receipt_user==user.id).order_by(Receipt.date.desc()).paginate(per_page=3, page=page_num, error_out=True)
			return render_template('receipts_izlaz.html', title='Otpremnice', form=form, receipts=receipts, search=s, begin=b, end=e, user=u, lista=lista, lista2=lista2)
	if form.submit.data:
		#import pdb; pdb.set_trace();
		if form.validate_on_submit():
			number = form.search.data
			if number.isdigit():
				receipts= Receipt.query.filter_by(id =number, status='active', receipt_type='izlaz').paginate(per_page=3, page=1, error_out=True)
				return render_template('receipts_izlaz.html', title='Otpremnice', form=form, receipts=receipts, search=" ", begin=" ", end=" ", user=" ", lista=lista, lista2=lista2)
			tvrtka = Tvrtka.query.filter(Tvrtka.name.like("%" + form.search.data + "%")).first()
			if form.search.data != "" and form.search.data != " " and tvrtka is None:
				flash(f'Tvrtka '+form.search.data+ ' ne postoji!', 'danger')
				return redirect(url_for('receipts_izlaz1'))
				import pdb; pdb.set_trace();
			user = User.query.filter_by(username=form.user.data).first()
			if form.user.data != "" and form.user.data != " " and user is None:
				flash(f'Korisnik '+form.user.data+ ' ne postoji!', 'danger')
				return redirect(url_for('receipts_izlaz1'))
			if user is None:
				form.user.data=" "
				if form.begin.data is None and form.end.data is None:
					if form.search.data == "" or form.search.data == " ":
						receipts = Receipt.query.filter(Receipt.receipt_type=='izlaz', Receipt.status=='storno').order_by(Receipt.date.desc()).paginate(per_page=3, page=1, error_out=True)
						form.search.data= " "
					else:
						receipts = Receipt.query.filter(Receipt.receipt_tvrtka==tvrtka.id, Receipt.receipt_type=='izlaz', Receipt.status=='active').order_by(Receipt.date.desc()).paginate(per_page=3, page=1, error_out=True)
					form.begin.data = ' '
					form.end.data = ' '
					form.user.data=' '
					#import pdb; pdb.set_trace();
				elif form.begin.data is None:
					if form.search.data == "" or form.search.data == " ":
						receipts = Receipt.query.filter(Receipt.receipt_type=='izlaz', Receipt.status=='active', Receipt.date <= form.end.data).order_by(Receipt.date.desc()).paginate(per_page=3, page=1, error_out=True)
						form.search.data= " "
					else:
						receipts = Receipt.query.filter(Receipt.receipt_tvrtka==tvrtka.id, Receipt.receipt_type=='izlaz', Receipt.status=='active', Receipt.date <= form.end.data).order_by(Receipt.date.desc()).paginate(per_page=3, page=1, error_out=True)
					form.begin.data = ' '
					form.user.data=' '
				elif form.end.data is None:
					if form.search.data == "" or form.search.data == " ":
						receipts = Receipt.query.filter(Receipt.receipt_type=='izlaz', Receipt.status=='active', Receipt.date >= form.begin.data).order_by(Receipt.date.desc()).paginate(per_page=3, page=1, error_out=True)
						form.search.data= " "
					else:
						receipts = Receipt.query.filter(Receipt.receipt_tvrtka==tvrtka.id, Receipt.receipt_type=='izlaz', Receipt.status=='active', Receipt.date >= form.begin.data).order_by(Receipt.date.desc()).paginate(per_page=3, page=1, error_out=True)
					form.end.data = ' '
					form.user.data=' '
				else:
					form.user.data=' '
					if form.search.data == "" or form.search.data == " ":
						receipts = Receipt.query.filter(Receipt.receipt_type=='izlaz', Receipt.status=='active', Receipt.date >= form.begin.data, Receipt.date <= form.end.data).order_by(Receipt.date.desc()).paginate(per_page=3, page=1, error_out=True)
						form.search.data= " "
					else:
						receipts = Receipt.query.filter(Receipt.receipt_tvrtka==tvrtka.id, Receipt.receipt_type=='izlaz', Receipt.status=='active', Receipt.date >= form.begin.data, Receipt.date <= form.end.data).order_by(Receipt.date.desc()).paginate(per_page=3, page=1, error_out=True)	
			else:
				#import pdb; pdb.set_trace();
				user = User.query.filter_by(username=form.user.data).first()
				if form.begin.data is None and form.end.data is None:
					if form.search.data == "" or form.search.data == " ":
						receipts = Receipt.query.filter( Receipt.receipt_type=='izlaz', Receipt.status=='active', Receipt.receipt_user==user.id).order_by(Receipt.date.desc()).paginate(per_page=3, page=1, error_out=True)
						#import pdb; pdb.set_trace();
						form.search.data= " "
					else:
						receipts = Receipt.query.filter(Receipt.receipt_tvrtka==tvrtka.id, Receipt.receipt_type=='izlaz', Receipt.status=='active', Receipt.receipt_user==user.id).order_by(Receipt.date.desc()).paginate(per_page=3, page=1, error_out=True)
					form.begin.data = ' '
					form.end.data = ' '
				elif form.begin.data is None:
					if form.search.data == "" or form.search.data == " ":
						receipts = Receipt.query.filter(Receipt.receipt_type=='izlaz', Receipt.status=='active', Receipt.date <= form.end.data, Receipt.receipt_user==user.id).order_by(Receipt.date.desc()).paginate(per_page=3, page=1, error_out=True)
						form.search.data= " "
					else:
						receipts = Receipt.query.filter(Receipt.receipt_tvrtka==tvrtka.id, Receipt.receipt_type=='izlaz', Receipt.status=='active', Receipt.date <= form.end.data, Receipt.receipt_user==user.id).order_by(Receipt.date.desc()).paginate(per_page=3, page=1, error_out=True)
					form.begin.data = ' '
				elif form.end.data is None:
					if form.search.data == "" or form.search.data == " ":
						receipts = Receipt.query.filter(Receipt.receipt_type=='izlaz', Receipt.status=='active', Receipt.date >= form.begin.data, Receipt.receipt_user==user.id).order_by(Receipt.date.desc()).paginate(per_page=3, page=1, error_out=True)
						form.search.data= " "
					else:
						receipts = Receipt.query.filter(Receipt.receipt_tvrtka==tvrtka.id, Receipt.receipt_type=='izlaz', Receipt.status=='active', Receipt.date >= form.begin.data, Receipt.receipt_user==user.id).order_by(Receipt.date.desc()).paginate(per_page=3, page=1, error_out=True)
					form.end.data = ' '
				else:
					if form.search.data == "" or form.search.data == " ":
						receipts = Receipt.query.filter(Receipt.receipt_type=='izlaz', Receipt.status=='active', Receipt.date >= form.begin.data, Receipt.date <= form.end.data, Receipt.receipt_user==user.id).order_by(Receipt.date.desc()).paginate(per_page=3, page=1, error_out=True)
						form.search.data= " "
					else:
						receipts = Receipt.query.filter(Receipt.receipt_tvrtka==tvrtka.id, Receipt.receipt_type=='izlaz', Receipt.status=='active', Receipt.date >= form.begin.data, Receipt.date <= form.end.data, Receipt.receipt_user==user.id).order_by(Receipt.date.desc()).paginate(per_page=3, page=1, error_out=True)
			return render_template('receipts_izlaz.html', title='Otpremnice', form=form, receipts=receipts, search=form.search.data, begin=form.begin.data, end=form.end.data, lista=lista, lista2=lista2, user=form.user.data, page=1)
		return redirect(url_for('receipts_izlaz1'))
	return render_template('receipts_izlaz.html', title='Otpremnice', form=form, receipts=receipts, search=s, begin=b, end=e, user=u, lista=lista, lista2=lista2)

@app.route('/receipts_izlaz1', methods=['GET', 'POST'])
@login_required
def receipts_izlaz1():
	return redirect(url_for('receipts_izlaz', page_num=1, s=" ", b=" ", e=" ", u=" "))

@app.route('/receipts_unosa_storno/<int:page_num>+<s>+<b>+<e>+<u>+<st>', methods=['GET', 'POST'])
@login_required
def receipts_unosa_storno(page_num, s, b, e, u, st):
	form = SearchFormReceiptStorno()
	lista = []
	lista2 = []
	sveTvrtke = Tvrtka.query.all()
	for tvrtka in sveTvrtke:
		lista.append(tvrtka.name)
	sviUseri = User.query.all()
	for user in sviUseri:
		lista2.append(user.username)
	if form.submit.data:
		if form.validate_on_submit():
			
			number = form.search.data
			if number.isdigit():
				receipts= Receipt.query.filter_by(id =number, status='storno', receipt_type='unos').paginate(per_page=3, page=1, error_out=True)
				return render_template('receipts_unosa_storno.html', title='Stornirane Primke', form=form, receipts=receipts, search=" ", begin=" ", end=" ", user=" ", lista=lista, lista2=lista2)
			tvrtka = Tvrtka.query.filter(Tvrtka.name.like("%" + form.search.data + "%")).first()
			if form.search.data != "" and form.search.data != " " and tvrtka is None:
				flash(f'Tvrtka '+form.search.data+ ' ne postoji!', 'danger')
				return redirect(url_for('receipts_unosa_storno1'))
				#import pdb; pdb.set_trace();
			user = User.query.filter_by(username=form.user.data).first()
			if form.user.data != "" and form.user.data != " " and user is None:
				flash(f'Korisnik '+form.user.data+ ' ne postoji!', 'danger')
				return redirect(url_for('receipts_unosa_storno1'))
			#import pdb; pdb.set_trace();
			if form.storno.data=="aktivni":
				if user is None:
					form.user.data=" "
					if form.begin.data is None and form.end.data is None:
						if form.search.data == "" or form.search.data == " ":
							receipts = Receipt.query.filter(Receipt.receipt_type=='unos', Receipt.status=='storno').order_by(Receipt.date.desc()).paginate(per_page=3, page=1, error_out=True)
							form.search.data= " "
						else:
							receipts = Receipt.query.filter(Receipt.receipt_tvrtka==tvrtka.id, Receipt.receipt_type=='unos', Receipt.status=='storno').order_by(Receipt.date.desc()).paginate(per_page=3, page=1, error_out=True)
						form.begin.data = ' '
						form.end.data = ' '
						form.user.data=' '
					elif form.begin.data is None:
						if form.search.data == "" or form.search.data == " ":
							receipts = Receipt.query.filter(Receipt.receipt_type=='unos', Receipt.status=='storno', Receipt.date <= form.end.data).order_by(Receipt.date.desc()).paginate(per_page=3, page=1, error_out=True)
							form.search.data= " "
						else:
							receipts = Receipt.query.filter(Receipt.receipt_tvrtka==tvrtka.id, Receipt.receipt_type=='unos', Receipt.status=='storno', Receipt.date <= form.end.data).order_by(Receipt.date.desc()).paginate(per_page=3, page=1, error_out=True)
						form.begin.data = ' '
						form.user.data=' '
					elif form.end.data is None:
						if form.search.data == "" or form.search.data == " ":
							receipts = Receipt.query.filter(Receipt.receipt_type=='unos', Receipt.status=='storno', Receipt.date >= form.begin.data).order_by(Receipt.date.desc()).paginate(per_page=3, page=1, error_out=True)
							form.search.data= " "
						else:
							receipts = Receipt.query.filter(Receipt.receipt_tvrtka==tvrtka.id, Receipt.receipt_type=='unos', Receipt.status=='storno', Receipt.date >= form.begin.data).order_by(Receipt.date.desc()).paginate(per_page=3, page=1, error_out=True)
						form.end.data = ' '
						form.user.data=' '
					else:
						form.user.data=' '
						if form.search.data == "" or form.search.data == " ":
							receipts = Receipt.query.filter(Receipt.receipt_type=='unos', Receipt.status=='storno', Receipt.date >= form.begin.data, Receipt.date <= form.end.data).order_by(Receipt.date.desc()).paginate(per_page=3, page=1, error_out=True)
							form.search.data= " "
						else:
							receipts = Receipt.query.filter(Receipt.receipt_tvrtka==tvrtka.id, Receipt.receipt_type=='unos', Receipt.status=='storno', Receipt.date >= form.begin.data, Receipt.date <= form.end.data).order_by(Receipt.date.desc()).paginate(per_page=3, page=1, error_out=True)	
				else:
					#import pdb; pdb.set_trace();
					user = User.query.filter_by(username=form.user.data).first()
					if form.begin.data is None and form.end.data is None:
						if form.search.data == "" or form.search.data == " ":
							receipts = Receipt.query.filter( Receipt.receipt_type=='unos', Receipt.status=='storno', Receipt.receipt_user==user.id).order_by(Receipt.date.desc()).paginate(per_page=3, page=1, error_out=True)
							#import pdb; pdb.set_trace();
							form.search.data= " "
						else:
							receipts = Receipt.query.filter(Receipt.receipt_tvrtka==tvrtka.id, Receipt.receipt_type=='unos', Receipt.status=='storno', Receipt.receipt_user==user.id).order_by(Receipt.date.desc()).paginate(per_page=3, page=1, error_out=True)
						form.begin.data = ' '
						form.end.data = ' '
					elif form.begin.data is None:
						if form.search.data == "" or form.search.data == " ":
							receipts = Receipt.query.filter(Receipt.receipt_type=='unos', Receipt.status=='storno', Receipt.date <= form.end.data, Receipt.receipt_user==user.id).order_by(Receipt.date.desc()).paginate(per_page=3, page=1, error_out=True)
							form.search.data= " "
						else:
							receipts = Receipt.query.filter(Receipt.receipt_tvrtka==tvrtka.id, Receipt.receipt_type=='unos', Receipt.status=='storno', Receipt.date <= form.end.data, Receipt.receipt_user==user.id).order_by(Receipt.date.desc()).paginate(per_page=3, page=1, error_out=True)
						form.begin.data = ' '
					elif form.end.data is None:
						if form.search.data == "" or form.search.data == " ":
							receipts = Receipt.query.filter(Receipt.receipt_type=='unos', Receipt.status=='storno', Receipt.date >= form.begin.data, Receipt.receipt_user==user.id).order_by(Receipt.date.desc()).paginate(per_page=3, page=1, error_out=True)
							form.search.data= " "
						else:
							receipts = Receipt.query.filter(Receipt.receipt_tvrtka==tvrtka.id, Receipt.receipt_type=='unos', Receipt.status=='storno', Receipt.date >= form.begin.data, Receipt.receipt_user==user.id).order_by(Receipt.date.desc()).paginate(per_page=3, page=1, error_out=True)
						form.end.data = ' '
					else:
						if form.search.data == "" or form.search.data == " ":
							receipts = Receipt.query.filter(Receipt.receipt_type=='unos', Receipt.status=='storno', Receipt.date >= form.begin.data, Receipt.date <= form.end.data, Receipt.receipt_user==user.id).order_by(Receipt.date.desc()).paginate(per_page=3, page=1, error_out=True)
							form.search.data= " "
						else:
							receipts = Receipt.query.filter(Receipt.receipt_tvrtka==tvrtka.id, Receipt.receipt_type=='unos', Receipt.status=='storno', Receipt.date >= form.begin.data, Receipt.date <= form.end.data, Receipt.receipt_user==user.id).order_by(Receipt.date.desc()).paginate(per_page=3, page=1, error_out=True)
				return render_template('receipts_unosa_storno.html', title='Stornirane Primke', form=form, receipts=receipts, search=form.search.data, begin=form.begin.data, end=form.end.data, lista=lista, lista2=lista2, user=form.user.data, st=form.storno.data, page=1)
			else:
				if user is None:
					form.user.data=" "
					if form.begin.data is None and form.end.data is None:
						if form.search.data == "" or form.search.data == " ":
							receipts = Receipt.query.filter(Receipt.receipt_type=='unos', Receipt.status=='storno').order_by(Receipt.storno_date.desc()).paginate(per_page=3, page=1, error_out=True)
							form.search.data= " "
						else:
							receipts = Receipt.query.filter(Receipt.receipt_tvrtka==tvrtka.id, Receipt.receipt_type=='unos', Receipt.status=='storno').order_by(Receipt.storno_date.desc()).paginate(per_page=3, page=1, error_out=True)
						form.begin.data = ' '
						form.end.data = ' '
						form.user.data=' '
					elif form.begin.data is None:
						if form.search.data == "" or form.search.data == " ":
							receipts = Receipt.query.filter(Receipt.receipt_type=='unos', Receipt.status=='storno', Receipt.storno_date <= form.end.data).order_by(Receipt.storno_date.desc()).paginate(per_page=3, page=1, error_out=True)
							form.search.data= " "
						else:
							receipts = Receipt.query.filter(Receipt.receipt_tvrtka==tvrtka.id, Receipt.receipt_type=='unos', Receipt.status=='storno', Receipt.storno_date <= form.end.data).order_by(Receipt.storno_date.desc()).paginate(per_page=3, page=1, error_out=True)
						form.begin.data = ' '
						form.user.data=' '
					elif form.end.data is None:
						if form.search.data == "" or form.search.data == " ":
							receipts = Receipt.query.filter(Receipt.receipt_type=='unos', Receipt.status=='storno', Receipt.storno_date >= form.begin.data).order_by(Receipt.storno_date.desc()).paginate(per_page=3, page=1, error_out=True)
							form.search.data= " "
						else:
							receipts = Receipt.query.filter(Receipt.receipt_tvrtka==tvrtka.id, Receipt.receipt_type=='unos', Receipt.status=='storno', Receipt.storno_date >= form.begin.data).order_by(Receipt.storno_date.desc()).paginate(per_page=3, page=1, error_out=True)
						form.end.data = ' '
						form.user.data=' '
					else:
						form.user.data=' '
						if form.search.data == "" or form.search.data == " ":
							receipts = Receipt.query.filter(Receipt.receipt_type=='unos', Receipt.status=='storno', Receipt.storno_date >= form.begin.data, Receipt.storno_date <= form.end.data).order_by(Receipt.storno_date.desc()).paginate(per_page=3, page=1, error_out=True)
							form.search.data= " "
						else:
							receipts = Receipt.query.filter(Receipt.receipt_tvrtka==tvrtka.id, Receipt.receipt_type=='unos', Receipt.status=='storno', Receipt.storno_date >= form.begin.data, Receipt.storno_date <= form.end.data).order_by(Receipt.storno_date.desc()).paginate(per_page=3, page=1, error_out=True)	
				else:
					#import pdb; pdb.set_trace();
					user = User.query.filter_by(username=form.user.data).first()

					if form.begin.data is None and form.end.data is None:
						if form.search.data == "" or form.search.data == " ":
							receipts = Receipt.query.filter( Receipt.receipt_type=='unos', Receipt.status=='storno', Receipt.storno_user==user.id).order_by(Receipt.storno_date.desc()).paginate(per_page=3, page=1, error_out=True)
							
							form.search.data= " "
						else:
							receipts = Receipt.query.filter(Receipt.receipt_tvrtka==tvrtka.id, Receipt.receipt_type=='unos', Receipt.status=='storno', Receipt.storno_user==user.id).order_by(Receipt.storno_date.desc()).paginate(per_page=3, page=1, error_out=True)
						form.begin.data = ' '
						form.end.data = ' '
					elif form.begin.data is None:
						if form.search.data == "" or form.search.data == " ":
							receipts = Receipt.query.filter(Receipt.receipt_type=='unos', Receipt.status=='storno', Receipt.storno_date <= form.end.data, Receipt.storno_user==user.id).order_by(Receipt.storno_date.desc()).paginate(per_page=3, page=1, error_out=True)
							form.search.data= " "
						else:
							receipts = Receipt.query.filter(Receipt.receipt_tvrtka==tvrtka.id, Receipt.receipt_type=='unos', Receipt.status=='storno', Receipt.storno_date <= form.end.data, Receipt.storno_user==user.id).order_by(Receipt.storno_date.desc()).paginate(per_page=3, page=1, error_out=True)
						form.begin.data = ' '
					elif form.end.data is None:
						if form.search.data == "" or form.search.data == " ":
							receipts = Receipt.query.filter(Receipt.receipt_type=='unos', Receipt.status=='storno', Receipt.storno_date >= form.begin.data, Receipt.storno_user==user.id).order_by(Receipt.storno_date.desc()).paginate(per_page=3, page=1, error_out=True)
							form.search.data= " "
						else:
							receipts = Receipt.query.filter(Receipt.receipt_tvrtka==tvrtka.id, Receipt.receipt_type=='unos', Receipt.status=='storno', Receipt.storno_date >= form.begin.data, Receipt.storno_user==user.id).order_by(Receipt.storno_date.desc()).paginate(per_page=3, page=1, error_out=True)
						form.end.data = ' '
					else:
						if form.search.data == "" or form.search.data == " ":
							receipts = Receipt.query.filter(Receipt.receipt_type=='unos', Receipt.status=='storno', Receipt.storno_date >= form.begin.data, Receipt.storno_date <= form.end.data, Receipt.storno_user==user.id).order_by(Receipt.storno_date.desc()).paginate(per_page=3, page=1, error_out=True)
							form.search.data= " "
						else:
							receipts = Receipt.query.filter(Receipt.receipt_tvrtka==tvrtka.id, Receipt.receipt_type=='unos', Receipt.status=='storno', Receipt.storno_date >= form.begin.data, Receipt.storno_date <= form.end.data, Receipt.storno_user==user.id).order_by(Receipt.storno_date.desc()).paginate(per_page=3, page=1, error_out=True)
				return render_template('receipts_unosa_storno.html', title='Stornirane Primke', form=form, receipts=receipts, search=form.search.data, begin=form.begin.data, end=form.end.data, lista=lista, lista2=lista2, user=form.user.data, st=form.storno.data, page=1)
		#import pdb; pdb.set_trace();
		return redirect(url_for('receipts_unosa_storno1'))
	if st=='aktivni':
		if s == ' ':
			if u==' ':
				if b ==' ' and e==' ':
					receipts = Receipt.query.filter( Receipt.receipt_type=='unos', Receipt.status=='storno').order_by(Receipt.date.desc()).paginate(per_page=3, page=page_num, error_out=True)
				elif b ==' ':
					receipts = Receipt.query.filter( Receipt.receipt_type=='unos', Receipt.status=='storno', Receipt.date <= e).order_by(Receipt.date.desc()).paginate(per_page=3, page=page_num, error_out=True)
				elif e==' ':
					receipts = Receipt.query.filter( Receipt.receipt_type=='unos', Receipt.status=='storno', Receipt.date >= b).order_by(Receipt.date.desc()).paginate(per_page=3, page=page_num, error_out=True)
				else:
					receipts = Receipt.query.filter( Receipt.receipt_type=='unos', Receipt.status=='storno', Receipt.date >= b, Receipt.date <=e).order_by(Receipt.date.desc()).paginate(per_page=3, page=page_num, error_out=True)
			else:
				user = User.query.filter_by(username=u).first()
				if b ==' ' and e==' ':
					receipts = Receipt.query.filter( Receipt.receipt_type=='unos', Receipt.status=='storno', Receipt.receipt_user==user.id).order_by(Receipt.date.desc()).paginate(per_page=3, page=page_num, error_out=True)
				elif b ==' ':
					receipts = Receipt.query.filter( Receipt.receipt_type=='unos', Receipt.status=='storno', Receipt.date <= e, Receipt.receipt_user==user.id).order_by(Receipt.date.desc()).paginate(per_page=3, page=page_num, error_out=True)
				elif e==' ':
					receipts = Receipt.query.filter( Receipt.receipt_type=='unos', Receipt.status=='storno', Receipt.date >= b, Receipt.receipt_user==user.id).order_by(Receipt.date.desc()).paginate(per_page=3, page=page_num, error_out=True)
				else:
					receipts = Receipt.query.filter( Receipt.receipt_type=='unos', Receipt.status=='storno', Receipt.date >= b, Receipt.date <=e, Receipt.receipt_user==user.id).order_by(Receipt.date.desc()).paginate(per_page=3, page=page_num, error_out=True)

		elif not form.submit.data:
			tvrtka=Tvrtka.query.filter(Tvrtka.name.like("%"+s+"%")).first()
			if u == ' ':
				if b ==' ' and e==' ':
					receipts = Receipt.query.filter( Receipt.receipt_tvrtka==tvrtka.id, Receipt.receipt_type=='unos', Receipt.status=='storno').order_by(Receipt.date.desc()).paginate(per_page=3, page=page_num, error_out=True)
				elif b ==' ':
					receipts = Receipt.query.filter(Receipt.receipt_tvrtka==tvrtka.id, Receipt.receipt_type=='unos', Receipt.status=='storno', Receipt.date <= e).order_by(Receipt.date.desc()).paginate(per_page=3, page=page_num, error_out=True)
				elif e ==' ':
					receipts = Receipt.query.filter(Receipt.receipt_tvrtka==tvrtka.id, Receipt.receipt_type=='unos', Receipt.status=='storno', Receipt.date >= b).order_by(Receipt.date.desc()).paginate(per_page=3, page=page_num, error_out=True)
				else:
					receipts = Receipt.query.filter(Receipt.receipt_tvrtka==tvrtka.id, Receipt.receipt_type=='unos', Receipt.status=='storno', Receipt.date >= b, Receipt.date <= e).order_by(Receipt.date.desc()).paginate(per_page=3, page=page_num, error_out=True)
				return render_template('receipts_unosa_storno.html', title='Stornirane Primke', form=form, receipts=receipts, search=s, begin=b, end=e, user=u, st=st, lista=lista, lista2=lista2)
			else:
				user = User.query.filter_by(username=u).first()
				if b ==' ' and e==' ':
					receipts = Receipt.query.filter( Receipt.receipt_tvrtka==tvrtka.id, Receipt.receipt_type=='unos', Receipt.status=='storno', Receipt.receipt_user==user.id).order_by(Receipt.date.desc()).paginate(per_page=3, page=page_num, error_out=True)
				elif b ==' ':
					receipts = Receipt.query.filter(Receipt.receipt_tvrtka==tvrtka.id, Receipt.receipt_type=='unos', Receipt.status=='storno', Receipt.date <= e, Receipt.receipt_user==user.id).order_by(Receipt.date.desc()).paginate(per_page=3, page=page_num, error_out=True)
				elif e ==' ':
					receipts = Receipt.query.filter(Receipt.receipt_tvrtka==tvrtka.id, Receipt.receipt_type=='unos', Receipt.status=='storno', Receipt.date >= b, Receipt.receipt_user==user.id).order_by(Receipt.date.desc()).paginate(per_page=3, page=page_num, error_out=True)
				else:
					receipts = Receipt.query.filter(Receipt.receipt_tvrtka==tvrtka.id, Receipt.receipt_type=='unos', Receipt.status=='storno', Receipt.date >= b, Receipt.date <= e, Receipt.receipt_user==user.id).order_by(Receipt.date.desc()).paginate(per_page=3, page=page_num, error_out=True)
				return render_template('receipts_unosa_storno.html', title='Stornirane Primke', form=form, receipts=receipts, search=s, begin=b, end=e, user=u, st=st, lista=lista, lista2=lista2)
	else:
		if s == ' ':
			if u==' ':
				if b ==' ' and e==' ':
					receipts = Receipt.query.filter( Receipt.receipt_type=='unos', Receipt.status=='storno').order_by(Receipt.storno_date.desc()).paginate(per_page=3, page=page_num, error_out=True)
				elif b ==' ':
					receipts = Receipt.query.filter( Receipt.receipt_type=='unos', Receipt.status=='storno', Receipt.storno_date <= e).order_by(Receipt.storno_date.desc()).paginate(per_page=3, page=page_num, error_out=True)
				elif e==' ':
					receipts = Receipt.query.filter( Receipt.receipt_type=='unos', Receipt.status=='storno', Receipt.storno_date >= b).order_by(Receipt.storno_date.desc()).paginate(per_page=3, page=page_num, error_out=True)
				else:
					receipts = Receipt.query.filter( Receipt.receipt_type=='unos', Receipt.status=='storno', Receipt.storno_date >= b, Receipt.storno_date <=e).order_by(Receipt.storno_date.desc()).paginate(per_page=3, page=page_num, error_out=True)
			else:
				user = User.query.filter_by(username=u).first()
				if b ==' ' and e==' ':
					receipts = Receipt.query.filter( Receipt.receipt_type=='unos', Receipt.status=='storno', Receipt.storno_user==user.id).order_by(Receipt.storno_date.desc()).paginate(per_page=3, page=page_num, error_out=True)
				elif b ==' ':
					receipts = Receipt.query.filter( Receipt.receipt_type=='unos', Receipt.status=='storno', Receipt.storno_date <= e, Receipt.storno_user==user.id).order_by(Receipt.storno_date.desc()).paginate(per_page=3, page=page_num, error_out=True)
				elif e==' ':
					receipts = Receipt.query.filter( Receipt.receipt_type=='unos', Receipt.status=='storno', Receipt.storno_date >= b, Receipt.storno_user==user.id).order_by(Receipt.storno_date.desc()).paginate(per_page=3, page=page_num, error_out=True)
				else:
					receipts = Receipt.query.filter( Receipt.receipt_type=='unos', Receipt.status=='storno', Receipt.storno_date >= b, Receipt.storno_date <=e, Receipt.storno_user==user.id).order_by(Receipt.storno_date.desc()).paginate(per_page=3, page=page_num, error_out=True)

		elif not form.submit.data:
			tvrtka=Tvrtka.query.filter(Tvrtka.name.like("%"+s+"%")).first()
			#import pdb; pdb.set_trace()
			if u == ' ':
				if b ==' ' and e==' ':
					receipts = Receipt.query.filter( Receipt.receipt_tvrtka==tvrtka.id, Receipt.receipt_type=='unos', Receipt.status=='storno').order_by(Receipt.storno_date.desc()).paginate(per_page=3, page=page_num, error_out=True)
				elif b ==' ':
					receipts = Receipt.query.filter(Receipt.receipt_tvrtka==tvrtka.id, Receipt.receipt_type=='unos', Receipt.status=='storno', Receipt.storno_date <= e).order_by(Receipt.storno_date.desc()).paginate(per_page=3, page=page_num, error_out=True)
				elif e ==' ':
					receipts = Receipt.query.filter(Receipt.receipt_tvrtka==tvrtka.id, Receipt.receipt_type=='unos', Receipt.status=='storno', Receipt.storno_date >= b).order_by(Receipt.storno_date.desc()).paginate(per_page=3, page=page_num, error_out=True)
				else:
					receipts = Receipt.query.filter(Receipt.receipt_tvrtka==tvrtka.id, Receipt.receipt_type=='unos', Receipt.status=='storno', Receipt.storno_date >= b, Receipt.storno_date <= e).order_by(Receipt.storno_date.desc()).paginate(per_page=3, page=page_num, error_out=True)
				return render_template('receipts_unosa_storno.html', title='Stornirane Primke', form=form, receipts=receipts, search=s, begin=b, end=e, user=u, st=st, lista=lista, lista2=lista2)
			else:
				user = User.query.filter_by(username=u).first()
				if b ==' ' and e==' ':

					receipts = Receipt.query.filter(Receipt.receipt_tvrtka==tvrtka.id, Receipt.receipt_type=='unos', Receipt.status=='storno', Receipt.storno_user==user.id).order_by(Receipt.storno_date.desc()).paginate(per_page=3, page=page_num, error_out=True)
				elif b ==' ':
					receipts = Receipt.query.filter(Receipt.receipt_tvrtka==tvrtka.id, Receipt.receipt_type=='unos', Receipt.status=='storno', Receipt.storno_date <= e, Receipt.storno_user==user.id).order_by(Receipt.storno_date.desc()).paginate(per_page=3, page=page_num, error_out=True)
				elif e ==' ':
					receipts = Receipt.query.filter(Receipt.receipt_tvrtka==tvrtka.id, Receipt.receipt_type=='unos', Receipt.status=='storno', Receipt.storno_date >= b, Receipt.storno_user==user.id).order_by(Receipt.storno_date.desc()).paginate(per_page=3, page=page_num, error_out=True)
				else:
					receipts = Receipt.query.filter(Receipt.receipt_tvrtka==tvrtka.id, Receipt.receipt_type=='unos', Receipt.status=='storno', Receipt.storno_date >= b, Receipt.storno_date <= e, Receipt.storno_user==user.id).order_by(Receipt.storno_date.desc()).paginate(per_page=3, page=page_num, error_out=True)
				return render_template('receipts_unosa_storno.html', title='Stornirane Primke', form=form, receipts=receipts, search=s, begin=b, end=e, user=u, st=st, lista=lista, lista2=lista2)
	
	
	return render_template('receipts_unosa_storno.html', title='Stornirane Primke', form=form, receipts=receipts, search=s, begin=b, end=e, user=u, st=st, lista=lista, lista2=lista2)

@app.route('/receipts_unosa_storno1', methods=['GET', 'POST'])
@login_required
def receipts_unosa_storno1():
	return redirect(url_for('receipts_unosa_storno', page_num=1, s=" ", b=" ", e=" ", u=" ", st="aktivni"))

@app.route('/receipts_izlaz_storno/<int:page_num>+<s>+<b>+<e>+<u>+<st>', methods=['GET', 'POST'])
@login_required
def receipts_izlaz_storno(page_num, s, b, e, u, st):
	form = SearchFormReceiptStorno()
	lista = []
	lista2 = []
	sveTvrtke = Tvrtka.query.all()
	for tvrtka in sveTvrtke:
		lista.append(tvrtka.name)
	sviUseri = User.query.all()
	for user in sviUseri:
		lista2.append(user.username)
	if form.submit.data:
		if form.validate_on_submit():

			number = form.search.data
			if number.isdigit():
				receipts= Receipt.query.filter_by(id =number, status='storno', receipt_type='izlaz').paginate(per_page=3, page=1, error_out=True)
				return render_template('receipts_izlaz_storno.html', title='Stornirane Primke', form=form, receipts=receipts, search=" ", begin=" ", end=" ", user=" ", lista=lista, lista2=lista2)
			tvrtka = Tvrtka.query.filter(Tvrtka.name.like("%" + form.search.data + "%")).first()
			if form.search.data != "" and form.search.data != " " and tvrtka is None:
				flash(f'Tvrtka '+form.search.data+ ' ne postoji!', 'danger')
				return redirect(url_for('receipts_izlaz_storno1'))
				#import pdb; pdb.set_trace();
			user = User.query.filter_by(username=form.user.data).first()
			if form.user.data != "" and form.user.data != " " and user is None:
				flash(f'Korisnik '+form.user.data+ ' ne postoji!', 'danger')
				return redirect(url_for('receipts_izlaz_storno1'))
			#import pdb; pdb.set_trace();
			if form.storno.data=="aktivni":
				if user is None:
					form.user.data=" "
					if form.begin.data is None and form.end.data is None:
						if form.search.data == "" or form.search.data == " ":
							receipts = Receipt.query.filter(Receipt.receipt_type=='izlaz', Receipt.status=='storno').order_by(Receipt.date.desc()).paginate(per_page=3, page=1, error_out=True)
							form.search.data= " "
						else:
							receipts = Receipt.query.filter(Receipt.receipt_tvrtka==tvrtka.id, Receipt.receipt_type=='izlaz', Receipt.status=='storno').order_by(Receipt.date.desc()).paginate(per_page=3, page=1, error_out=True)
						form.begin.data = ' '
						form.end.data = ' '
						form.user.data=' '
					elif form.begin.data is None:
						if form.search.data == "" or form.search.data == " ":
							receipts = Receipt.query.filter(Receipt.receipt_type=='izlaz', Receipt.status=='storno', Receipt.date <= form.end.data).order_by(Receipt.date.desc()).paginate(per_page=3, page=1, error_out=True)
							form.search.data= " "
						else:
							receipts = Receipt.query.filter(Receipt.receipt_tvrtka==tvrtka.id, Receipt.receipt_type=='izlaz', Receipt.status=='storno', Receipt.date <= form.end.data).order_by(Receipt.date.desc()).paginate(per_page=3, page=1, error_out=True)
						form.begin.data = ' '
						form.user.data=' '
					elif form.end.data is None:
						if form.search.data == "" or form.search.data == " ":
							receipts = Receipt.query.filter(Receipt.receipt_type=='izlaz', Receipt.status=='storno', Receipt.date >= form.begin.data).order_by(Receipt.date.desc()).paginate(per_page=3, page=1, error_out=True)
							form.search.data= " "
						else:
							receipts = Receipt.query.filter(Receipt.receipt_tvrtka==tvrtka.id, Receipt.receipt_type=='izlaz', Receipt.status=='storno', Receipt.date >= form.begin.data).order_by(Receipt.date.desc()).paginate(per_page=3, page=1, error_out=True)
						form.end.data = ' '
						form.user.data=' '
					else:
						form.user.data=' '
						if form.search.data == "" or form.search.data == " ":
							receipts = Receipt.query.filter(Receipt.receipt_type=='izlaz', Receipt.status=='storno', Receipt.date >= form.begin.data, Receipt.date <= form.end.data).order_by(Receipt.date.desc()).paginate(per_page=3, page=1, error_out=True)
							form.search.data= " "
						else:
							receipts = Receipt.query.filter(Receipt.receipt_tvrtka==tvrtka.id, Receipt.receipt_type=='izlaz', Receipt.status=='storno', Receipt.date >= form.begin.data, Receipt.date <= form.end.data).order_by(Receipt.date.desc()).paginate(per_page=3, page=1, error_out=True)	
				else:
					#import pdb; pdb.set_trace();
					user = User.query.filter_by(username=form.user.data).first()
					if form.begin.data is None and form.end.data is None:
						if form.search.data == "" or form.search.data == " ":
							receipts = Receipt.query.filter( Receipt.receipt_type=='izlaz', Receipt.status=='storno', Receipt.receipt_user==user.id).order_by(Receipt.date.desc()).paginate(per_page=3, page=1, error_out=True)
							#import pdb; pdb.set_trace();
							form.search.data= " "
						else:
							receipts = Receipt.query.filter(Receipt.receipt_tvrtka==tvrtka.id, Receipt.receipt_type=='izlaz', Receipt.status=='storno', Receipt.receipt_user==user.id).order_by(Receipt.date.desc()).paginate(per_page=3, page=1, error_out=True)
						form.begin.data = ' '
						form.end.data = ' '
					elif form.begin.data is None:
						if form.search.data == "" or form.search.data == " ":
							receipts = Receipt.query.filter(Receipt.receipt_type=='izlaz', Receipt.status=='storno', Receipt.date <= form.end.data, Receipt.receipt_user==user.id).order_by(Receipt.date.desc()).paginate(per_page=3, page=1, error_out=True)
							form.search.data= " "
						else:
							receipts = Receipt.query.filter(Receipt.receipt_tvrtka==tvrtka.id, Receipt.receipt_type=='izlaz', Receipt.status=='storno', Receipt.date <= form.end.data, Receipt.receipt_user==user.id).order_by(Receipt.date.desc()).paginate(per_page=3, page=1, error_out=True)
						form.begin.data = ' '
					elif form.end.data is None:
						if form.search.data == "" or form.search.data == " ":
							receipts = Receipt.query.filter(Receipt.receipt_type=='izlaz', Receipt.status=='storno', Receipt.date >= form.begin.data, Receipt.receipt_user==user.id).order_by(Receipt.date.desc()).paginate(per_page=3, page=1, error_out=True)
							form.search.data= " "
						else:
							receipts = Receipt.query.filter(Receipt.receipt_tvrtka==tvrtka.id, Receipt.receipt_type=='izlaz', Receipt.status=='storno', Receipt.date >= form.begin.data, Receipt.receipt_user==user.id).order_by(Receipt.date.desc()).paginate(per_page=3, page=1, error_out=True)
						form.end.data = ' '
					else:
						if form.search.data == "" or form.search.data == " ":
							receipts = Receipt.query.filter(Receipt.receipt_type=='izlaz', Receipt.status=='storno', Receipt.date >= form.begin.data, Receipt.date <= form.end.data, Receipt.receipt_user==user.id).order_by(Receipt.date.desc()).paginate(per_page=3, page=1, error_out=True)
							form.search.data= " "
						else:
							receipts = Receipt.query.filter(Receipt.receipt_tvrtka==tvrtka.id, Receipt.receipt_type=='izlaz', Receipt.status=='storno', Receipt.date >= form.begin.data, Receipt.date <= form.end.data, Receipt.receipt_user==user.id).order_by(Receipt.date.desc()).paginate(per_page=3, page=1, error_out=True)
				return render_template('receipts_izlaz_storno.html', title='Stornirane Otpremnice', form=form, receipts=receipts, search=form.search.data, begin=form.begin.data, end=form.end.data, lista=lista, lista2=lista2, user=form.user.data, st=form.storno.data, page=1)
			else:
				if user is None:
					form.user.data=" "
					if form.begin.data is None and form.end.data is None:
						if form.search.data == "" or form.search.data == " ":
							receipts = Receipt.query.filter(Receipt.receipt_type=='izlaz', Receipt.status=='storno').order_by(Receipt.storno_date.desc()).paginate(per_page=3, page=1, error_out=True)
							form.search.data= " "
						else:
							receipts = Receipt.query.filter(Receipt.receipt_tvrtka==tvrtka.id, Receipt.receipt_type=='izlaz', Receipt.status=='storno').order_by(Receipt.storno_date.desc()).paginate(per_page=3, page=1, error_out=True)
						form.begin.data = ' '
						form.end.data = ' '
						form.user.data=' '
					elif form.begin.data is None:
						if form.search.data == "" or form.search.data == " ":
							receipts = Receipt.query.filter(Receipt.receipt_type=='izlaz', Receipt.status=='storno', Receipt.storno_date <= form.end.data).order_by(Receipt.storno_date.desc()).paginate(per_page=3, page=1, error_out=True)
							form.search.data= " "
						else:
							receipts = Receipt.query.filter(Receipt.receipt_tvrtka==tvrtka.id, Receipt.receipt_type=='izlaz', Receipt.status=='storno', Receipt.storno_date <= form.end.data).order_by(Receipt.storno_date.desc()).paginate(per_page=3, page=1, error_out=True)
						form.begin.data = ' '
						form.user.data=' '
					elif form.end.data is None:
						if form.search.data == "" or form.search.data == " ":
							receipts = Receipt.query.filter(Receipt.receipt_type=='izlaz', Receipt.status=='storno', Receipt.storno_date >= form.begin.data).order_by(Receipt.storno_date.desc()).paginate(per_page=3, page=1, error_out=True)
							form.search.data= " "
						else:
							receipts = Receipt.query.filter(Receipt.receipt_tvrtka==tvrtka.id, Receipt.receipt_type=='izlaz', Receipt.status=='storno', Receipt.storno_date >= form.begin.data).order_by(Receipt.storno_date.desc()).paginate(per_page=3, page=1, error_out=True)
						form.end.data = ' '
						form.user.data=' '
					else:
						form.user.data=' '
						if form.search.data == "" or form.search.data == " ":
							receipts = Receipt.query.filter(Receipt.receipt_type=='izlaz', Receipt.status=='storno', Receipt.storno_date >= form.begin.data, Receipt.storno_date <= form.end.data).order_by(Receipt.storno_date.desc()).paginate(per_page=3, page=1, error_out=True)
							form.search.data= " "
						else:
							receipts = Receipt.query.filter(Receipt.receipt_tvrtka==tvrtka.id, Receipt.receipt_type=='izlaz', Receipt.status=='storno', Receipt.storno_date >= form.begin.data, Receipt.storno_date <= form.end.data).order_by(Receipt.storno_date.desc()).paginate(per_page=3, page=1, error_out=True)	
				else:
					#import pdb; pdb.set_trace();
					user = User.query.filter_by(username=form.user.data).first()

					if form.begin.data is None and form.end.data is None:
						if form.search.data == "" or form.search.data == " ":
							receipts = Receipt.query.filter( Receipt.receipt_type=='izlaz', Receipt.status=='storno', Receipt.storno_user==user.id).order_by(Receipt.storno_date.desc()).paginate(per_page=3, page=1, error_out=True)
							
							form.search.data= " "
						else:
							receipts = Receipt.query.filter(Receipt.receipt_tvrtka==tvrtka.id, Receipt.receipt_type=='izlaz', Receipt.status=='storno', Receipt.storno_user==user.id).order_by(Receipt.storno_date.desc()).paginate(per_page=3, page=1, error_out=True)
						form.begin.data = ' '
						form.end.data = ' '
					elif form.begin.data is None:
						if form.search.data == "" or form.search.data == " ":
							receipts = Receipt.query.filter(Receipt.receipt_type=='izlaz', Receipt.status=='storno', Receipt.storno_date <= form.end.data, Receipt.storno_user==user.id).order_by(Receipt.storno_date.desc()).paginate(per_page=3, page=1, error_out=True)
							form.search.data= " "
						else:
							receipts = Receipt.query.filter(Receipt.receipt_tvrtka==tvrtka.id, Receipt.receipt_type=='izlaz', Receipt.status=='storno', Receipt.storno_date <= form.end.data, Receipt.storno_user==user.id).order_by(Receipt.storno_date.desc()).paginate(per_page=3, page=1, error_out=True)
						form.begin.data = ' '
					elif form.end.data is None:
						if form.search.data == "" or form.search.data == " ":
							receipts = Receipt.query.filter(Receipt.receipt_type=='izlaz', Receipt.status=='storno', Receipt.storno_date >= form.begin.data, Receipt.storno_user==user.id).order_by(Receipt.storno_date.desc()).paginate(per_page=3, page=1, error_out=True)
							form.search.data= " "
						else:
							receipts = Receipt.query.filter(Receipt.receipt_tvrtka==tvrtka.id, Receipt.receipt_type=='izlaz', Receipt.status=='storno', Receipt.storno_date >= form.begin.data, Receipt.storno_user==user.id).order_by(Receipt.storno_date.desc()).paginate(per_page=3, page=1, error_out=True)
						form.end.data = ' '
					else:
						if form.search.data == "" or form.search.data == " ":
							receipts = Receipt.query.filter(Receipt.receipt_type=='izlaz', Receipt.status=='storno', Receipt.storno_date >= form.begin.data, Receipt.storno_date <= form.end.data, Receipt.storno_user==user.id).order_by(Receipt.storno_date.desc()).paginate(per_page=3, page=1, error_out=True)
							form.search.data= " "
						else:
							receipts = Receipt.query.filter(Receipt.receipt_tvrtka==tvrtka.id, Receipt.receipt_type=='izlaz', Receipt.status=='storno', Receipt.storno_date >= form.begin.data, Receipt.storno_date <= form.end.data, Receipt.storno_user==user.id).order_by(Receipt.storno_date.desc()).paginate(per_page=3, page=1, error_out=True)
				return render_template('receipts_izlaz_storno.html', title='Stornirane Otpremnice', form=form, receipts=receipts, search=form.search.data, begin=form.begin.data, end=form.end.data, lista=lista, lista2=lista2, user=form.user.data, st=form.storno.data, page=1)
		#import pdb; pdb.set_trace();
		return redirect(url_for('receipts_izlaz_storno1'))
	if st=='aktivni':
		if s == ' ':
			if u==' ':
				if b ==' ' and e==' ':
					receipts = Receipt.query.filter( Receipt.receipt_type=='izlaz', Receipt.status=='storno').order_by(Receipt.date.desc()).paginate(per_page=3, page=page_num, error_out=True)
				elif b ==' ':
					receipts = Receipt.query.filter( Receipt.receipt_type=='izlaz', Receipt.status=='storno', Receipt.date <= e).order_by(Receipt.date.desc()).paginate(per_page=3, page=page_num, error_out=True)
				elif e==' ':
					receipts = Receipt.query.filter( Receipt.receipt_type=='izlaz', Receipt.status=='storno', Receipt.date >= b).order_by(Receipt.date.desc()).paginate(per_page=3, page=page_num, error_out=True)
				else:
					receipts = Receipt.query.filter( Receipt.receipt_type=='izlaz', Receipt.status=='storno', Receipt.date >= b, Receipt.date <=e).order_by(Receipt.date.desc()).paginate(per_page=3, page=page_num, error_out=True)
			else:
				user = User.query.filter_by(username=u).first()
				if b ==' ' and e==' ':
					receipts = Receipt.query.filter( Receipt.receipt_type=='izlaz', Receipt.status=='storno', Receipt.receipt_user==user.id).order_by(Receipt.date.desc()).paginate(per_page=3, page=page_num, error_out=True)
				elif b ==' ':
					receipts = Receipt.query.filter( Receipt.receipt_type=='izlaz', Receipt.status=='storno', Receipt.date <= e, Receipt.receipt_user==user.id).order_by(Receipt.date.desc()).paginate(per_page=3, page=page_num, error_out=True)
				elif e==' ':
					receipts = Receipt.query.filter( Receipt.receipt_type=='izlaz', Receipt.status=='storno', Receipt.date >= b, Receipt.receipt_user==user.id).order_by(Receipt.date.desc()).paginate(per_page=3, page=page_num, error_out=True)
				else:
					receipts = Receipt.query.filter( Receipt.receipt_type=='izlaz', Receipt.status=='storno', Receipt.date >= b, Receipt.date <=e, Receipt.receipt_user==user.id).order_by(Receipt.date.desc()).paginate(per_page=3, page=page_num, error_out=True)

		elif not form.submit.data:
			tvrtka=Tvrtka.query.filter(Tvrtka.name.like("%"+s+"%")).first()
			if u == ' ':
				if b ==' ' and e==' ':
					receipts = Receipt.query.filter( Receipt.receipt_tvrtka==tvrtka.id, Receipt.receipt_type=='izlaz', Receipt.status=='storno').order_by(Receipt.date.desc()).paginate(per_page=3, page=page_num, error_out=True)
				elif b ==' ':
					receipts = Receipt.query.filter(Receipt.receipt_tvrtka==tvrtka.id, Receipt.receipt_type=='izlaz', Receipt.status=='storno', Receipt.date <= e).order_by(Receipt.date.desc()).paginate(per_page=3, page=page_num, error_out=True)
				elif e ==' ':
					receipts = Receipt.query.filter(Receipt.receipt_tvrtka==tvrtka.id, Receipt.receipt_type=='izlaz', Receipt.status=='storno', Receipt.date >= b).order_by(Receipt.date.desc()).paginate(per_page=3, page=page_num, error_out=True)
				else:
					receipts = Receipt.query.filter(Receipt.receipt_tvrtka==tvrtka.id, Receipt.receipt_type=='izlaz', Receipt.status=='storno', Receipt.date >= b, Receipt.date <= e).order_by(Receipt.date.desc()).paginate(per_page=3, page=page_num, error_out=True)
				return render_template('receipts_izlaz_storno.html', title='Stornirane Otpremnice', form=form, receipts=receipts, search=s, begin=b, end=e, user=u, st=st, lista=lista, lista2=lista2)
			else:
				user = User.query.filter_by(username=u).first()
				if b ==' ' and e==' ':
					receipts = Receipt.query.filter( Receipt.receipt_tvrtka==tvrtka.id, Receipt.receipt_type=='izlaz', Receipt.status=='storno', Receipt.receipt_user==user.id).order_by(Receipt.date.desc()).paginate(per_page=3, page=page_num, error_out=True)
				elif b ==' ':
					receipts = Receipt.query.filter(Receipt.receipt_tvrtka==tvrtka.id, Receipt.receipt_type=='izlaz', Receipt.status=='storno', Receipt.date <= e, Receipt.receipt_user==user.id).order_by(Receipt.date.desc()).paginate(per_page=3, page=page_num, error_out=True)
				elif e ==' ':
					receipts = Receipt.query.filter(Receipt.receipt_tvrtka==tvrtka.id, Receipt.receipt_type=='izlaz', Receipt.status=='storno', Receipt.date >= b, Receipt.receipt_user==user.id).order_by(Receipt.date.desc()).paginate(per_page=3, page=page_num, error_out=True)
				else:
					receipts = Receipt.query.filter(Receipt.receipt_tvrtka==tvrtka.id, Receipt.receipt_type=='izlaz', Receipt.status=='storno', Receipt.date >= b, Receipt.date <= e, Receipt.receipt_user==user.id).order_by(Receipt.date.desc()).paginate(per_page=3, page=page_num, error_out=True)
				return render_template('receipts_izlaz_storno.html', title='Stornirane Otpremnice', form=form, receipts=receipts, search=s, begin=b, end=e, user=u, st=st, lista=lista, lista2=lista2)
	else:
		if s == ' ':
			if u==' ':
				if b ==' ' and e==' ':
					receipts = Receipt.query.filter( Receipt.receipt_type=='izlaz', Receipt.status=='storno').order_by(Receipt.storno_date.desc()).paginate(per_page=3, page=page_num, error_out=True)
				elif b ==' ':
					receipts = Receipt.query.filter( Receipt.receipt_type=='izlaz', Receipt.status=='storno', Receipt.storno_date <= e).order_by(Receipt.storno_date.desc()).paginate(per_page=3, page=page_num, error_out=True)
				elif e==' ':
					receipts = Receipt.query.filter( Receipt.receipt_type=='izlaz', Receipt.status=='storno', Receipt.storno_date >= b).order_by(Receipt.storno_date.desc()).paginate(per_page=3, page=page_num, error_out=True)
				else:
					receipts = Receipt.query.filter( Receipt.receipt_type=='izlaz', Receipt.status=='storno', Receipt.storno_date >= b, Receipt.storno_date <=e).order_by(Receipt.storno_date.desc()).paginate(per_page=3, page=page_num, error_out=True)
			else:
				user = User.query.filter_by(username=u).first()
				if b ==' ' and e==' ':
					receipts = Receipt.query.filter( Receipt.receipt_type=='izlaz', Receipt.status=='storno', Receipt.storno_user==user.id).order_by(Receipt.storno_date.desc()).paginate(per_page=3, page=page_num, error_out=True)
				elif b ==' ':
					receipts = Receipt.query.filter( Receipt.receipt_type=='izlaz', Receipt.status=='storno', Receipt.storno_date <= e, Receipt.storno_user==user.id).order_by(Receipt.storno_date.desc()).paginate(per_page=3, page=page_num, error_out=True)
				elif e==' ':
					receipts = Receipt.query.filter( Receipt.receipt_type=='izlaz', Receipt.status=='storno', Receipt.storno_date >= b, Receipt.storno_user==user.id).order_by(Receipt.storno_date.desc()).paginate(per_page=3, page=page_num, error_out=True)
				else:
					receipts = Receipt.query.filter( Receipt.receipt_type=='izlaz', Receipt.status=='storno', Receipt.storno_date >= b, Receipt.storno_date <=e, Receipt.storno_user==user.id).order_by(Receipt.storno_date.desc()).paginate(per_page=3, page=page_num, error_out=True)

		elif not form.submit.data:
			tvrtka=Tvrtka.query.filter(Tvrtka.name.like("%"+s+"%")).first()
			if u == ' ':
				if b ==' ' and e==' ':
					receipts = Receipt.query.filter( Receipt.receipt_tvrtka==tvrtka.id, Receipt.receipt_type=='izlaz', Receipt.status=='storno').order_by(Receipt.storno_date.desc()).paginate(per_page=3, page=page_num, error_out=True)
				elif b ==' ':
					receipts = Receipt.query.filter(Receipt.receipt_tvrtka==tvrtka.id, Receipt.receipt_type=='izlaz', Receipt.status=='storno', Receipt.storno_date <= e).order_by(Receipt.storno_date.desc()).paginate(per_page=3, page=page_num, error_out=True)
				elif e ==' ':
					receipts = Receipt.query.filter(Receipt.receipt_tvrtka==tvrtka.id, Receipt.receipt_type=='izlaz', Receipt.status=='storno', Receipt.storno_date >= b).order_by(Receipt.storno_date.desc()).paginate(per_page=3, page=page_num, error_out=True)
				else:
					receipts = Receipt.query.filter(Receipt.receipt_tvrtka==tvrtka.id, Receipt.receipt_type=='izlaz', Receipt.status=='storno', Receipt.storno_date >= b, Receipt.storno_date <= e).order_by(Receipt.storno_date.desc()).paginate(per_page=3, page=page_num, error_out=True)
				return render_template('receipts_izlaz_storno.html', title='Stornirane Otpremnice', form=form, receipts=receipts, search=s, begin=b, end=e, user=u, st=st, lista=lista, lista2=lista2)
			else:
				user = User.query.filter_by(username=u).first()
				if b ==' ' and e==' ':
					receipts = Receipt.query.filter( Receipt.receipt_tvrtka==tvrtka.id, Receipt.receipt_type=='izlaz', Receipt.status=='storno', Receipt.storno_user==user.id).order_by(Receipt.storno_date.desc()).paginate(per_page=3, page=page_num, error_out=True)
				elif b ==' ':
					receipts = Receipt.query.filter(Receipt.receipt_tvrtka==tvrtka.id, Receipt.receipt_type=='izlaz', Receipt.status=='storno', Receipt.storno_date <= e, Receipt.storno_user==user.id).order_by(Receipt.storno_date.desc()).paginate(per_page=3, page=page_num, error_out=True)
				elif e ==' ':
					receipts = Receipt.query.filter(Receipt.receipt_tvrtka==tvrtka.id, Receipt.receipt_type=='izlaz', Receipt.status=='storno', Receipt.storno_date >= b, Receipt.storno_user==user.id).order_by(Receipt.storno_date.desc()).paginate(per_page=3, page=page_num, error_out=True)
				else:
					receipts = Receipt.query.filter(Receipt.receipt_tvrtka==tvrtka.id, Receipt.receipt_type=='izlaz', Receipt.status=='storno', Receipt.storno_date >= b, Receipt.storno_date <= e, Receipt.storno_user==user.id).order_by(Receipt.storno_date.desc()).paginate(per_page=3, page=page_num, error_out=True)
				return render_template('receipts_izlaz_storno.html', title='Stornirane Otpremnice', form=form, receipts=receipts, search=s, begin=b, end=e, user=u, st=st, lista=lista, lista2=lista2)
	
	
	return render_template('receipts_izlaz_storno.html', title='Stornirane Otpremnice', form=form, receipts=receipts, search=s, begin=b, end=e, user=u, st=st, lista=lista, lista2=lista2)

@app.route('/receipts_izlaz_storno1', methods=['GET', 'POST'])
@login_required
def receipts_izlaz_storno1():
	return redirect(url_for('receipts_izlaz_storno', page_num=1, s=" ", b=" ", e=" ", u=" ", st="aktivni"))

@app.route('/receipt/<id>', methods=['GET', 'POST'])
@login_required
def receipt(id):
	form = Storno()
	evidencije = Evidencija.query.filter_by(receipt_id=id)
	evidencija = Evidencija.query.filter_by(receipt_id=id).first()
	receipt = Receipt.query.get(id)
	if form.submit.data:
		if form.validate_on_submit():
			if receipt.status!="storno":
				receipt.status="storno"
				for e in evidencije:
					proizvod= Proizvod.query.get(e.proizvod_id)
					if e.vrsta_unosa == 'unos':
						if proizvod.kolicina<e.promijenjena_kolicina:
							flash(f'Nema dovoljno kolicine na stanju za stornirati proizvod '+proizvod.name+'!', 'danger')
						else:
							proizvod.kolicina -= e.promijenjena_kolicina
							receipt.storno_date=datetime.utcnow()
							receipt.storno_user=current_user.id
							db.session.add(proizvod)
							db.session.add(receipt)
							db.session.commit()
					elif e.vrsta_unosa == 'izlaz':
						proizvod.kolicina += e.promijenjena_kolicina
						receipt.storno_date=datetime.utcnow()
						receipt.storno_user=current_user.id
						db.session.add(proizvod)
						db.session.add(receipt)
						db.session.commit()
	return render_template('receipt.html', id=id, evidencije=evidencije, evidencija=evidencija, receipt=receipt, form=form)

@app.route('/receipt_pdf/<id>')
@login_required
def receipt_pdf(id):
	receipt = Receipt.query.get(id)
	evidencije = Evidencija.query.filter_by(receipt_id=id)
	evidencija = Evidencija.query.filter_by(receipt_id=id).first()
	html = render_template('receipt_pdf.html', id=id, evidencije=evidencije, evidencija=evidencija, receipt=receipt)
	pdf= pdfkit.from_string(html, False, configuration=config)
	response = make_response(pdf)
	response.headers['Content-Type']='application/pdf'
	if evidencija.vrsta_unosa == "izlaz":
		response.headers['Content-Disposition']= 'inline; filename="{}"'.format('otpremnica '+id+'.pdf')
	else:
		response.headers['Content-Disposition']= 'inline; filename="{}"'.format('primka '+id+'.pdf')
	return response