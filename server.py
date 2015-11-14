import os
from sqlalchemy import *
from sqlalchemy.pool import NullPool
from flask import Flask, request, render_template, g, redirect, Response, make_response
import datetime


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


@app.route('/test1/', methods=["POST", "GET"])
def test1():
  if not request.cookies.get('userid'):
    userid = request.form['userid']
    username = request.form['username']
    q = "SELECT * FROM defaultuser WHERE id=%s"
    cursor = g.conn.execute(q, (int(userid)))
    exists = False
    for result in cursor:
      exists = True
      break
    if not exists:
      q = "INSERT INTO defaultuser VALUES (%s, %s, %s)"
      g.conn.execute(q, (int(userid), username, True))
    response = make_response('')
    response.set_cookie('userid', userid)
    response.set_cookie('username', username)
    return response
  return ''



@app.route('/test2/', methods=["POST", "GET"])
def test2():
  if request.cookies.get('userid'):
    response = make_response('')
    response.set_cookies('userid', None)
    response.set_cookies('username', None)
    return response
  return ''


@app.route('/test3/', methods=["POST", "GET"])
def test3():
  if request.cookies.get('userid'):
    response = make_response('')
    response.set_cookies('userid', None)
    response.set_cookies('username', None)
    return response
  return ''


mainlimit = 3
@app.route('/', methods=["POST", "GET"])
def index():  
  cursor = g.conn.execute("SELECT distinct name FROM category")
  names = []
  for result in cursor:
    names.append(result['name'])
  cursor.close()
  context=dict(data=names)
  memes = []
  #Get recent memes posted by the people you're following
  if request.cookies.get('userid'):
    memes = memes + recent_posts_from_following(request.cookies.get('userid'), 0)
    context["sections"] = ["People_You_Are_Following"]
    
  #Get most popular memes
  memes = memes + most_pop_posts(0)
  context["sections"].append("Most_Popular_MemeTweets")
  
  #Get most recent memes
  memes = memes + most_recent_posts(0)
  context["sections"].append("Most_Recent_MemeTweets")
  context["memes"] = memes
  context["limit"] = mainlimit
  response = make_response(render_template("memetweet.html", **context))
  response.set_cookie('followeroffset', str(mainlimit)) 
  response.set_cookie('popularoffset', str(mainlimit))
  response.set_cookie('recentoffset', str(mainlimit))
  return response

def most_recent_posts(offset):
  memes = []
  q =  "select m.id, m.title, m.imageurl, m.userid, m.locked, m.timeuploaded, " + \
      "m.markasinappropriate, d.username " + \
      "from memetweet m, defaultuser d " + \
      "where m.userid = d.id " + \
      "order by m.timeuploaded desc " + \
      "limit " + str(mainlimit) + " offset %s "
  cursor = g.conn.execute(q, (offset))
  for c in cursor:
    meme = {}
    meme['locked'] = c['locked']
    meme['markasinappropriate'] = c['markasinappropriate']
    meme['timeuploaded'] = c['timeuploaded']
    meme['memeid'] = c['id']
    meme['userid'] = c['userid']
    meme['username'] = c['username']
    meme['imageurl'] = c['imageurl'].strip()
    meme['title'] = c['title'].strip()
    meme['section'] = "Most_Recent_MemeTweets"
    memes.append(meme)
  cursor.close()
  return memes;

def most_pop_posts(offset):
  memes = []
  q = "select mru.id, mru.title, mru.imageurl, mru.userid, mru.locked, mru.timeuploaded, mru.markasinappropriate," + \
      " mru.categoryname, mru.retweets, mru.upvotes, defaultuser.username " + \
      "from  " + \
      "  (select mr.id, mr.title, mr.imageurl, mr.userid, mr.locked, " + \
      "  mr.timeuploaded, mr.markasinappropriate, mr.categoryname, " + \
      "  mr.retweets, coalesce(u.upvotes, 0) as upvotes " + \
      "  from  " + \
      "    (select m.id, m.title, m.imageurl, m.userid, m.locked, " + \
      "    m.timeuploaded, m.markasinappropriate, m.categoryname,    coalesce(r.retweets, 0) as retweets " + \
      "    from memetweet as m LEFT OUTER JOIN  " + \
      "      (select memeid as id, count(memeid) as retweets " + \
      "      from retweet " + \
      "      group by memeid) as r " + \
      "    on m.id = r.id) as mr LEFT OUTER JOIN " + \
      "    (select memeid as id, count(memeid) as upvotes " + \
      "    from upvotes " + \
      "    group by memeid) as u " + \
      "  on mr.id = u.id) as mru, defaultuser " + \
      "where mru.userid = defaultuser.id " + \
      "order by (mru.retweets + mru.upvotes) desc " + \
      "limit " + str(mainlimit) + " offset %s "
  cursor = g.conn.execute(q, (offset))
  for c in cursor:
    meme = {}
    meme['locked'] = c['locked']
    meme['markasinappropriate'] = c['markasinappropriate']
    meme['timeuploaded'] = c['timeuploaded']
    meme['memeid'] = c['id']
    meme['userid'] = c['userid']
    meme['username'] = c['username']
    meme['imageurl'] = c['imageurl'].strip()
    meme['title'] = c['title'].strip()
    meme['section'] = "Most_Popular_MemeTweets"
    memes.append(meme)
  cursor.close()
  return memes;

def recent_posts_from_following(userid, offset):
  memes = []
  q = "select meme.id, meme.title, meme.imageurl, meme.userid, defaultuser.username," + \
      " meme.timeUploaded, meme.locked, meme.markasinappropriate " + \
      "from " + \
      "(select id, title, imageurl, userid, timeUploaded, locked, markasinappropriate " + \
      "from memetweet " + \
      "where id in " + \
        "(select followeeid " + \
        "from follows " + \
        "where followerid=%s)) as meme, " + \
      "defaultuser " + \
    "where defaultuser.id = meme.userid order by meme.timeUploaded desc limit " + str(mainlimit) + " offset %s;"
  cursor = g.conn.execute(q, (userid, offset))
  for c in cursor:
    meme = {}
    meme['locked'] = c['locked']
    meme['timeuploaded'] = c['timeuploaded']
    meme['markasinappropriate'] = c['markasinappropriate']
    meme['memeid'] = c['id']
    meme['userid'] = c['userid']
    meme['username'] = c['username']
    meme['imageurl'] = c['imageurl'].strip()
    meme['title'] = c['title'].strip()
    meme['section'] = "People_You_Are_Following"
    memes.append(meme)
  cursor.close()
  return memes;

categorylimit = 10
@app.route('/categories/<categoryname>/', methods=["POST", "GET"])
def category(categoryname):
  cursor = g.conn.execute("SELECT distinct name FROM category")
  names = []
  for result in cursor:
    names.append(result['name'])
  cursor.close()
  context = dict(data=names)
  context['memes'] = pop_memes_from_category(categoryname, 0)
  context["sections"] = [categoryname]
  context["limit"] = categorylimit
  response = make_response(render_template("memetweet.html", **context))
  response.set_cookie(categoryname + "offset", str(categorylimit)) 
  return response

def pop_memes_from_category(categoryname, offset):
  q = "select t1.id, t1.count as retweets, t2.userid, t3.username, t4.count as upvotes ,t5.imageurl," + \
      " t5.title, t5.locked, t5.markasinappropriate " + \
      "from( " + \
        "select id,count(retweet.memeid) " + \
        "from memetweet "  + \
        "left outer join retweet " + \
        "on memetweet.id = retweet.memeid " + \
        "group by id " + \
        "order by id " + \
      ") " + \
      "as t1, " + \
      "(select * " + \
        "from memetweet " + \
        "where memetweet.categoryname = %s" + \
        ") " + \
      "as t2, " + \
      "(select * " + \
      "from defaultuser) " + \
      "as t3, " + \
      "(select id,count(upvotes.memeid) " + \
        "from memetweet left outer join upvotes " + \
        "on memetweet.id = upvotes.memeid  " + \
        "group by id " + \
        "order by id " + \
      ") " + \
      "as t4, " + \
      "(select * " + \
      "from memetweet) as t5 " + \
    "where t1.id = t2.id " + \
    "and t4.id = t2.id " + \
    "and t2.userid = t3.id " + \
    "and t5.id = t2.id " + \
    "order by t1.count+t4.count desc limit " +  str(categorylimit)  + " offset %s;"
  cursor = g.conn.execute(q, (categoryname, offset))
  memes = []
  for c in cursor:
    meme = {}
    meme['locked'] = c['locked']
    meme['markasinappropriate'] = c['markasinappropriate']
    meme['memeid'] = c['id']
    meme['retweets'] = c['retweets']
    meme['userid'] = c['userid']
    meme['username'] = c['username']
    meme['upvotes'] = c['upvotes']
    meme['imageurl'] = c['imageurl'].strip()
    meme['title'] = c['title'].strip()
    meme['section'] = categoryname
    memes.append(meme)
  return memes

@app.route('/users/<userid>/', methods = ["POST","GET"])
def users(userid):
    cursor = g.conn.execute("SELECT distinct name FROM category")
    names = []
    for result in cursor:
      names.append(result['name'])
    cursor.close()
    q = "SELECT username from defaultuser where id = %s;"
    cursor = g.conn.execute(q,(userid))
    users = []
    print (q,(userid))
    for result in cursor:
      users.append(result['username'])
    cursor.close()

    q = "select count(*) " + \
      "from ( " + \
              "select id " + \
              "from memetweet " + \
              "where userid = %s) as memes, " + \
              "(select * " + \
              "from retweet ) as retweets " + \
      "where memes.id = retweets.memeid; "
    
    cursor = g.conn.execute(q,(userid))
    retweets = []
    print (q,(userid))
    for result in cursor:
      retweets.append(result['count'])
    cursor.close()

    q = "select count(*) " + \
      "from ( " + \
              "select id " + \
              "from memetweet " + \
              "where userid = %s) as memes, " + \
              "(select * " + \
              "from upvotes ) as upvotes " + \
      "where memes.id = upvotes.memeid; "
    
    cursor = g.conn.execute(q,(userid))
    upvotes = []
    print (q,(userid))
    for result in cursor:
      upvotes.append(result['count'])
    cursor.close()

    q = "select t2.username " + \
        "from ( " + \
        "select followeeid from follows " + \
        "where followerid = %s) as t1, " + \
        "(select * from defaultuser) as t2 " + \
        "where t1.followeeid = t2.id; "
    cursor = g.conn.execute(q,(userid))
    followees = []
    for results in cursor:
      followees.append(results['username'])
    cursor.close()

    q = "select t2.username " + \
        "from ( " + \
        "select followerid from follows " + \
        "where followeeid = %s) as t1, " + \
        "(select * from defaultuser) as t2 " + \
        "where t1.followerid = t2.id; "
    cursor = g.conn.execute(q,(userid))
    followers = []
    for results in cursor:
      followers.append(results['username'])
    cursor.close()

    
    context = dict(data=names, usernames = users, retweet = retweets, upvote = upvotes, 
                   followees=followees, followers = followers)
    print request.path
    return render_template("users.html", **context)

@app.route('/like/', methods=["POST", "GET"])
def like():
  if not request.cookies.get('userid'):
    return "You must be logged in to do that!"
  memeid = request.form['memeId']
  print memeid
  userid = request.cookies.get('userid')
  print userid
  q = "INSERT INTO upvotes VALUES (%s, %s);" 
  g.conn.execute(q, (userid, memeid))
  return ""

@app.route('/unlike/', methods=["POST"])
def unlike():
  if not request.cookies.get('userid'):
    return "You must be logged in to do that!"
  memeid = request.form['memeId']
  userid = request.cookies.get('userid')
  q = "DELETE FROM upvotes WHERE userid=%s AND memeid=%s;" 
  g.conn.execute(q, (userid, memeid))
  return ""

@app.route('/retweet/', methods=["POST"])
def retweet():
  if not request.cookies.get('userid'):
    return "You must be logged in to do that!"
  memeid = request.form['memeId']
  userid = request.cookies.get('userid')
  q = "INSERT INTO retweet VALUES(%s, %s);"
  g.conn.execute(q, (userid, memeid))
  return ""

@app.route('/getComments/', methods=["POST"])
def get_comment():
  memeid = request.form['memeId']
  q = "SELECT c.userid, c.commentText, c.timeUploaded, u.username " + \
      "FROM comment c, defaultuser u " + \
      "WHERE c.memeid = %s and c.userid = u.id " + \
      "ORDER BY c.timeUploaded DESC "
  cursor = g.conn.execute(q, (memeid))
  result = ""
  for c in cursor:
    result += create_comment(memeid, c['username'], c['userid'], c['commenttext'])
  return result

@app.route('/addComment/', methods=["POST"])
def add_comment():
  if not request.cookies.get('userid'):
      return "You must be logged in to do that!"
  memeid = request.form['memeId']
  comment = request.form['comment']
  userid = request.cookies.get('userid')
  username = request.cookies.get('username')
  time = datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
  q = "INSERT INTO comment (memeid, userid, commentText, timeUploaded) VALUES(%s, %s, %s, %s)"
  g.conn.execute(q, (memeid, userid, comment, time))
  return ""

@app.route('/isLiked/', methods=["POST"])
def is_liked():
  if not request.cookies.get('userid'):
      return "false"
  memeid = request.form['memeId']
  userid = request.cookies.get('userid')
  q = "SELECT * FROM upvotes WHERE userid=%s and memeid=%s"
  cursor = g.conn.execute(q, (userid, memeid))
  isLiked = "false"
  for c in cursor:
    isLiked = "true"
  return isLiked

def create_comment(memetweet_id, comment_name, comment_person_id, comment_content):
  toAddHtml = "<div class='comment_container'>" + \
            "<div class='comment_person'>" + \
              "<p class='comment_name person"
  toAddHtml += str(comment_person_id) + "'>"
  toAddHtml += comment_name
  toAddHtml += "</p>" + \
            "</div>" + \
            "<div class='comment_content'>" + \
              "<p>"
  toAddHtml += comment_content
  toAddHtml += "    </p>" + \
            "</div>" + \
          "</div>"
  return toAddHtml

@app.route('/newMemetweet/', methods=["POST"])
def newMemetweet():
  if not request.cookies.get('userid'):
    return "You need to be logged in to do that!"
  title = request.form['title'].strip()
  imageurl = request.form['imageurl'].strip()
  userid = request.cookies.get('userid')
  category = request.form['category']
  time = datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
  locked = False
  markasinappropriate = False
  q = "INSERT INTO memetweet (title, imageurl, timeUploaded, userid, locked, markasinappropriate, categoryname) " + \
      "VALUES (%s, %s, %s, %s, %s, %s, %s);"
  g.conn.execute(q, (title, imageurl, time, userid, locked, markasinappropriate, category))
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
    app.run(host=HOST, port=PORT, debug=True, threaded=threaded)


  run()
