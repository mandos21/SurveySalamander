from flask import Flask,request
import MySQLdb
import configparser
import json

app = Flask(__name__)
config= configparser.ConfigParser()
config.read('/.config.ini')

hostname = config.get('config','hostname')
username = config.get('config','username')
database = config.get('config','database')
password = config.get('config','password')

conn = MySQLdb.connect( host=hostname, user=username, passwd=password, db=database)


def gen_query_string(arglist, table, where, whereval):
    exstring = " select "
    for item in arglist:
        exstring += item + ", "
    exstring = exstring[:-2]
    exstring += " from " + table + " where " + where + " = " + str(whereval)
    return exstring

def execute_query(sql):
    curr = conn.cursor()
    try:
        curr.execute(sql)
    except MySQLdb.Error as e:
        return "An error has occured ", e
        conn.rollback()
    else:
        conn.commit()
        return "operation completed"

# Get all answers for a given question
def getanswersbyquestion(question):
    cur = conn.cursor()
    answer = []
    
    arglist = ['answer','answer_id','question_id','user_id']
    table = "answers"
    where = "question_id"
    whereval = question

    cur.execute(gen_query_string(arglist,table,where,whereval))
    for val_list in cur.fetchall():
        answer.append(dict(zip(arglist,val_list)))
    return json.dumps(answer)



# Get all questions for a given survey
def getquestionsbysurvey(survey):
    cur = conn.cursor()
    answer = []

    arglist = ['question_id','question','user_id','survey_id']
    table = "questions"
    where = "survey_id"
    whereval = survey

    cur.execute(gen_query_string(arglist,table,where,whereval))
    for val_list in cur.fetchall():
        answer.append(dict(zip(arglist,val_list)))
    return json.dumps(answer)




# Return all questions for a given survey
@app.route("/qbys")
def survey_questions_endpoint():
    return getquestionsbysurvey(request.args['survey_id'])
