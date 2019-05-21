import random
import string
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
    questiontype = db.Column('question_type',db.String(1))


    def __init__(self, question, userid, surveyid, questionnum, questiontype):
        self.question = question
        self.userid = userid
        self.surveyid = surveyid
        self.questionnum = questionnum
        self.questiontype = questiontype

# Object definition of Survey Table
class Survey(db.Model):
    __tablename__ = 'survey'
    surveyid = db.Column('survey_id', db.Integer, primary_key=True)
    userid = db.Column('user_id', db.Integer)
    surveyname = db.Column('survey_name', db.String(100))
    description = db.Column('description', db.String(300))
    public = db.Column('public', db.Integer)
    privcode = db.Column('privcode', db.String(10))
    questions = db.Column('questions', db.Integer)


    def __init__(self, userid, surveyname, description, public,questions):
        self.userid = userid
        self.surveyname = surveyname
        self.description = description
        self.public = public
        self.questions = questions

# Object definition of User table
class User(db.Model):
    __tablename__ = 'users'
    userid = db.Column('user_id', db.Integer, primary_key=True)
    emailaddress = db.Column('email_address',db.String(60))
    password = db.Column('password',db.String(60))

    def __init__(self, emailaddress, password):
        self.password = password
        self.emailaddress = emailaddress

# Object definition of Answer table
class Answer(db.Model):
    __tablename__ = 'answers'
    answerid = db.Column('answer_id', db.Integer, primary_key=True)
    userid = db.Column('user_id', db.Integer)
    questionid = db.Column('question_id', db.Integer)
    answer = db.Column('answer',db.String(2000))

    def __init__(self, questionid,answer):
        self.questionid = questionid
        self.answer = answer


# Listing shcemas (what fields to serve when pulling from database)
class QuestionSchema(ma.Schema):
    class Meta:
        fields = ('questionid','question','userid','surveyid','questionnum','questiontype')
class SurveySchema(ma.Schema):
    class Meta:
        fields = ('surveyid','userid','survey_name','description','questions')

class UserSchema(ma.Schema):
    class Meta:
        fields = ('userid','emailaddress','password')

class AnswerSchema(ma.Schema):
    class Meta:
        fields = ('answerid','userid','questionid','answer')


# Init Schemas
question_schema = QuestionSchema(strict = True)
questions_schema = QuestionSchema(many = True, strict = True)

survey_schema = SurveySchema(strict=True)
surveys_schema = SurveySchema(many = True, strict = True)

user_schema = UserSchema(strict = True)
users_schema = UserSchema(many = True, strict = True)

answer_schema  = AnswerSchema(strict = True)
answers_schema = AnswerSchema(many = True, strict = True)


## APP ENDPOINTS:

# Verify Logon
@app.route('/login', methods=['POST'])
def login():
    email = request.form['email']
    passw = request.form['pass']
    if(email_in_db(email)):
        user = User.query.filter(User.emailaddress == email).first()
        surveys = Survey.query.filter(Survey.userid == user.userid)
        
        if(pwd_context.verify(passw, user.password)):
            data = [{'userid':user.userid,'email':user.emailaddress},surveys]
            #return render_template('index.html', data = data )
            return redirect('https://degenaro.tk:5000/home/' + str(user.userid))
        else:
            return redirect('https://www.degenaro.tk/Survey/login/badlogin.html')
    else:
        return redirect('https://www.degenaro.tk/Survey/signup/index.html')

# Add User
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
    return render_template('/home.html', data = data)



#
#     QUESTIONS
#


# Submit Question
@app.route('/qcreate',methods=['POST'])
def qcreate():
    question = request.form['question']
    questiontype = request.form['questiontype']
    questionnum = request.form['questionnum']
    surveyid = request.form['surveyid']
    userid = request.form['userid']

    survey = Survey.query.filter(Survey.surveyid == surveyid).first()
    user = User.query.filter(User.userid == userid).first()

    survey.questions = survey.questions + 1
    db.session.add(survey)
    db.session.commit()


    new_question = Question(question,userid,surveyid,questionnum,questiontype)
    db.session.add(new_question)
    db.session.commit()

    data = [user,survey]
    return render_template('qcreate.html',data = data)

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

# Redirect to question view from survey view
@app.route('/qredirect/<surveyid>', methods=['GET'])
def qredirect(surveyid):
    survey = Survey.query.filter(Survey.surveyid == surveyid).first()
    user = User.query.filter(User.userid == survey.userid).first() 
    questions = Question.query.filter(Question.surveyid == surveyid)
    data = [user,survey,questions]
    return render_template('questionview.html', data = data)

# Renders template for question editing page
@app.route('/qedit/<questionid>', methods=['GET'])
def qedit(questionid):
    question = Question.query.filter(Question.questionid == questionid).first()    
    user = User.query.filter(User.userid == question.userid).first()
    survey = Survey.query.filter(Survey.surveyid == question.surveyid).first()
    data = [user,survey,question]
    return render_template('qedit.html',data = data)

# Commit changes to database, redirect over to question view page
@app.route('/qeditconfirm', methods =['POST'])
def qeditconfirm():
    questiontext = request.form['question']
    questionid = request.form['questionid']
    question = Question.query.filter(Question.questionid == questionid).first()
    question.question = questiontext
    db.session.add(question)
    db.session.commit()

    user = User.query.filter(User.userid == question.userid).first()
    survey = Survey.query.filter(Survey.surveyid == question.surveyid).first()
    questions = Question.query.filter(Question.surveyid == survey.surveyid)
    data = [user,survey,questions]
    return render_template('questionview.html',data = data)

# Redirect to add a question to survey page
@app.route('/qaddredirect/<surveyid>', methods = ['GET'])
def qaddredirect(surveyid):
    survey = Survey.query.get(surveyid)
    user = User.query.filter(User.userid == survey.userid).first()

    data = [user,survey]
    debug(len(data))
    return render_template('qadd.html', data = data)

# Render Question Deletetion Confirmation Page
@app.route('/qdelete/<questionid>', methods = ['GET'])
def qdelete(questionid):
    question = Question.query.get(questionid)
    survey = Survey.query.get(question.surveyid) 
    user = User.query.filter(User.userid == survey.userid)

    data = [user,survey,question]
    return render_template('qdelete.html', data = data)

# Delete a question via post
@app.route('/qdeleteconfirm', methods = ['POST'])
def qdeleteconfirm():
    userid = request.form['userid']
    questionid = request.form['questionid']
    surveyid = request.form['surveyid']

    user = User.query.get(userid)
    question = Question.query.get(questionid)
    survey = Survey.query.get(surveyid)

    db.session.delete(question)
    db.session.commit()

    questions = Question.query.filter(Question.surveyid == survey.surveyid)
    data = [user, survey, questions]
    return render_template('questionview.html', data = data)


#
#     SURVEYS
#

# Create Survey
@app.route('/screate',methods=['POST'])
def screate():
    surveyname = request.form['surveyname']
    description = request.form['description']
    userid = request.form['userid']
    public = request.form['public']


    new_survey = Survey(userid,surveyname,description, public,0)

    if public == "0":
        privcode = genprivcode(10)
        new_survey.privcode = privcode

    db.session.add(new_survey)
    db.session.commit()

    user = User.query.filter(User.userid == userid).first()
    data = [user, new_survey]
    return render_template('qcreate.html', data = data)


# Renders template for Survey editing page
@app.route('/sedit/<userid>', methods=['GET'])
def sedit(userid):
    user = User.query.filter(User.userid == userid).first()
    data = [user]
    return render_template('sedit.html',data = data)

# Re-render the sedit template for previously created templates
@app.route('/salter/<surveyid>', methods=['GET'])
def salter(surveyid):
    survey = Survey.query.filter(Survey.surveyid == surveyid).first()
    user = User.query.filter(User.userid == survey.userid).first() 
    questions = Question.query.filter(Question.surveyid == surveyid)
    data = [user,survey,questions]
    return render_template('salter.html', data = data)


# Commit changes to database, redirect over to Survey view page
@app.route('/salterconfirm', methods =['POST'])
def salterconfirm():
    surveyname = request.form['surveyname']
    description = request.form['description']
    userid = request.form['userid']
    public = request.form['public']
    surveyid = request.form['surveyid']
    
    survey = Survey.query.filter(Survey.surveyid == surveyid).first()

    if survey.privcode == None and public == "0":
        privcode = genprivcode(10)
        survey.privcode = privcode


    survey.surveyname = surveyname
    survey.description = description
    survey.public = public

    db.session.add(survey)
    db.session.commit()

    user = User.query.filter(User.userid == userid).first()
    survey = Survey.query.filter(Survey.surveyid == surveyid).first()
    questions = Question.query.filter(Question.surveyid == surveyid)
    data = [user,survey,questions]
    return render_template('questionview.html',data = data)

    # Render Survey Deletetion Confirmation Page
@app.route('/sdelete/<surveyid>', methods = ['GET'])
def sdelete(surveyid):
    survey = Survey.query.get(surveyid)
    user = User.query.filter(User.userid == survey.userid)
    questions = Question.query.filter(Question.surveyid == surveyid)

    data = [user,survey,questions]
    
    return render_template('sdelete.html', data = data)

# Delete a survey via post
@app.route('/sdeleteconfirm', methods = ['POST'])
def sdeleteconfirm():
    userid = request.form['userid']
    surveyid = request.form['surveyid']

    user = User.query.get(userid)
    survey = Survey.query.get(surveyid)

    db.session.delete(survey)
    db.session.commit()
    debug(userid) 
    surveys = Survey.query.filter(Survey.userid == userid)
    data = [user, surveys]
    return render_template('index.html', data = data)



#
#   ANSWERS
#

# Redirect to answer page based on private code
@app.route('/privredirect', methods = ['POST'])
def privredirect():
    privcode = request.form['privcode']
    userid = request.form['userid']
    user = User.query.get(userid)
    survey = Survey.query.filter(Survey.privcode == privcode).first()
    questions = Question.query.filter(Question.surveyid == survey.surveyid)


    data = [user, survey, questions,0]
    return render_template('sanswer.html', data = data)


# Redirect to answer page from public survey
@app.route('/sredirect/<surveyid>/<userid>', methods = ['GET'])
def sredirect(surveyid,userid):
    survey = Survey.query.get(surveyid)
    user = User.query.get(userid)
    questions = Question.query.filter(Question.surveyid == survey.surveyid)


    data = [user, survey, questions,0]
    return render_template('sanswer.html', data = data)


# Redirect to answer page based on private code (public)
@app.route('/privredirectpub', methods = ['POST'])
def privredirectpub():
    privcode = request.form['privcode']
    survey = Survey.query.filter(Survey.privcode == privcode).first()
    questions = Question.query.filter(Question.surveyid == survey.surveyid)


    data = [0,survey, questions,0]
    return render_template('sanswer.html', data = data)


# Redirect to answer page from public survey (public)
@app.route('/sredirectpub/<surveyid>', methods = ['GET'])
def sredirectpub(surveyid):
    survey = Survey.query.get(surveyid)
    questions = Question.query.filter(Question.surveyid == survey.surveyid)


    data = [0,survey, questions,0]
    return render_template('sanswer.html', data = data)

# Accept submitted answers into the database
@app.route('/asubmit', methods = ['POST'])
def asubmit():
    surveyid = request.form['surveyid']
    qnum = request.form['qnum']
    userid = request.form['userid']

    user = User.query.get(userid)
    questions = Question.query.filter(Question.surveyid == surveyid)
    questionr = questions_schema.dump(questions)

    debug(qnum)
    for i,q in zip(range(0,int(qnum)),questionr[0]):
        answertext = request.form[str(i)]
        qid = q['questionid']
        answer = Answer(qid,answertext)
        db.session.add(answer)
        db.session.commit()
    
    surveys = Survey.query.filter(Survey.public == 1, Survey.questions != 0)
    data = [user, surveys]
    if userid != "":
        return render_template('answerhome.html', data = data)
    else:
        data=[surveys]
        return render_template('publicanswer.html', data = data)

# View Survey Answers
@app.route('/aview/<surveyid>', methods = ['GET'])
def aview(surveyid):
    survey = Survey.query.get(surveyid)
    user = User.query.filter(User.userid == survey.userid).first()
    questions = Question.query.filter(Question.surveyid == surveyid)
    qdata = []

    for q in questions_schema.dump(questions)[0]:
        qview = [Question.query.get(q['questionid'])]
        answers = Answer.query.filter(Answer.questionid == q['questionid'])
        adump = answers_schema.dump(answers)[0]
        alist = []
        for a in adump:
            if a not in (" ","  ",""):
                alist.append(Answer.query.get(a['answerid']))
        qdata.append([qview[0],alist])

    debug(qdata)
    data = [user,survey,qdata]
   
    return render_template('aview.html', data = data)

#
#     OTHER
#


# Get users by email
def email_in_db(email):
    emails = User.query.filter(User.emailaddress == email)
    emailr = users_schema.dump(emails)
    print(str(emailr.data))
    return not (str(emailr.data) == '[]')

# Redirect to Answerhome page for public users
@app.route('/pubanswerredirect', methods = ['GET'])
def pubanswerredirect():
    surveys = Survey.query.filter(Survey.public == 1, Survey.questions != 0)
    data = [surveys]
    return render_template('publicanswer.html', data = data)


# Redirect user to his Survey page based on userid
@app.route('/user/<userid>', methods = ['GET'])
def user_redirect(userid):
    user = User.query.filter(User.userid == userid).first()
    surveys = Survey.query.filter(Survey.userid == userid)
    data = [user,surveys]
    return render_template('index.html', data = data)

# Redirec to home page
@app.route('/home/<userid>', methods = ['GET'])
def home(userid):
    user = User.query.filter(User.userid == userid).first()
    data = [user]
    return render_template('home.html', data = data)

# Regenerate Sharing Key
@app.route('/privregen/<surveyid>', methods = ['GET'])
def privregen(surveyid):
    survey = Survey.query.get(surveyid)
    privcode = genprivcode(10)

    survey.privcode = privcode
    db.session.add(survey)
    db.session.commit()

    
    user = User.query.filter(User.userid == survey.userid).first()
    surveys = Survey.query.filter(Survey.userid == survey.userid)
    data = [user,surveys]
    return render_template('index.html', data = data)

# Redirect to Answer Home page
@app.route('/answerhome/<userid>', methods = ['GET'])
def answerhome(userid):
    user = User.query.get(userid)
    surveys = Survey.query.filter(Survey.public == 1, Survey.questions != 0)
    data = [user,surveys]
    return render_template('answerhome.html', data = data)



# The hello world endpoint
@app.route("/hello")
def hello_endpoint():
    return "Hello world!"


# For debugging purposes
def debug(item):
    print("*******************************************************************")
    print(item)
    print("*******************************************************************")

def genprivcode(length):
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=length))

if __name__ == "__main__":
    # app.run()
    app.run(host='0.0.0.0', port=5000,ssl_context=('../certs/fullchain.pem','../certs/privkey.pem'))
