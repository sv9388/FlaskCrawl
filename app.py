from flask import session, url_for, Flask, request, redirect, render_template, abort
from flask_sqlalchemy import SQLAlchemy
import datetime, requests, json, binascii, os

app = Flask(__name__)
app.config.from_pyfile("./insta_cfg.py")
db = SQLAlchemy(app)

default_summary = {'Follower Change' : 0, 'Following Change' : 0, 'Post Change' : 0, 'Engagement Rate Change' : "0.0 %"}
token_id = "access_token"
DB_DATE_FS = '{:%Y-%m-%d 00:00:00}'

@app.errorhandler(400)
def err400(e):
    return render_template('login.html', msg = "You have submitted an erroneous request. Flush cookies and retry. If the problem persists, contact admin!")

@app.before_request
def csrf_protect():
    if request.method == "POST":
        token = session.pop('_csrf_token', None)
        print(type(token))
        gottoken = request.form['_csrf_token']
        print(type(gottoken))
        if not token or not token == gottoken:
            abort(400)

def generate_csrf_token():
    if '_csrf_token' not in session:
        session['_csrf_token'] = binascii.hexlify(os.urandom(24)).decode()
    return session['_csrf_token']

app.jinja_env.globals['csrf_token'] = generate_csrf_token

from models import User, Role, Iprofile, IprofileData
from functools import wraps
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if token_id not in session or session[token_id] is None or User.verify_auth_token(session[token_id]) is None:
            return redirect(url_for('login', next=request.url))
        user = User.verify_auth_token(session[token_id])
        return f(*args, user = user, **kwargs)
    return decorated_function

def get_insta_profile_pic(handle):
    r = requests.get("""https://www.instagram.com/%s/?__a=1"""%handle)
    return json.loads(r.content)['user']['profile_pic_url']

def get_likes_moving_average(iprofiles):
  media_likes_mv_avg = []
  i = 0
  j = 0
  while j < len(iprofiles):
      den = 7 if (j-i)==7 else ((j-i)+1)
      num = sum([x.media_likes for x in iprofiles[i:j+1]])
      media_likes_mv_avg.append([iprofiles[j].date.strftime('%Y/%m/%d'), num * 1./den])
      j+=1
      i = i+1 if (j-i)==7 else i

  if len(media_likes_mv_avg)>=14:
      media_likes_mv_avg = media_likes_mv_avg[-14:]
  return media_likes_mv_avg

def get_summary(startp, endp):
    if not endp:
        return default_summary
    return {'Follower Change' : endp.followers_count - (startp.followers_count if startp else 0),
                       'Following Change' : endp.following_count -  (startp.following_count if startp else 0),
                       'Post Change' : endp.media_likes -  (startp.media_likes if startp else 0),
                       'Engagement Rate Change' : "{:3.1f} %".format((endp.engagement_rate - (startp.engagement_rate if startp else 0))*100)}


diffact = lambda s, e : [e, "{:.2f} %".format((s-e)*100./s if s > 0 else 0.0), 0] if s>e else [e, "{:.2f} %".format((e-s)*100./e if e > 0 else 0.0), 1]
def get_activity(handle):
  tstart_date = datetime.datetime.today()-datetime.timedelta(days=1)
  mstart_date = datetime.datetime.today()-datetime.timedelta(days=31)
  end_date = datetime.datetime.today()
  tsp = IprofileData.query.filter_by(iprofile_id = handle).filter_by(date = DB_DATE_FS.format(tstart_date)).first()
  msp = IprofileData.query.filter_by(iprofile_id = handle).filter_by(date = DB_DATE_FS.format(mstart_date)).first()
  ep = IprofileData.query.filter_by(iprofile_id = handle).filter_by(date = DB_DATE_FS.format(end_date)).first()

  deng = diffact(tsp.engagement_rate if tsp else 0, ep.engagement_rate)
  deng = ["{:.2f} %".format(deng[0]), deng[1], deng[2]]
  daily_activity = {'following' : diffact(tsp.following_count if tsp else 0, ep.following_count), \
                    'followers' : diffact(tsp.followers_count if tsp else 0, ep.followers_count), \
                    'engagement' : deng, \
                    'likes' : diffact(tsp.media_likes if tsp else 0, ep.media_likes)}#, 'media' : [tsp.media_count if tsp else 0, ep.media_count]})

  meng = diffact(msp.engagement_rate if msp else 0, ep.engagement_rate)
  meng = ["{:.2f} %".format(meng[0]), meng[1], meng[2]]
  monthly_activity = {'following' : diffact(msp.following_count if msp else 0, ep.following_count), \
                      'followers' : diffact(msp.followers_count if msp else 0, ep.followers_count), \
                      'engagement' : meng, \
                      'likes' : diffact(tsp.media_likes if tsp else 0, ep.media_likes)}
  return daily_activity, monthly_activity

@app.route("/logout")
def logout():
  session.clear()
  return render_template('login.html')

@app.route("/ig/<string:handle>", methods = ["GET", "POST"])
@login_required
def instaboard(handle, user=None):
  print(user)
  print(handle)
  detail_str = "the past 14 days" if request.method == "GET" else " between %s and %s" % (request.form['startdate'], request.form['enddate'])
  accounts = [x.instagram_id for x in user.iprofiles]
  if handle not in accounts:
    session.clear()
    return render_template('login.html', msg = "Not a registered account to monitor.")

  iprofileq = IprofileData.query.filter_by(iprofile_id = handle)
  iprofile_today = iprofileq.filter_by(date = DB_DATE_FS.format(datetime.datetime.today())).first()
  #iprofile_yestr = iprofileq.filter_by(date = DB_DATE_FS.format(datetime.datetime.today() -  datetime.timedelta(days=1))).first()
  summary_start_date = DB_DATE_FS.format(datetime.datetime.today() -  datetime.timedelta(days=1))
  if iprofile_today is None: # or iprofile_yestr is None:
    return render_template('instaboard.html', roles = [x.name for x in user.roles], accounts = accounts, username = user.username.upper(), \
            profile_pic = user.profile_pic, handle = handle, iprofile_pic = get_insta_profile_pic(handle), detail_str = detail_str, \
            dashboard_summary = default_summary, summary_start_date = summary_start_date, \
            following_raw_data = [], followers_raw_data = [],  media_likes_raw_data = [], \
            engagement_rate_raw_data = [], media_likes_mv_avg = [], \
            daily_activity = {'followers' : [0,0,0], 'following' : [0,0,0], 'engagement' : [0,0,0], 'likes' : [0, 0, 0]}, \
            monthly_activity = {'followers' : [0,0,0], 'following' : [0,0,0], 'engagement' : [0,0,0], 'likes' : [0, 0, 0]}, \
            followers_today = 0 if iprofile_today is None else iprofile_today.followers_count, \
            engagement_today = 0.0 if iprofile_today is None else iprofile_today.engagement_rate, \
            msg = "Nothing here yet! Check back in 2 days." if iprofile_today is None else "Only today's data is available. Check back tomorrow for userful content.")

  daily_activity, monthly_activity = get_activity(handle)

  dashboard_summary = {}
  summary_start_date = summary_start_date
  if request.method == "GET":
    iprofile_today = iprofileq.filter_by(date = DB_DATE_FS.format(datetime.datetime.today())).first()
    iprofile_yestr = iprofileq.filter_by(date = DB_DATE_FS.format(datetime.datetime.today() -  datetime.timedelta(days=1))).first()
    dashboard_summary = get_summary(iprofile_yestr,  iprofile_today)
  elif request.method == "POST":
    start_date = datetime.datetime.strptime(request.form['startdate'], "%m/%d/%Y")
    end_date = datetime.datetime.strptime(request.form['enddate'], "%m/%d/%Y")
    iprofile_start = iprofileq.filter_by(date = DB_DATE_FS.format(start_date)).first()
    iprofile_end = iprofileq.filter_by(date = DB_DATE_FS.format(end_date)).first()
    dashboard_summary = get_summary(iprofile_start, iprofile_end)
    summary_start_date = DB_DATE_FS.format(start_date)
  else:
    return render_template('instaboard.html', roles = [x.name for x in user.roles], accounts = accounts, username = user.username.upper(), \
            profile_pic = user.profile_pic, handle = handle, iprofile_pic = get_insta_profile_pic(handle), detail_str = detail_str, \
            dashboard_summary = default_summary, summary_start_date = summary_start_date,\
            following_raw_data = [], followers_raw_data = [],  media_likes_raw_data = [], \
            engagement_rate_raw_data = [], media_likes_mv_avg = [], \
            daily_activity = {'followers' : [0,0,0], 'following' : [0,0,0], 'engagement' : [0,0,0], 'likes' : [0, 0, 0]}, \
            monthly_activity = {'followers' : [0,0,0], 'following' : [0,0,0], 'engagement' : [0,0,0], 'likes' : [0, 0, 0]}, \
            followers_today = 0 if iprofile_today is None else iprofile_today.followers_count, \
            engagement_today = 0.0 if iprofile_today is None else iprofile_today.engagement_rate, \
            msg = "Unsupported method.")

  start_date = datetime.datetime.today()-datetime.timedelta(days=15)
  end_date   = datetime.datetime.today()-datetime.timedelta(days=1)
  if request.method == "POST":
    start_date = datetime.datetime.strptime(request.form['startdate'], "%m/%d/%Y")
    end_date = datetime.datetime.strptime(request.form['enddate'], "%m/%d/%Y")
    print(start_date)
    print(end_date)
  iprofiles = iprofileq.filter(IprofileData.date >= DB_DATE_FS.format(start_date)).filter(IprofileData.date <= DB_DATE_FS.format(end_date)).all()

  db_date = lambda dt : dt.strftime('%Y/%m/%d')
  following_raw_data =   [[db_date(x.date), x.following_count] for x in iprofiles ]
  followers_raw_data =   [[db_date(x.date), x.followers_count] for x in iprofiles]
  engagement_rate_raw_data = [[db_date(x.date), x.engagement_rate] for x in iprofiles]
  media_likes_raw_data = [[db_date(x.date), x.media_likes] for x in iprofiles]

  start_date = start_date - datetime.timedelta(days = 7)
  mvprofiles = iprofileq.filter(IprofileData.date >= DB_DATE_FS.format(start_date)).filter(IprofileData.date <= DB_DATE_FS.format(end_date)).all()
  media_likes_mv_avg = get_likes_moving_average(mvprofiles)

  print(followers_raw_data)
  print(engagement_rate_raw_data)
  return render_template('instaboard.html', roles = [x.name for x in user.roles], accounts = accounts, username = user.username.upper(), \
                        profile_pic = user.profile_pic, handle = handle, iprofile_pic = get_insta_profile_pic(handle), detail_str = detail_str,  \
                        dashboard_summary = dashboard_summary, summary_start_date = summary_start_date,\
                        following_raw_data = following_raw_data, followers_raw_data = followers_raw_data,  media_likes_raw_data = media_likes_raw_data, \
                        engagement_rate_raw_data = engagement_rate_raw_data, media_likes_mv_avg = media_likes_mv_avg, daily_activity = daily_activity, \
                        monthly_activity = monthly_activity, followers_today = iprofile_today.followers_count, engagement_today = iprofile_today.engagement_rate)

@app.route("/instaaccounts", methods = ["GET", "POST"])
@login_required
def instaaccounts(user = None):
  existing_accounts = [x.instagram_id for x in user.iprofiles]
  if request.method == "GET":
    print(user.email)
    return render_template('instaaccounts.html', roles = [x.name for x in user.roles], accounts = existing_accounts, username = user.username.upper(), profile_pic = user.profile_pic, account_limit = user.max_insta_accounts)
  if request.method == "POST":
    updated_accounts = request.form['accounts']
    updated_accounts = list(set(updated_accounts.split(',')))
    if len(updated_accounts) > user.max_insta_accounts:
        return render_template('instaaccounts.html', roles = [x.name for x in user.roles], accounts = existing_accounts, username = user.username.upper(), profile_pic = user.profile_pic, account_limit = user.max_insta_accounts, msg = "You cannot monitor more than %d accounts"%user.max_insta_accounts)

    delete_accounts = user.iprofiles
    for x in delete_accounts:
        user.iprofiles.remove(x)

    #new_accounts = get_insta_accounts_by_handles(updated_accounts)
    profiles = []
    for x in updated_accounts:
        prof = Iprofile.query.filter_by(instagram_id = x).first()
        if not prof:
            prof = Iprofile()
            prof.instagram_id = x
            db.session.add(prof)
            db.session.commit()
        profiles.append(prof)
    user.iprofiles = profiles
    db.session.add(user)
    db.session.commit()
    print(','.join([x.instagram_id for x in user.iprofiles]))
    return render_template('instaaccounts.html', roles = [x.name for x in user.roles], accounts = [x.instagram_id for x in user.iprofiles], username = user.username.upper(), profile_pic = user.profile_pic, account_limit = user.max_insta_accounts, msg = "Updated the account handles you are monitoring. Come back tomorrow for some interesting info!")

@app.route("/admin")
@login_required
def admin(user = None):
    if not 'admin' in [x.name for x in user.roles]:
        session.clear()
        return render_template('login.html', msg = "Not allowed to do perform this action.")
    all_users = User.query.all()
    return render_template('admin.html', roles = [x.name for x in user.roles], accounts = [x.instagram_id for x in user.iprofiles], username = user.username.upper(), profile_pic = user.profile_pic, all_users = all_users)

@app.route("/admin/<int:id>/max_accounts", methods = ["POST", "PUT"])
@login_required
def max_acc_edit(id, user = None):
    print(request.method)
    print(request.form)
    if not 'admin' in [x.name for x in user.roles]:
        session.clear()
        return render_template('login.html', msg = "Not allowed to do perform this action.")
    eduser = User.query.filter_by(id = id).first()
    eduser.max_insta_accounts = int(request.form['value'])
    db.session.add(eduser)
    db.session.commit()

    all_users = User.query.all()
    return render_template('admin.html', roles = [x.name for x in user.roles], accounts = [x.instagram_id for x in user.iprofiles], username = user.username.upper(), profile_pic = user.profile_pic, all_users = all_users)

@app.route("/")
@login_required
def index(user = None):
    return redirect(url_for('instaaccounts', user = user))

@app.route('/login', methods = ['GET', 'POST'])
def login():
  if request.method == "GET":
    if token_id in session:
      return redirect(url_for('instaaccounts'))
    return render_template('login.html')
  if request.method == "POST":
    print(request.form)
    user = User.query.filter_by(email = request.form['email']).first()
    if not user:
      return render_template('login.html', msg = "Incorrect email")
    session[token_id] = user.generate_auth_token()
    return redirect(url_for('instaaccounts'))

@app.route('/register', methods = ['GET', 'POST'])
def register():
  if request.method == "GET":
    return render_template('register.html')
  if request.method == "POST":
    print(request.form)
    if request.form['email'] != request.form['remail']:
        return render_template('register.html', msg = "Emails don't match")
    if User.query.filter_by(email=request.form['email']).first():
        return render_template('register.html', msg = "Email already taken. Did you forget password?")
    if request.form['password'] != request.form['rpassword']:
        return render_template('register.html', msg = "Passwords don't match")

    roles = [Role.query.filter_by(name="regular_user").first()]
    user = User()
    user.email = request.form['email']
    user.username = request.form['username']
    user.hash_password(request.form['password'])
    user.roles = roles
    db.session.add(user)
    db.session.commit()
    return render_template('register.html', msg = "Registration complete. Login to the app to access features")

@app.route('/upgrade')
@login_required
def upgrade(user = None):
    return render_template('upgrade.html', roles = [x.name for x in user.roles], accounts = [x.instagram_id for x in user.iprofiles], username = user.username.upper(), profile_pic = user.profile_pic)

@app.route('/user', methods = ['GET', 'POST'])
@login_required
def app_user(user = None):
  if request.method == 'GET':
    return render_template('profile.html', roles = [x.name for x in user.roles], accounts = [x.instagram_id for x in user.iprofiles], username = user.username.upper(), profile_pic = user.profile_pic, email = user.email)
  if request.method == "POST":
    if request.form['password'] != request.form['cpassword']:
        return render_template('profile.html', roles = [x.name for x in user.roles], accounts = [x.instagram_id for x in user.iprofiles], username = user.username.upper(), profile_pic = user.profile_pic, email = user.email)
    user.username = request.form['username']
    if request.form['password'] != '':
        user.hash_password(request.form['password'])
    db.session.add(user)
    db.session.commit()
    return render_template('profile.html', roles = [x.name for x in user.roles], accounts = [x.instagram_id for x in user.iprofiles], username = user.username.upper(), profile_pic = user.profile_pic, email = user.email, msg = "User details upgraded successfully.")

@app.route('/password/forgot', methods = ['GET', 'POST'])
def forgot_password():
  if request.method == "GET":
    return render_template('forgot_password.html')
  if request.method == "POST":
    user = User.query.filter_by(email = request.form['email']).first()
    if not user:
        return render_template('forgot_password.html', msg = "No such email found.")
    user.hash_password('123456')
    db.session.add(user)
    db.session.commit()
    return render_template('forgot_password.html', msg = "Your dummy password is 123456. Login and reset the password. ")
