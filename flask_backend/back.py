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


