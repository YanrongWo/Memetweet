import os
from sqlalchemy import *
from sqlalchemy.pool import NullPool
from flask import Flask, request, render_template, g, redirect, Response

tmpl_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'templates')
app = Flask(__name__, template_folder=tmpl_dir)

DATABASEURI = "postgresql://kah2204:998@w4111db1.cloudapp.net:5432/proj1part2"

engine = create_engine(DATABASEURI)

@app.before_request
def before_request():
  """
  This function is run at the beginning of every web request 
  (every time you enter an address in the web browser).
  We use it to setup a database connection that can be used throughout the request

  The variable g is globally accessible
  """
  try:
    g.conn = engine.connect()
  except:
    print "uh oh, problem connecting to database"
    import traceback; traceback.print_exc()
    g.conn = None

@app.teardown_request
def teardown_request(exception):
  """
  At the end of the web request, this makes sure to close the database connection.
  If you don't the database could run out of memory!
  """
  try:
    g.conn.close()
  except Exception as e:
    pass


loggedin = false
userid = ''

@app.route('/test1/', methods=["POST", "GET"])
def test1():
  loggedin = true
  userid = request.form['userid']
  print userid
  return ''



@app.route('/test2/', methods=["POST", "GET"])
def test2():
  loggedin = false
  userid = null
  return ''


@app.route('/test3/', methods=["POST", "GET"])
def test3():
  loggedin = false
  userid = null
  return ''


app.route('/animals/', methods=["POST", "GET"])
def animals():
  
  cursor = g.conn.execute("SELECT distinct name FROM category")
  names = []
  for result in cursor:
    names.append(result['name'])
  cursor.close()
  context=dict(data=names)
  
  return render_template("animals.html", **context)

@app.route('/', methods=["POST", "GET"])
<<<<<<< HEAD
def index():  
  cursor = g.conn.execute("SELECT distinct name FROM category")
  names = []
  for result in cursor:
    names.append(result['name'])
  cursor.close()
  context=dict(data=names)
  return render_template("menu.html", **context)
=======

@app.route('/RonasTest', methods=["POST", "GET"])
def ronasTest():
	mydict = {}
	"""mydict["memetweet_name"] = "Rona Wo"
	mydict["memetweet_title"] = "Test Puppy Image"
	mydict["memetweet_image"] = "https://encrypted-tbn3.gstatic.com/images?q=tbn:ANd9GcRSeispWpEabZbYn7fIE74Bmm71pKWXvf1tJElobLkiEpl4sx35njAwamIx"
	mydict["comment_name"] = "It's Rona Again";
	mydict["comment_content"] = "Ronas test comment";"""
	mydict["all_memetweet_id"] = "1"
	return render_template("memetweet.html", **mydict)

@app.route('/like/', methods=["POST"])
def like():
	memeid = request.form['memeId']
	#q = "INSERT INTO upvotes Values (%s, %s);" 
	#g.conn.execute(q, (userid, memeid))
	return ""

@app.route('/like/', methods=["POST"])
def like():
	memeid = request.form['memeId']
	#q = "DELETE FROM upvotes WHERE userid=%s AND memeid=%s;" 
	#g.conn.execute(q, (userid, memeid))
	return ""

if __name__ == "__main__":
  import click

  @click.command()
  @click.option('--debug', is_flag=True)
  @click.option('--threaded', is_flag=True)
  @click.argument('HOST', default='0.0.0.0')
  @click.argument('PORT', default=8111, type=int)
  def run(debug, threaded, host, port):
    """
    This function handles command line parameters.
    Run the server using

        python server.py

    Show the help text using

        python server.py --help

    """

    HOST, PORT = host, port
    print "running on %s:%d" % (HOST, PORT)
    app.run(host=HOST, port=PORT, debug=debug, threaded=threaded)


  run()
