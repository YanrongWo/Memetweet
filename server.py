import os
from sqlalchemy import *
from sqlalchemy.pool import NullPool
from flask import Flask, request, render_template, g, redirect, Response, make_response
import datetime
import json

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
      g.conn.execute(q, (int(userid), username, False))
    response = make_response('changed')
    response.set_cookie('userid', userid)
    response.set_cookie('username', username)
    return response
  return ''


@app.route('/test2/', methods=["POST", "GET"])
def test2():
  if request.cookies.get('userid'):
    response = make_response('changed')
    response.set_cookie('userid', '', expires=0)
    response.set_cookie('username', '', expires=0)
    return response
  return ''


@app.route('/test3/', methods=["POST", "GET"])
def test3():
  if request.cookies.get('userid'):
    response = make_response('changed')
    response.set_cookie('userid', '', expires=0)
    response.set_cookie('username', '', expires=0)
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
  context["sections"] = []
  #Get recent memes posted by the people you're following
  if request.cookies.get('userid'):
    memes = memes + recent_posts_from_following(request.cookies.get('userid'), 0)
    context["sections"].append("People_You_Are_Following")
    
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
    meme['memeid'] = c['id']
    meme['userid'] = c['userid']
    meme['username'] = c['username']
    meme['imageurl'] = c['imageurl'].strip()
    meme['title'] = c['title'].strip()
    meme['section'] = "Most_Recent_MemeTweets"
    meme['isretweet'] = "False"
    memes.append(meme)
  cursor.close()
  return memes;

def most_pop_posts(offset):
  memes = []
  q = "select mru.id, mru.title, mru.imageurl, mru.userid, mru.locked, mru.markasinappropriate," + \
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
    meme['memeid'] = c['id']
    meme['userid'] = c['userid']
    meme['username'] = c['username']
    meme['imageurl'] = c['imageurl'].strip()
    meme['title'] = c['title'].strip()
    meme['section'] = "Most_Popular_MemeTweets"
    meme['isretweet'] = "False"
    memes.append(meme)
  cursor.close()
  return memes;

def recent_posts_from_following(userid, offset):
  print offset
  memes = []
  q = "select * from " + \
    "((select meme.id, meme.title, meme.imageurl, meme.userid, defaultuser.username, " + \
      " meme.locked, meme.markasinappropriate, 1=0 as isretweet, meme.timeuploaded " + \
      "from " + \
      "(select id, title, imageurl, userid, timeUploaded, locked, markasinappropriate " + \
      "from memetweet " + \
      "where id in " + \
        "(select followeeid " + \
        "from follows " + \
        "where followerid=%s)) as meme, " + \
      "defaultuser " + \
    "where defaultuser.id = meme.userid) " + \
    "union " + \
    "(select m.id, m.title, m.imageurl, u.id, u.username, m.locked, m.markasinappropriate, 1=1 as isretweet, r.timeretweeted " + \
    "from memetweet m, defaultuser u, " + \
    "(select r.userid, r.memeid, r.timeretweeted " + \
    "from retweet r " + \
    "where r.userid in  " + \
    "  (select followeeid " + \
    "  from follows " + \
    "  where followerid = %s)) as r " + \
    "where m.id = r.memeid and u.id = r.userid)) as pr " + \
    "order by timeUploaded desc limit " + str(mainlimit) + " offset %s;"
  cursor = g.conn.execute(q, (userid, userid, offset))
  for c in cursor:
    meme = {}
    meme['locked'] = c['locked']
    meme['markasinappropriate'] = c['markasinappropriate']
    meme['memeid'] = c['id']
    meme['userid'] = c['userid']
    meme['username'] = c['username']
    meme['imageurl'] = c['imageurl'].strip()
    meme['title'] = c['title'].strip()
    meme['section'] = "People_You_Are_Following"
    if (c['isretweet']):
      meme['isretweet'] = "True"
    else:
      meme['isretweet'] = "False"
    memes.append(meme)
  cursor.close()
  print memes
  return memes

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
    meme['isretweet'] = "False"
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

    for result in cursor:
      upvotes.append(result['count'])
    cursor.close()

    q = "select t2.username, t2.id " + \
        "from ( " + \
        "select followeeid from follows " + \
        "where followerid = %s) as t1, " + \
        "(select * from defaultuser) as t2 " + \
        "where t1.followeeid = t2.id; "
    cursor = g.conn.execute(q,(userid))
    followees = []

    for result in cursor:
      followees.append({'name':result['username'], 'id':str(result['id'])})
    cursor.close()

    q = "select t2.username, t2.id " + \
        "from ( " + \
        "select followerid from follows " + \
        "where followeeid = %s) as t1, " + \
        "(select * from defaultuser) as t2 " + \
        "where t1.followerid = t2.id; "
    cursor = g.conn.execute(q,(userid))
    followers = []
    for result in cursor:
      followers.append({'name':result['username'], 'id':str(result['id'])})
    cursor.close()

    q = "select id " + \
        "from defaultuser " + \
        "where admin = true " + \
        "and id = %s; "

    cursor = g.conn.execute(q,(userid))
    admin = 0
    print (q,(userid))
    for result in cursor:
      admin = 1
    cursor.close()
    ratings = -1
    loggedin = False
    if(request.cookies.get('userid')):
      loggedin = True

    limit = 5
    if(admin == 1):
      q = "select avg(rating) " + \
        "from rates " + \
        "where adminid = %s; "
      cursor = g.conn.execute(q,(userid))
      for result in cursor:
        if(result['avg']):
          ratings = str(round(result['avg'], 2))
      cursor.close()

    meme = []
    q = "select * from memetweet inner join defaultuser on memetweet.userid = defaultuser.id where userid = %s; "
    cursor = g.conn.execute(q,(userid))
    for result in cursor:
      meme.append({'memeid': result['id'], 'username': result['username'], 'title':result['title'].strip(), 'imageurl': result['imageurl'].strip(), 
       'userid': result['userid'], 'section': 'Posts', 'locked': result['locked'],
       'markasinappropriate': result['markasinappropriate'], 'isretweet': 'False'})
    cursor.close()

    q = "select mt.id, mt.title, mt.userid, mt.imageurl, mt.locked, mt.timeuploaded, mt.markasinappropriate, mt.categoryname, du.username " + \
    "from memetweet mt left outer join retweet rt on mt.id = rt.memeid " + \
    "left outer join defaultuser du on du.id = mt.userid " + \
    "where rt.userid = %s ;"

    cursor = g.conn.execute(q,(userid))
    for result in cursor:
      meme.append({'memeid': result['id'], 'username': result['username'], 'title':result['title'].strip(), 'imageurl': result['imageurl'].strip(),
       'userid': result['userid'], 'section': 'Retweets', 'locked': result['locked'], 
       'markasinappropriate': result['markasinappropriate'], 'isretweet': 'True' })
    section = ["Retweets", "Posts"]
    context = dict(data=names, usernames = users, retweet = retweets, upvote = upvotes, 
                   followees=followees, followers = followers, ratings = ratings, memes = meme, sections = section, 
                   loggedin = loggedin, limit = limit, admin=admin)

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
  time = datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
  q = "INSERT INTO retweet VALUES(%s, %s, %s);"
  g.conn.execute(q, (userid, memeid, time))
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

@app.route('/updatevote/', methods = ["POST"])
def updatevote():
  admin = str(request.form['userid'])
  rating = str(request.form['vote'])
  poster = str(request.cookies.get('userid'))
  admin = str(admin.split("/")[2])
  print admin
  print admin + " " + poster
  q = "select * from rates where adminid = %s and posterid = %s; "
  cursor = g.conn.execute(q, (admin, poster))
  print (q, (admin,poster))
  voted = False
  for c in cursor:
    voted = True
  cursor.close()
  print voted
  if (voted):
    q = "update rates set rating = %s where adminid = %s and posterid = %s; "
    cursor = g.conn.execute(q, (rating,admin,poster))
    cursor.close()
    print "updates"
  else:
    q = "insert into rates VALUES(%s,%s,%s); "
    cursor = g.conn.execute(q, (admin,poster,rating))
    cursor.close()
    print "inserts"
  return ""

@app.route('/rateradmin/', methods=["POST"])
def rateradmin():
  if not request.cookies.get('userid'):
    return false;
  userid = request.cookies.get('userid')
  q = "SELECT admin from defaultuser where id = %s"
  cursor = g.conn.execute(q, (userid))
  admin = "false"
  for c in cursor:
    if(c['admin'] == True):
      admin = "true"
  return admin

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

@app.route('/delete/', methods=["POST"])
def delete():
  memeid = request.form['memeId']
  q = "DELETE FROM memetweet WHERE id = %s"
  g.conn.execute(q, (memeid));
  return ''

@app.route('/nsfw/', methods=['POST'])
def nsfw():
  memeid = request.form['memeId']
  q = "UPDATE memetweet SET markasinappropriate = TRUE WHERE id = %s"
  g.conn.execute(q, (memeid));
  return ''

@app.route('/sfw/', methods=['POST'])
def sfw():
  memeid = request.form['memeId']
  q = "UPDATE memetweet SET markasinappropriate = FALSE WHERE id = %s"
  g.conn.execute(q, (memeid));
  return ''

@app.route('/seeMore/', methods=["POST"])
def see_more():
  section = request.form['section']
  cookie_name = ""
  offset = 0
  memes = []
  if section == "People_You_Are_Following" and request.cookies.get('userid'):
    offset = request.cookies.get('followeroffset')
    cookie_name = 'followeroffset'
    memes = recent_posts_from_following(request.cookies.get('userid'), offset)
    offset = str(int(offset) + int(mainlimit))
  elif section == "Most_Popular_MemeTweets":
    offset = request.cookies.get('popularoffset')
    cookie_name = 'popularoffset'
    memes = most_pop_posts(offset)
    offset = str(int(offset) + int(mainlimit))
  elif section == "Most_Recent_MemeTweets":
    offset = request.cookies.get('popularoffset')
    cookie_name = 'popularoffset'
    memes = most_recent_posts(offset)
    offset = str(int(offset) + int(mainlimit))
  else:
    offset = request.cookies.get(section + "offset")
    cookie_name = section + "offset"
    memes = pop_memes_from_category(section, offset)
    offset = str(int(offset) + int(categorylimit))
  result = { "offset": offset, "cookie_name" : cookie_name, "memes": memes}
  return json.dumps(result)

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
