import os
import psycopg2
import logging
import requests
import time
import json
import urlparse

from bs4 import BeautifulSoup
from datetime import datetime
from flask import Flask, render_template
from flask import request
from logging.handlers import RotatingFileHandler
from urllib import urlretrieve
from youtube_dl import YoutubeDL
from flask import Flask, session, redirect, url_for, escape, request, flash, jsonify

# All database stuff related to connection with heroku
url = urlparse.urlparse(os.environ.get('DATABASE_URL'))
db = "dbname=%s user=%s password=%s host=%s " % (url.path[1:], url.username, url.password, url.hostname)
schema = "schema.sql"
conn = psycopg2.connect(db)
cur = conn.cursor()

app = Flask(__name__)
app.config['SECRET_KEY'] = 'SECRET KEY'; # Type your secret key here


# All website directories
@app.route('/', methods = ['POST', 'GET'])
def home():
    ''' Home page of Mythical page '''

    if request.method == "POST":
        the_time = datetime.now().strftime("%A, %d %b %Y")
        name = request.form['name']
        text = request.form['text'] + '  '+the_time

        statement = "insert into salesforce.case(casenumber, description) values ('" \
            + name + "','" + text + "');"
        cur.execute(statement)
        conn.commit()

    cur.execute("""SELECT subject from salesforce.case where suppliedname = 'views' """)
    rows = cur.fetchall()
    count = str(int(rows[0][0])+1)
    statement = "update salesforce.case set subject = "+count+" where suppliedname = 'views'"
    cur.execute(statement)
    conn.commit()

    cur.execute("""SELECT casenumber, description from salesforce.case""")
    desc = cur.fetchall()
    my_list = []
    for data in range(len(desc)-2,-1,-1):
        my_list.append(desc[data])

    if 'username' in session:
        session['logged_in'] = True
        status = 'Logged in'
    else:
        session['logged_in'] = False
        status = 'Not logged in'
    return render_template('home.html', status = status, views = count, message = my_list)


@app.route('/doform')
def contactform():
    ''' Contact form to show form '''

    return render_template('doform.html')

@app.route('/todo', methods=['POST','GET'])
def toDoList():
    ''' To get all To-Do list task in one place '''
    if session['logged_in']:
        user = session['username']
    else:
        user = 'anonymous'
    the_time = datetime.now().strftime("%A, %d %b %Y %l:%M %p")
    try:
        if request.method == "POST":
            name = request.form["name"]
            priority = request.form["quality"]
            description = request.form["description"]+' '+the_time

            app.logger.info(name)
            statement = "insert into salesforce.contact(name, description, title, firstname) values ('" \
                + name + "','" + description + "','" + priority + "','" + user + "');"
            cur.execute(statement)
            conn.commit()
            errors = []
    except Exception as e:
        print(e)
        return []

    try:
        cur.execute("""SELECT name, description, title, firstname from salesforce.contact where firstname = """ +"'"+user+"'")
        rows = cur.fetchall()
        response = ''
        my_list = []
        x = 1
        for row in range(len(rows)-1,-1,-1):
            rows[row] = list(rows[row])
            rows[row].append(str(x))
            my_list.append(rows[row])
            x+=1

        return render_template('todo_list.html',  results=my_list)
    except Exception as e:
        print(e)
        return []

@app.route('/instagram')
def instagram():
    return render_template('instagram.html')

@app.route('/instagram_result', methods=['POST','GET'])
def instagram_result():
    try:
        if request.method == "POST":
            user = request.form["username"]
            try:
                qual = request.form["quality"]
            except:
                qual = 'HQ'
            r = requests.get('https://www.instagram.com/'+str(user))
            soup = BeautifulSoup(r.content)
            try:
                ss = 0
                l = soup.find_all('script')
                for i in l:
                    if i.text[:18] == 'window._sharedData':
                        break
                    else:
                        ss+=1
                l = soup.find_all('script')[ss].text
            except:
                return('Oh crap! Something is wrong.  Contact shashank.sharma98@gmail.com')
            jsonValue = '{%s}' % (l.split('{',1)[1].rsplit('}',1)[0],)
            value = json.loads(jsonValue)
            count = value['entry_data']['ProfilePage'][0]['user']['media']['count']
            user_id = str(value['entry_data']['ProfilePage'][ 0 ]['user']['username'])

            data = value['entry_data']['ProfilePage'][0]['user']['media']['nodes']
            page = value['entry_data']['ProfilePage'][0]['user']['media']['page_info']['has_next_page']
            if str(qual) == 'LQ':
                quality = 'thumbnail_src'
            else:
                quality = 'display_src'
            a = []
            st = ""
            start = 1
            logo = 'lock_open'

            for i in range(len(data)):
                link = str(data[i][quality])
                a.append(link)
                #st = st+'<img src = "'+link+'"> '
            if len(a) == 0:
                total = 'Seems like Account is Private'
                logo = 'lock'
            return render_template('instagram_result.html',  results=a, total=len(a), user = user, logo=logo)
    except:
        return('Wrong')

@app.route('/youtube')
def youtube():
    return render_template('youtube.html')

@app.route('/youtube-result', methods=['POST','GET'])
def youtubeDownload():
    try:
        if request.method == "POST":
            urlAddress = request.form["url"]
            urlData = ytDownload(urlAddress)

            urlDataPer = []
            urlExtract= []
            for i in urlData['formats']:
                urlDataPer.append(str(i['url']))
                urlDataPer.append(str(i['format'].split('-')[1]))
                urlDataPer.append(str(i['ext']))
                try:
                    urlDataPer.append(str(((int(i['filesize'])/1024)/1024))+' MB')
                except:
                    urlDataPer.append('? MB')
                urlExtract.append(urlDataPer)
                urlDataPer = []

            urlDuration = str(int(urlData['duration'])/60)+ ':' + str(int(urlData['duration'])%60)
            urlImage = urlData['thumbnail']
            urlTitle = urlData['title']
            return render_template('youtube-result.html', urlData = urlExtract, urlDuration = urlDuration, urlImage = urlImage, urlTitle = urlTitle, url = str(urlData['url']))
    except:
        return

@app.route('/signup', methods=['POST', 'GET'])
def signUp():
    try:
        if request.method == "POST":
            name = request.form["name"].lower()
            email = request.form["mail"]
            password = request.form["password"]
            error = 'none'


            cur.execute("""SELECT name, accountnumber, description from salesforce.account""")
            rows = cur.fetchall()
            for row in rows:
                if str(name) == str(row[0]):
                    error = 'block'
                    message = 'Username'
                    return render_template('signup.html', error = error, message = message)
                if str(email) == str(row[1]):
                    error = 'block'
                    message = 'Email'
                    return render_template('signup.html', error = error, message = message)

            app.logger.info(name)
            statement = "insert into salesforce.account(name, accountnumber, description) values ('" \
                + name + "','" + email + "','" + password + "');"
            cur.execute(statement)
            conn.commit()
            status = 'block'
            return render_template('login.html', status = status, error = 'none')

        else:
            error = 'none'
            message = ''
            return render_template('signup.html', error = error, message = message)
    except Exception as e:
        print(e)
        return []

@app.route('/login', methods=['POST', 'GET'])
def login():
    if session['logged_in'] == True:
        return render_template("home.html", status = 'Already Logged in')

    try:
        if request.method == "POST":
            name = request.form["name"].lower()
            password = request.form["password"]

            cur.execute("""SELECT name, description from salesforce.account""")
            rows = cur.fetchall()

            for row in rows:
                if str(name) == str(row[0]):
                    print str(password), str(row[1])
                    if str(password) == str(row[1]):
                        session['username'] = name
                        session['logged_in'] = True
                        return render_template('home.html', status = 'Successfully Logged in')

            return render_template('login.html', error = 'block', status = 'none')

        else:
            error = 'none'
            status = 'none'
            return render_template('login.html', error = error, status = status)
    except Exception as e:
        print(e)
        return []

@app.route('/profile', methods=['POST', 'GET'])
def profile():
    if session['logged_in'] == True:
        if request.method == "POST":
            delete = request.form["delete"]
            statement = "delete from salesforce.contact where description = '"+str(delete)+"'"
            cur.execute(statement)
            conn.commit()

        user = session['username']

        cur.execute("""SELECT name, accountnumber from salesforce.account where name = '"""+ str(session['username'])+"'")
        account = cur.fetchall()
        cur.execute("""SELECT name, description, title from salesforce.contact where firstname = """ +"'"+user+"'")
        rows = cur.fetchall()
        my_list = []
        x = 1
        for row in range(len(rows)-1,-1,-1):
            rows[row] = list(rows[row])
            rows[row].append(str(x))
            my_list.append(rows[row])
            x+=1

        total_do = len(my_list)

        return render_template('profile.html', user = user, results = my_list, username = account[0][0], email = account[0][1], count = total_do)
    else:
        print 'I failed'
        return render_template('login.html', dialog = "Materialize.toast('Please log in to continue', 6000)")

@app.route('/logout')
def logout():
    session.pop('username', None)
    session['logged_in'] = False
    return render_template("home.html", status = 'Successfully Logged out')


@app.route("/settings", methods = ["POST", "GET"])
def settings():
    if request.method == "POST" and session['logged_in']:
        name = session['username']
        password = request.form['password']
        statement = "update salesforce.account set description = '"+str(password)+"' where name = '"+name+"'"
        cur.execute(statement)
        conn.commit()
        dialog = "Materialize.toast('Password changed', 6000)"
    else:
        dialog = "Materialize.toast('Type your password', 6000)"
    return render_template("settings.html", dialog = dialog)

def ytDownload(link):
    ydl = YoutubeDL()
    r = ydl.extract_info(link, download=False)
    return(r)

if __name__ == '__main__':
    handler = RotatingFileHandler('foo.log', maxBytes=10000, backupCount=10)
    handler.setLevel(logging.INFO)
    app.logger.addHandler(handler)
    app.run()
