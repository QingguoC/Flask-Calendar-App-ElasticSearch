#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Fri Mar  2 19:22:47 2018

@author: qingguo
"""
from flask import Flask, render_template, redirect ,request, url_for
from flask_sqlalchemy import SQLAlchemy
from flask_bootstrap import Bootstrap
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, DateTimeField
from wtforms.validators import InputRequired, Email, Length
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from flask_pymongo import PyMongo
from elasticsearch import Elasticsearch
import datetime
import json
from bson import ObjectId
from os.path import join, dirname
import os
from dotenv import load_dotenv


app = Flask(__name__)

dotenv_path = join(dirname(__file__), '.env')
load_dotenv(dotenv_path)
SQLALCHEMY_DATABASE_URI = os.getenv('SQLALCHEMY_DATABASE_URI')
SECRET_KEY = os.getenv('SECRET_KEY')
MONGO_DBNAME = os.getenv('MONGO_DBNAME')
MONGO_URI = os.getenv('MONGO_URI')
ELASTICSEARCH_URL = os.getenv('ELASTICSEARCH_URL')
app.config['SQLALCHEMY_DATABASE_URI'] = SQLALCHEMY_DATABASE_URI
app.config['SECRET_KEY'] = SECRET_KEY
app.config['MONGO_DBNAME'] = MONGO_DBNAME
app.config['MONGO_URI'] = MONGO_URI
app.config['ELASTICSEARCH_URL'] = ELASTICSEARCH_URL

es = Elasticsearch([app.config['ELASTICSEARCH_URL']])

mongo = PyMongo(app)
Bootstrap(app)
class LoginForm(FlaskForm):
    username = StringField('username',validators = [InputRequired(), Length(min=3,max=30)])
    password = PasswordField('password',validators = [InputRequired(), Length(min=3, max=255)])
    
class RegisterForm(FlaskForm):
    username = StringField('username', validators=[InputRequired(), Length(min=3, max=30)])
    password = PasswordField('password', validators=[InputRequired(), Length(min=3, max=255)])
    email = StringField('email', validators=[InputRequired(), Email(message='Invalid email'), Length(max=50)])
    firstName = StringField('firstName', validators=[InputRequired(), Length(min=1, max=50)])
    lastName = StringField('lastName', validators=[InputRequired(), Length(min=1, max=50)])
class SearchForm(FlaskForm):
    keyword = StringField('keyword',validators = [InputRequired(), Length(min=1,max=255)])
    
class CalendarForm(FlaskForm):
    eventname = StringField('event', validators=[InputRequired(), Length(min=1, max=100)])
    time = DateTimeField('time', validators=[InputRequired()],render_kw={"placeholder": "YYYY-mm-dd hh:mm:ss"})
    note = StringField('note', validators=[Length(max=255)])
          
class JSONEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, ObjectId):
            return str(o)
        return json.JSONEncoder.default(self, o)
db = SQLAlchemy(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

class Users(UserMixin,db.Model):
    id = db.Column(db.Integer, primary_key = True)
    username = db.Column(db.String(50), unique = True)
    firstName = db.Column(db.String(100))
    lastName = db.Column(db.String(100))
    email = db.Column(db.String(100), unique = True)
    password = db.Column(db.String(200))

@login_manager.user_loader
def load_user(user_id):
    return Users.query.get(int(user_id))        

@app.before_first_request
def setupDatabase():
    db.create_all()

@app.route("/")

def index():
    return render_template('index.html')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    form = RegisterForm()

    if form.validate_on_submit():
        hashed_password = generate_password_hash(form.password.data, method='sha256')
        new_user = Users(username=form.username.data,firstName=form.firstName.data,lastName=form.lastName.data, email=form.email.data, password=hashed_password)
        db.session.add(new_user)
        db.session.commit()

        return redirect('/search')

    return render_template('register.html', form=form)
    
@app.route('/login',  methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        user = Users.query.filter_by(username=form.username.data).first()
        if user:
            if check_password_hash(user.password, form.password.data):
                login_user(user)
                return redirect('/search')
            else:
                return '<h1>Invalid password</h1>' 
        return '<h1>This user does not exist.</h1>'

    return render_template('login.html', form=form)
    
@app.route('/search',  methods=['GET', 'POST'])
@login_required
def search():
    form = SearchForm()
    return render_template('search.html', name=current_user.firstName, form=form)

@app.route('/search/result',  methods=['GET','POST'])
@login_required
def result():
    pagesize = 3
    if request.method == 'GET':
        form_ = int(request.args.get('from_'))

        from_ = max(form_,0)
        keyword = request.args.get('searchval')
        result = es.search(index="calendar",size=pagesize,from_ = from_, body={"query": {"multi_match" : { "query": keyword, "fields": ["eventname", "time", "note", "createdBy","createdDate"] }}})
        if int(result['hits']['total']) <=  from_ :
            from_ -= pagesize
        return render_template('result.html',name=current_user.firstName, searchval=keyword, result = result,from_ = from_, pagesize = pagesize)
        
    form = SearchForm()
    if form.validate_on_submit():
        keyword = form.keyword.data
        result = es.search(index="calendar",size=pagesize,from_ = 0, body={"query": {"multi_match" : { "query": keyword, "fields": ["eventname", "time", "note", "createdBy","createdDate"] }}})
        return render_template('result.html',name=current_user.firstName, searchval=keyword, result = result,from_ = 0, pagesize = pagesize)
    return render_template('search.html', name=current_user.firstName, form=form)
@app.route('/search/result/calendar',  methods=['GET'])
@login_required
def calendar():
    id = request.args.get('id')
    doc = mongo.db.calendar.find_one({'_id':id})
    return render_template('calendar.html', name=current_user.firstName, doc=doc)
    
@app.route('/add',  methods=['GET', 'POST'])
@login_required
def add():
    form = CalendarForm()

    if form.validate_on_submit():
        calendar = mongo.db.calendar
        post = {"_id": str(calendar.count()+1),
                "eventname": form.eventname.data,
                "time": str(form.time.data),
                "note": form.note.data,
                "createdBy":current_user.username,
                "createdDate": str(datetime.datetime.utcnow())}
        
        post_id = calendar.insert(post)
        del post['_id']
        esdata = JSONEncoder().encode(post)
        es.index(index="calendar", doc_type='general', id = post_id, body=json.loads(esdata))

        return redirect('/search')
       
    return render_template('add.html', name=current_user.firstName, form=form)
    
@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))
    
if __name__ == "__main__":

    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 5000)))
