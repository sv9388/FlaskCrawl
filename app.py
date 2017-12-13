from flask import session, url_for, Flask, request, redirect, render_template
from flask_sqlalchemy import SQLAlchemy
import datetime

app = Flask(__name__)
app.config.from_pyfile("./insta_cfg.py")
db = SQLAlchemy(app)

token_id = "access_token"
DB_DATE_FS = '{:%Y-%m-%d 00:00:00}'

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

@app.route("/logout")
def logout():
  session.clear()
  return render_template('login.html')

@app.route("/instaboard/<string:handle>")
@login_required
def instaboard(handle, user=None):
  print(user)
  print(handle)
  accounts = [x.instagram_id for x in user.iprofiles]
  if handle not in accounts:
    session.clear()
    return redirect(url_for('logout'), msg = "Not allowed to do perform this action.")


  iprofileq = IprofileData.query.filter_by(iprofile_id = handle)
  iprofile_today = iprofileq.filter_by(date = DB_DATE_FS.format(datetime.datetime.today())).first()
  iprofile_yestr = iprofileq.filter_by(date = DB_DATE_FS.format(datetime.datetime.today() -  datetime.timedelta(days=1))).first()
  print(iprofile_today.id)

  dashboard_summary = {'{:30s}'.format('Follower Change') : iprofile_today.followers_count - (iprofile_yestr.followers_count if iprofile_yestr else 0),
                       '{:30s}'.format('Following Change') : iprofile_today.following_count -  (iprofile_yestr.following_count if iprofile_yestr else 0),
                       '{:30s}'.format('Post Change') : iprofile_today.media_likes -  (iprofile_yestr.media_likes if iprofile_yestr else 0),
                       '{:30s}'.format('Engagement Rate Change') : "{:3.1f} %".format((iprofile_today.engagement_rate - (iprofile_yestr.engagement_rate if iprofile_yestr else 0))*100)}

  today = datetime.datetime.today()
  start_date = datetime.datetime(today.year, today.month, 1)
  end_date   = datetime.datetime(today.year, today.month, today.day)
  iprofiles = iprofileq.filter(IprofileData.date >= DB_DATE_FS.format(start_date)).filter(IprofileData.date <= DB_DATE_FS.format(end_date)).all()

  print((iprofiles[0].date))
  following_raw_data =   [[datetime.datetime.strptime(x.date, '%Y-%m-%d %H:%M:%S').strftime('%Y/%m/%d'), x.following_count] for x in iprofiles]
  followers_raw_data =   [[datetime.datetime.strptime(x.date, '%Y-%m-%d %H:%M:%S').strftime('%Y/%m/%d'), x.followers_count] for x in iprofiles]
  media_likes_raw_data = [[datetime.datetime.strptime(x.date, '%Y-%m-%d %H:%M:%S').strftime('%Y/%m/%d'), x.media_likes] for x in iprofiles]
  engagement_rate_raw_data = [[datetime.datetime.strptime(x.date, '%Y-%m-%d %H:%M:%S').strftime('%Y/%m/%d'), x.engagement_rate] for x in iprofiles]

  following_raw_data =   [[following_raw_data[i][0], following_raw_data[i][1] - following_raw_data[i-1][1]] for i in range(1, len(following_raw_data))]
  followers_raw_data =   [[followers_raw_data[i][0], followers_raw_data[i][1] - followers_raw_data[i-1][1]] for i in range(1, len(followers_raw_data))]
  media_likes_raw_data = [[media_likes_raw_data[i][0], media_likes_raw_data[i][1] - media_likes_raw_data[i-1][1]] for i in range(1, len(media_likes_raw_data))]
  engagement_rate_raw_data = [[engagement_rate_raw_data[i][0], engagement_rate_raw_data[i][1] - engagement_rate_raw_data[i-1][1]] for i in range(1, len(engagement_rate_raw_data))]

  return render_template('instaboard.html', roles = [x.name for x in user.roles], accounts = accounts, username = user.username.upper(), profile_pic = user.profile_pic, \
                        handle = handle, dashboard_summary = dashboard_summary, following_raw_data = following_raw_data, \
                        followers_raw_data = followers_raw_data,  media_likes_raw_data = media_likes_raw_data, engagement_rate_raw_data = engagement_rate_raw_data)

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
        return redirect(url_for('login'), msg = "Not allowed to do perform this action.")
    all_users = User.query.all()
    return render_template('admin.html', roles = [x.name for x in user.roles], accounts = [x.instagram_id for x in user.iprofiles], username = user.username.upper(), profile_pic = user.profile_pic, all_users = all_users)

@app.route("/admin/<int:id>/max_accounts", methods = ["POST", "PUT"])
@login_required
def max_acc_edit(id, user = None):
    print(request.method)
    print(request.form)
    if not 'admin' in [x.name for x in user.roles]:
        session.clear()
        return redirect(url_for('login'), msg = "Not allowed to do perform this action.")
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

@app.route('/user', methods = ['GET', 'PUT'])
@login_required
def app_user(user = None):
  if request.method == 'GET':
    return render_template('profile.html', user = user)
  if request.method == "PUT":
    if request.form['password'] != request.form['rpassword']:
        return render_template('profile.html', user = user, msg = "Passwords don't match")
    user.email = request.form['email']
    user.username = request.form['username']
    user.hash_password(request.form['password'])
    db.session.add(user)
    db.session.commit()
    return render_template('profile.html', user = user, msg = "User details upgraded successfully.")

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
