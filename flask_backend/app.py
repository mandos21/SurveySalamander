import configparser
import json
import os
import MySQLdb
from sqlalchemy.sql import func
from flask import Flask, jsonify, request, send_from_directory
from flask_marshmallow import Marshmallow
from flask_sqlalchemy import SQLAlchemy
from flask_uploads import IMAGES, UploadSet, configure_uploads


app = Flask(__name__, root_path='/usr/share/webapps/Survey/flask_backend')

#Configure image uploading
UPLOAD_FOLDER = os.path.basename('images')
photos = UploadSet('photos', IMAGES)
app.config['UPLOADED_PHOTOS_DEST'] = UPLOAD_FOLDER
configure_uploads(app, photos)

# app.debug = True
config=configparser.ConfigParser()
config.read('./config.ini')
hostname = config.get('config','hostname')
username = config.get('config','username')
database = config.get('config','database')
password = config.get('config','password')

#SQL-Alchemy settings
app.config['SQLALCHEMY_DATABASE_URI'] = f'mysql://{username}:{password}@{hostname}/{database}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Init DB
db = SQLAlchemy(app)

# Init marshmallow
ma = Marshmallow(app)

## SQLAlchemy DB classes(map db tables to python objects)
#TODO implement tables for Users and Ratings
class Question(db.Model):
    __tablename__ = 'questions'
    questionid = db.Column('question_id', db.Integer, primary_key=True)
    question = db.Column('question', db.String(2000), default=0)
    userid = db.Column('user_id', db.Integer)
    surveyid = db.Column('survey_id',db.Integer)


    def __init__(self, question, userid, surveyid):
        self.question = question
        self.userid = userid
        self.sruveyid = surveyid


class Survey(db.Model):
    __tablename__ = 'survey'
    surveyid = db.Column('survey_id', db.Integer, primary_key=True)
    urlinfo = db.Column('urlinfo', db.String(45))


    def __init__(self, urlinfo):
        self.urlinfo = urlinfo


class User(db.Model):
    __tablename__ = 'users'
    userid = db.Column('users_id', db.Integer, primary_key=True)
    emailaddress = db.Column('email_address',db.String(60))
    password = db.column('password',db.String(60))

    def __init__(self, emailaddress, password):
        self.password = password
        self.emailaddress = emailaddress

class Answer(db.Model):
    __tablename__ = 'answers'
    answerid = db.Column('ansewr_id', db.Integer, primary_key=True)
    userid = db.Column('user_id', db.Integer)
    questionid = db.Column('questionid', db.Integer)
    answer = db.Column('answer',db.String(2000))

    def __init__(self, userid, questionid,answer):
        self.userid = userid
        self.questionid = questionid
        self.answer = answer


# Listing shcemas (what fields to serve when pulling from database)
class QuestionSchema(ma.Schema):
    class Meta:
        fields = ('questionid','question','userid','surveyid')

class SurveySchema(ma.Schema):
    class Meta:
        fields = ('surveyid','urlinfo')

class UserSchema(ma.Schema):
    class Meta:
        fileds = ('userid','emailaddress','password')

class AnswerSchema(ma.Schema):
    class Meta:
        fields = ('answerid','userid','questionid','answer')


# Init Schema
question_schema = QuestionSchema(strict = True)
questions_schema = QuestionSchema(many = True, strict = True)

survey_schema = SurveySchema(strict=True)
surveys_schema = SurveySchema(many = True, strict = True)

user_schema = UserSchema(strict = True)
users_schema = UserSchema(many = True, strict = True)

answer_schema  = AnswerSchema(strict = True)
answers_scheme = AnswerSchema(many = True, strict = True)


## APP ENDPOINTS:

# Add Question 
@app.route('/addquestion', methods=['POST'])
def add_question():
    userid = request.json['userid']
    question = request.json['question']
    surveyid = request.json['surveyid']
    new_question = Question(question, userid, surveyid)
    db.session.add(new_question)
    db.session.commit()
    return listing_schema.jsonify(new_question)

# Add Survey
@app.route('/addsurvey', methods=['POST'])
def add_survey():
    userid = request.json['urlinfo']
    new_survey = Question(urlinfo)
    db.session.add(new_survey)
    db.session.commit()
    return listing_schema.jsonify(new_survey)

@app.route('/adduser', methods=['POST'])
def add_user():
    emailaddress = request.json['emailaddress']
    password = request.json['password']
    new_user = User(emailaddress, password)
    db.session.add(new_user)
    db.session.commit()
    return listing_schema.jsonify(new_user)

@app.route('/addanswer', methods=['POST'])
def add_answer():
    userid = request.json['userid']
    quesitonid = request.json['questionid']
    surveyid = request.json['surveyid']
    new_answer = Answer(userid, questionid, surveyid)
    db.session.add(new_answer)
    db.session.commit()
    return listing_schema.jsonify(new_answer)




#Upload image
@app.route('/uploads/<listingid>/<index>', methods = ['POST'])
def upload_image(listingid,index):
    photo = photos.save(request.files['photo'])
    imagename = os.path.basename(photo)
    new_image = Images(imagename,listingid,index)
    db.session.add(new_image)
    db.session.commit()
    return imagename

# Get image from listing
@app.route('/images/<listingid>/<index>', methods = ['GET'])
def get_image(listingid,index):
    photo = Images.query.filter(Images.listingid == listingid and Images.index == index).first()
    return send_from_directory(UPLOAD_FOLDER,photo.name)

# Return next available listing id 
@app.route('/getnextid/', methods = ['GET'])
def get_next_id():
    nextid = db.session.query(func.max(Listing.listingid)).scalar() + 1
    return f'{nextid}'

# Get all listings
@app.route('/listings', methods = ['GET'])
def get_listings():
    all_listings = Listing.query.all()
    results = listings_schema.dump(all_listings)
    return jsonify(results.data)

# Get listing by id
@app.route('/listingbyid/<listingid>', methods = ['GET'])
def get_listingbyid(listingid):
    listing = Listing.query.get(listingid)
    return listing_schema.jsonify(listing)

# Get listings by zipcode
@app.route('/listingsbyzip/<zipcode>', methods = ['GET'])
def get_listingsbyzip(zipcode):
    listings = Listing.query.filter(Listing.zipcode == zipcode)
    results = listings_schema.dump(listings)
    return jsonify(results.data)

# Increment/Update listing views
@app.route('/incrementview/<listingid>', methods = ['PUT'])
def incrementview(listingid):
    listing = Listing.query.get(listingid)
    listing.views += 1
    db.session.commit()
    return listing_schema.jsonify(listing)

# Get listings by tag
@app.route('/listingsbytag/<tag>', methods = ['GET'])
def get_listingsbytag(tag):
    listings = Listing.query.filter(Listing.tag == tag)
    results = listings_schema.dump(listings)
    return jsonify(results.data)

# Delete listing
@app.route('/deletelisting/<listingid>', methods = ['GET'])
def deletelisting(listingid):
    listing = Listing.query.get(listingid)
    db.session.delete(listing)
    db.session.commit()
    return "Operation successful"

# The hello world endpoint
@app.route("/hello")
def hello_endpoint():
    return "Hello world!"

if __name__ == "__main__":
    # app.run()
    app.run(host='0.0.0.0', port=5000,ssl_context=('../certs/fullchain.pem','../certs/privkey.pem'))
