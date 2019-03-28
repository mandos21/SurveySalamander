import configparser
import json
import os
import MySQLdb
from sqlalchemy.sql import func
from flask import Flask, jsonify, request, send_from_directory, redirect, render_template
from flask_marshmallow import Marshmallow
from flask_sqlalchemy import SQLAlchemy
from flask_uploads import IMAGES, UploadSet, configure_uploads
from passlib.apps import custom_app_context as pwd_context


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
class Question(db.Model):
    __tablename__ = 'questions'
    questionid = db.Column('question_id', db.Integer, primary_key=True)
    question = db.Column('question', db.String(2000), default=0)
    userid = db.Column('user_id', db.Integer)
    surveyid = db.Column('survey_id',db.Integer)
    questionnum = db.Column('question_num',db.Integer)


    def __init__(self, question, userid, surveyid):
        self.question = question
        self.userid = userid
        self.surveyid = surveyid
        self.questionnum = questionnum


class Survey(db.Model):
    __tablename__ = 'survey'
    surveyid = db.Column('survey_id', db.Integer, primary_key=True)
    userid = db.Column('user_id', db.Integer)
    surveyname = db.Column('survey_name', db.String(100))
    description = db.Column('description', db.String(300))



    def __init__(self, userid, surveyname):
        self.userid = userid
        self.surveyname = surveyname
        self.description = description


class User(db.Model):
    __tablename__ = 'users'
    userid = db.Column('user_id', db.Integer, primary_key=True)
    emailaddress = db.Column('email_address',db.String(60))
    password = db.Column('password',db.String(60))

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
        fields = ('surveyid','userid','survey_name','description')

class UserSchema(ma.Schema):
    class Meta:
        fields = ('userid','emailaddress','password')

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

# Verify Logon
@app.route('/login', methods=['POST'])
def login():
    email = request.form['email']
    passw = request.form['pass']
    if(email_in_db(email)):
        user = User.query.filter(User.emailaddress == email).first()
        surveys = Survey.query.filter(Survey.userid == user.userid)
        print("***********************ASS************")
        print(surveys)
        if(pwd_context.verify(passw, user.password)):
            data = [{'userid':user.userid,'email':user.emailaddress},surveys]
            return render_template('index.html', data = data )
        else:
            return redirect('https://www.degenaro.tk/Survey/login/badlogin.html')
    else:
        return redirect('https://www.degenaro.tk/Survey/signup/index.html')

# Add Question 
@app.route('/addquestion', methods=['POST'])
def add_question():
    userid = request.json['userid']
    question = request.json['question']
    surveyid = request.json['surveyid']
    new_question = Question(question, userid, surveyid)
    db.session.add(new_question)
    db.session.commit()
    return question_schema.jsonify(new_question)

# Add Survey
@app.route('/addsurvey', methods=['POST'])
def add_survey():
    userid = request.json['urlinfo']
    new_survey = Question(urlinfo)
    db.session.add(new_survey)
    db.session.commit()
    return survey_schema.jsonify(new_survey)

@app.route('/adduser', methods=['POST'])
def add_user():
    emailaddress = request.form['email']
    password = request.form['pass']
    rpassword = request.form['repeat-pass']
    if rpassword != password:
        return redirect('https://www.degenaro.tk/Survey/login/index.html')
    hashword = pwd_context.hash(password)
    new_user = User(emailaddress, hashword)
    db.session.add(new_user)
    db.session.commit()
    user_schema.jsonify(new_user)

    surveys = Survey.query.filter(Survey.userid == new_user.userid)
    data = [{'userid':new_user.userid,'email':emailaddress},surveys]
    return render_template('/index.html', data = data)

@app.route('/addanswer', methods=['POST'])
def add_answer():
    userid = request.json['userid']
    quesitonid = request.json['questionid']
    surveyid = request.json['surveyid']
    new_answer = Answer(userid, questionid, surveyid)
    db.session.add(new_answer)
    db.session.commit()
    return answer_schema.jsonify(new_answer)

@app.route('/qredirect/<surveyid>', methods=['GET'])
def qredirect(surveyid):
    survey = Survey.query.filter(Survey.surveyid == surveyid).first()
    user = User.query.filter(User.userid == survey.userid).first() 
    questions = Question.query.filter(Question.surveyid == surveyid)
    data = [user,survey,questions]
    return render_template('questionview.html', data = data)

@app.route('/qedit/<questionid>', methods=['GET'])
def qedit(questionid):
    question = Question.query.filter(Question.questionid == questionid).first()    
    user = User.query.filter(User.userid == question.userid).first()
    data = [user,question]
    return render_template('qedit.html',data = data)


# Get all users
@app.route('/users', methods = ['GET'])
def get_users():
    all_users = User.query.all()
    print(all_users)
    results = users_schema.dump(all_users)
    return jsonify(results.data)


# Get users by email
def email_in_db(email):
    emails = User.query.filter(User.emailaddress == email)
    emailr = users_schema.dump(emails)
    print(str(emailr.data))
    return not (str(emailr.data) == '[]')


# Get surveys by user id
@app.route('/surveysbyuserid/<userid>', methods = ['GET'])
def get_surveysbyid(userid):
    survey = Survey.query.filter(Survey.userid == userid)
    results = surveys_schema.dump(surveys)
    return survey_schema.jsonify(survey)

# Get questions by surveyid
@app.route('/questionsbyid/<surveyid>', methods = ['GET'])
def get_questiondsbyid(surveyid):
    questions = Question.query.filter(Question.surveyid == surveyid)
    results = listings_schema.dump(questions)
    return jsonify(results.data)

# Get answers by questionid
@app.route('/answersbyid/<questionid>', methods = ['GET'])
def get_answerssbyid(questionid):
    answers = Answer.query.filter(Answer.questionid == questionid)
    results = listings_schema.dump(answers)
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
