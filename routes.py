from flask import Flask, request, render_template, redirect, url_for, session
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, SubmitField
from flask_bootstrap import Bootstrap
from sys import exit
from os import environ
from subprocess import check_output, run
from string import ascii_uppercase as letters
from random import choice
from tabulate import tabulate
import sqlite3


def get_random_string(n):
    return ''.join(choice(letters) for i in range(n))

DB_NAME = "./db.sqlite"
TUTORIAL_DB_NAME = "./animals.sqlite"

app = Flask(__name__)
Bootstrap(app)
app.config["SECRET_KEY"] = environ.get('SECRET_KEY') or get_random_string(32)
app.config["WTF_CSRF_ENABLED"] = False

class BashForm(FlaskForm):
    command = StringField('Command')
    submit = SubmitField("Run Command")

class SqlForm(FlaskForm):
    query = StringField('Query')
    submit = SubmitField("Execute query")

class TestForm(FlaskForm):
    address = StringField('IP Address or Domain Name')
    submit = SubmitField('Perform Test')

class LogHistory(FlaskForm):
    file = SubmitField('login_history.log')

class LogCalls(FlaskForm):
    file = SubmitField('call_history.log')

class LoginForm(FlaskForm):
    username = StringField('Username')
    password = PasswordField('Password')
    submit = SubmitField('Sign In')

@app.route('/')
def root():
    print("[+] Executing root route")
    message = "Please login to continue"
    return render_template("./index.j2", message=message, form=LoginForm())

@app.route('/login', methods=["POST"])
def login():
    print(f"[+] Executing login route")
    user = request.form.get("username")
    password = request.form.get("password")
    sql_stmt = f"SELECT * FROM Users WHERE username='{user}' and password='{password}'"
    print(f"[+] Executing SQL Statement:\n\t{sql_stmt}")
    
    with sqlite3.connect(DB_NAME) as db:
        c = db.cursor()
        c.execute(sql_stmt)
        row = c.fetchone()
        if row:
            print(f"[+] Logged in as {row[0]} succesefully!")
            session['username'] = row[0]
            return redirect(url_for("control_panel"))
        else:
            print(f"[!] Login failed!")

    message = "Login failed, please try again"
    return render_template("./index.j2", message=message, form=LoginForm())

@app.route('/control_panel')
def control_panel():
    print(f"[+] Executing control_panel route")
    if 'username' in session and session['username'] == 'Admin':
        return render_template("control_panel.j2",
                username=session['username'],
                testForm=TestForm(),
                logHistory=LogHistory(),
                logCalls=LogCalls())
    else:
        print(f"[!] User is not logged in, redirecting...")
        return redirect(url_for("root"))

@app.route('/do_test')
def do_test():
    print(f"[+] Executing do_test route")
    if 'username' in session and session['username'] == 'Admin':
        command_string = f"ping -c 1 -t 100 {request.args.get('address')}"
        try:
            command_output = check_output([command_string], shell=True).decode().strip()
        except Exception:
            command_output = f"Failed to execute {command_string}"
        return render_template("control_panel.j2",
                username=session['username'],
                testForm=TestForm(),
                logHistory=LogHistory(),
                logCalls=LogCalls(),
                command_output=command_output)
    else:
        print(f"[!] User is not logged in, redirecting...")
        return redirect(url_for("root"))

@app.route('/get_file')
def get_file():
    print(f"[+] Executing get_file route")
    if 'username' in session and session['username'] == 'Admin':
        file_name = request.args.get('file')
        print(f"[+] Opening {file_name}")
        try:
            with open(file_name) as f:
                data = f.read()
            print("[+] File read successeful!")
        except Exception:
            print(f"[!] failed to open {file_name}")
            data = f"Couldn't open file {file_name}"
        return render_template("control_panel.j2",
                username=session['username'],
                testForm=TestForm(),
                logHistory=LogHistory(),
                logCalls=LogCalls(),
                file_data=data)
    else:
        print(f"[!] User is not logged in, redirecting...")
        return redirect(url_for("root"))

@app.route('/learn_sql')
def learn_sql():
    if "sql_output" in session:
        sql_output = session["sql_output"]
        del session["sql_output"]
    else:
        sql_output = None
    with sqlite3.connect(TUTORIAL_DB_NAME) as db:
        try:
            c = db.cursor()
            c.execute("SELECT * FROM Animals")
            rows = c.fetchall()
            headers = [x[0] for x in c.description]
            table = tabulate(rows, headers, tablefmt="psql")
        except Exception as e:
            print(f"[!] Someone broke the database...{e}")
            table = f"[!]Table is broken:\n{e}"
    return render_template("learn_sql.j2",
            sqlForm=SqlForm(),
            table=table,
            sql_output=sql_output)

@app.route("/execute_sql", methods=["POST"])
def run_sql():
    with sqlite3.connect(TUTORIAL_DB_NAME) as db:
        try:
            c = db.cursor()
            c.execute(request.form.get("query"))
            rows = c.fetchall()
            rows = '\n'.join([str(x) for x in rows])
        except Exception as e:
            rows = e
        session["sql_output"] = rows
    return redirect(url_for("learn_sql"))

@app.route('/learn_bash')
def learn_bash():
    if "bash_output" in session:
        bash_output = session["bash_output"]
        del session["bash_output"]
    else:
        bash_output = None
    return render_template("learn_bash.j2",
            bashForm=BashForm(),
            bash_output=bash_output)

@app.route('/run_bash_command', methods=["POST"])
def run_bash():
        try:
            completed_process = run([request.form.get("command")], shell=True, capture_output=True)
            command_output = completed_process.stdout.decode()
            command_output += completed_process.stderr.decode()
        except Exception as e:
            command_output = f"Failed to execute {request.form.get('command')}\n{e}"
        session['bash_output'] = command_output
        return redirect(url_for("learn_bash"))

def setup_db():
    try:
        password = get_random_string(32)
        db = sqlite3.connect(DB_NAME)
        cursor = db.cursor()
        try:
            cursor.execute("DROP TABLE Users")
            db.commit()
        except Exception as e:
            print("[+] Looks like this is a first run :)")
        cursor.execute("CREATE TABLE Users (username text, password text)")
        cursor.execute(f"INSERT INTO Users VALUES ('Admin', '{password}')")
        db.commit()
    except Exception as e:
        print(f"Failed to setup database...\n{e}")
        exit(-1)


def setup_test_db():
    try:
        db = sqlite3.connect(TUTORIAL_DB_NAME)
        cursor = db.cursor()
        try:
            cursor.execute("DROP TABLE Animals")
            db.commit()
        except Exception as e:
            pass
        cursor.execute("CREATE TABLE Animals (name text, legs int, class text)")
        cursor.execute("INSERT INTO Animals VALUES ('Dog', 4, 'Mammal')")
        cursor.execute("INSERT INTO Animals VALUES ('Spider', 8, 'Arachnid')")
        cursor.execute("INSERT INTO Animals VALUES ('Snake', 0, 'Reptile')")
        cursor.execute("INSERT INTO Animals VALUES ('Gorilla', 2, 'Mammal')")
        cursor.execute("INSERT INTO Animals VALUES ('Robin', 2, 'Reptile')")
        db.commit()
    except Exception as e:
        print(f"Failed to setup database...\n{e}")
        exit(-1)


if __name__ == "__main__":
    setup_db()
    setup_test_db()
    app.run(debug=True, host="0.0.0.0")
