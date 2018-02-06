import os
from flask import session, url_for, Flask, request, redirect, render_template, abort, jsonify
from werkzeug.utils import secure_filename
from flask_sqlalchemy import SQLAlchemy
import datetime, binascii, os, re, logging, sys

ROOT_DIR = os.path.dirname(__file__)
#LOGOS_FOLDER = os.path.join(ROOT_DIR + "/" + app.config['UPLOAD_FOLDER'])
app = Flask(__name__)
app.config.from_pyfile("./insta_cfg.py")
app.config['UPLOAD_FOLDER'] = "static/logos"
app.logger.addHandler(logging.StreamHandler(sys.stdout))
app.logger.setLevel(logging.DEBUG)

db = SQLAlchemy(app)

token_id = "access_token"

ALLOWED_EXTENSIONS = set(['png', 'jpg', 'jpeg'])
ALL_FILTERS = ['followersc', 'activity', 'engagementc', 'likesc', 'fvsmnlikec' ]
FILTER_DICT = {'followersc' : "Followers Chart", 'activity' : "Activity", 'engagementc' : "Engagement Chart", 'likesc' : "Likes Chart", 'fvsmnlikec' : "Followers Vs Likes Chart"}
SERVER_NAME =  "analytics.socialmedia.com" #TEST: "smsilo.pythonanywhere.com"
UI_DATE_FS = '{:%m/%d/%Y}'

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.errorhandler(400)
def err400(e):
    print(e)
    return render_template('login.html', msg = "You have submitted an erroneous request. Flush cookies and retry. If the problem persists, contact admin!")

@app.before_request
def csrf_protect():
    if request.method == "POST":
        token = session.pop('_csrf_token', None)
        gottoken = request.form['_csrf_token']
        print(gottoken)
        print(token)
        if not token or not token == gottoken:
            abort(400)

def generate_csrf_token():
    if '_csrf_token' not in session:
        session['_csrf_token'] = binascii.hexlify(os.urandom(24)).decode()
    return session['_csrf_token']

app.jinja_env.globals['csrf_token'] = generate_csrf_token

from insta_utils import DB_DATE_FS, get_likes_moving_average, get_summary, get_activity, get_insta_profile_pic, get_chart_data
from models import User, Role, Iprofile, IprofileData, Tier
from functools import wraps
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if token_id not in session or session[token_id] is None or User.verify_auth_token(session[token_id]) is None:
            return render_template('login.html')
        user = User.verify_auth_token(session[token_id])
        return f(*args, user = user, **kwargs)
    return decorated_function

@app.route("/logout")
def logout():
  session.clear()
  return render_template('login.html')

def activity_util(handle, filters):
    if "activity" not in filters:
        app.logger.info("Activity not selected")
        app.logger.debug(filters)
        return None, None
    daily_activity, monthly_activity = get_activity(handle)
    app.logger.info("Monthly and daily activity retrieved")
    return daily_activity, monthly_activity

def summary_util(handle, filters, start_date = None, end_date = None):
    summary_start_date = datetime.datetime.today() -  datetime.timedelta(days=1) if not start_date else start_date
    summary_end_date = datetime.datetime.today() if not end_date else end_date
    app.logger.info("Retrieving dashboard summary for timerange %s and %s", summary_start_date, summary_end_date)
    dashboard_summary = get_summary(handle, summary_start_date, summary_end_date)
    app.logger.info("Retrieved Dashboard summary")
    return dashboard_summary, summary_start_date

def chart_util(handle, filters, start_date = None, end_date = None):
    chart_start_date = datetime.datetime.today()-datetime.timedelta(days=15) if not start_date else start_date
    chart_end_date   = datetime.datetime.today()-datetime.timedelta(days=1) if not end_date else end_date
    app.logger.info("Retrieving chart data for timerange %s and %s", chart_start_date, chart_end_date)
    following_raw_data, followers_raw_data, engagement_rate_raw_data, media_likes_raw_data = get_chart_data(handle, chart_start_date, chart_end_date, filters)
    app.logger.info("Retrieved chart data")
    return chart_start_date, chart_end_date, following_raw_data, followers_raw_data, engagement_rate_raw_data, media_likes_raw_data

def mv_avg_util(handle, filters, start_date = None, end_date = None):
    if "fvsmnlikec" not in filters:
        app.logger.info("Moving Avg Chart not selected")
        app.logger.debug(filters)
        return None

    mv_avg_start_date = datetime.datetime.today() - datetime.timedelta(days=15) if not start_date else start_date
    mv_avg_end_date = datetime.datetime.today() - datetime.timedelta(days=1) if not end_date else end_date
    mv_avg_start_date = mv_avg_start_date - datetime.timedelta(days=7)
    media_likes_mv_avg = get_likes_moving_average(handle, mv_avg_start_date, mv_avg_end_date)
    return media_likes_mv_avg

def get_board_data(handle, request_dict):
  iprofile_today = IprofileData.query.filter_by(iprofile_id = handle).filter_by(date = DB_DATE_FS.format(datetime.datetime.today())).first()
  followers_today = iprofile_today.followers_count if iprofile_today else 0
  engagement_today = iprofile_today.engagement_rate if iprofile_today else 0.0

  filters = session.get("_filters", ALL_FILTERS)
  print(filters)
  daily_activity, monthly_activity = activity_util(handle, filters)
  start_date = datetime.datetime.strptime(request_dict['startdate'], "%m/%d/%Y") if 'startdate' in request_dict else None
  end_date = datetime.datetime.strptime(request_dict['enddate'], "%m/%d/%Y") if 'enddate' in request_dict else None
  dashboard_summary, summary_start_date = summary_util(handle, filters, start_date, end_date)
  fstart_date, fend_date, following_raw_data, followers_raw_data, engagement_rate_raw_data, media_likes_raw_data = chart_util(handle, filters, start_date, end_date)
  media_likes_mv_avg = mv_avg_util(handle, filters, start_date, end_date)
  return followers_today, engagement_today, daily_activity, monthly_activity, dashboard_summary, summary_start_date, filters,\
            fstart_date, fend_date, following_raw_data, followers_raw_data, engagement_rate_raw_data, media_likes_raw_data, media_likes_mv_avg


@app.route("/ig/filters", methods = ["POST"])
def set_filters():
    print(request.form.getlist('filters'))
    print(session)
    session['_filters'] = request.form.getlist('filters')
    print(session)
    return jsonify(msg = "Filters updated. Please refresh the page.")

@app.route("/ig/report/store", methods = ["POST"])
def store_report():
    print("Storing reports")
    blobf = request.files['content']
    fn = request.form['filename']
    filename = secure_filename(fn)
    blobf.save(os.path.join(app.static_folder, 'reports', filename))
    return jsonify(fileloc = url_for('static', filename = "reports/" +  fn))


@app.route("/ig/report/preview/<string:handle>", methods = ["POST"])
@login_required
def preview_report_ui(handle, user = None):
  app.logger.info('Previewing report on  handle %s', handle)
  detail_str = request.form['detail_str']
  fstart_date = datetime.datetime.strptime(request.form['fstart_date'], "%m/%d/%Y")
  fend_date = datetime.datetime.strptime(request.form['fend_date'], "%m/%d/%Y")
  print(request.form['dashboard_summary'])
  dashboard_summary = eval(request.form['dashboard_summary'])
  print(dashboard_summary)
  summary_start_date = request.form['summary_start_date']
  print(detail_str, fstart_date, fend_date, dashboard_summary, summary_start_date)
  following_raw_data = eval(request.form['following_raw_data'])
  followers_raw_data = eval(request.form['followers_raw_data'])
  media_likes_raw_data = eval(request.form['media_likes_raw_data'])
  engagement_rate_raw_data = eval(request.form['engagement_rate_raw_data'])
  print(following_raw_data)
  media_likes_mv_avg = eval(request.form['media_likes_mv_avg'])
  daily_activity = eval(request.form['daily_activity'])
  monthly_activity = eval(request.form['monthly_activity'])
  followers_today = request.form['followers_today']
  engagement_today = float(request.form['engagement_today']) * 100.
  logofile = request.form['logofile']

  return render_template('preview.html', logo = logofile, all_filters = FILTER_DICT, filters = session.get("_filters", ALL_FILTERS), lf = session.get("_filters", ALL_FILTERS)[-1],\
                        handle = handle, iprofile_pic = get_insta_profile_pic(handle), detail_str = detail_str, fstart_date = '{:%m-%d-%Y}'.format(fstart_date), \
                        fend_date = '{:%m-%d-%Y}'.format(fend_date), dashboard_summary = dashboard_summary, summary_start_date = summary_start_date,\
                        following_raw_data = following_raw_data, followers_raw_data = followers_raw_data,  media_likes_raw_data = media_likes_raw_data, \
                        engagement_rate_raw_data = engagement_rate_raw_data, media_likes_mv_avg = media_likes_mv_avg, daily_activity = daily_activity, \
                        monthly_activity = monthly_activity, followers_today = followers_today, engagement_today = engagement_today)

@app.route("/ig/<string:handle>", methods = ["GET", "POST"])
@login_required
def instaboard(handle, user=None):
  app.logger.info('%s is checking handle %s', user.email, handle)
  accounts = sorted([x.instagram_id for x in user.iprofiles])
  if handle not in accounts:
    session.clear()
    return render_template('login.html', msg = "Not a registered account to monitor.")
  detail_str = "the past 14 days" if request.method == "GET" else " between %s and %s" % (request.form['startdate'], request.form['enddate'])

  request_dict = request.form if request.method == "POST" else {}
  followers_today, engagement_today, daily_activity, monthly_activity, dashboard_summary, summary_start_date, filters, \
  fstart_date, fend_date, following_raw_data, followers_raw_data, engagement_rate_raw_data, media_likes_raw_data, media_likes_mv_avg = \
            get_board_data(handle, request_dict)

  return render_template('instaboard.html', roles = [x.name for x in user.roles], accounts = accounts, username = user.username.upper(), \
                        profile_pic = url_for('static', filename = 'logos/'+user.profile_pic), all_filters = FILTER_DICT, filters = filters, handle = handle, \
                        iprofile_pic = get_insta_profile_pic(handle), detail_str = detail_str, fstart_date = UI_DATE_FS.format(fstart_date), \
                        fend_date = UI_DATE_FS.format(fend_date), dashboard_summary = dashboard_summary, summary_start_date = summary_start_date,\
                        following_raw_data = following_raw_data, followers_raw_data = followers_raw_data,  media_likes_raw_data = media_likes_raw_data, \
                        engagement_rate_raw_data = engagement_rate_raw_data, media_likes_mv_avg = media_likes_mv_avg, daily_activity = daily_activity, \
                        monthly_activity = monthly_activity, followers_today = followers_today, engagement_today = engagement_today)

@app.route("/", methods = ["GET"])
@app.route("/instaaccounts", methods = ["GET", "POST"])
@login_required
def instaaccounts(user = None):
  filters = session.get("_filters", ALL_FILTERS)
  existing_accounts = sorted([x.instagram_id for x in user.iprofiles])
  if request.method == "GET":
    print(user.email)
    return render_template('instaaccounts.html', roles = [x.name for x in user.roles], accounts = existing_accounts, username = user.username.upper(), \
                            profile_pic = url_for('static', filename = 'logos/'+user.profile_pic), all_filters = FILTER_DICT, filters = filters, account_limit = user.max_insta_accounts)
  if request.method == "POST":
    updated_accounts = request.form['accounts']
    updated_accounts = list(set(updated_accounts.split(',')))
    correct_accounts = [x.lower() for x in updated_accounts if re.match("^[a-zA-Z0-9_\.]*$", x)]
    incorrect_accounts = list(set(updated_accounts) - set(correct_accounts))
    if len(updated_accounts) != len(correct_accounts):
        return render_template('instaaccounts.html', roles = [x.name for x in user.roles], accounts = existing_accounts, username = user.username.upper(), \
                profile_pic = url_for('static', filename = 'logos/'+user.profile_pic), all_filters = FILTER_DICT, filters = filters, \
                account_limit = user.max_insta_accounts, msg = "Instagram handles can contain alphanumeric character, _ and . The following accounts don't meet that criteria: " + ", ".join(incorrect_accounts))
    if len(correct_accounts) > user.max_insta_accounts:
        return render_template('instaaccounts.html', roles = [x.name for x in user.roles], accounts = existing_accounts, username = user.username.upper(), \
                            profile_pic = url_for('static', filename = 'logos/'+user.profile_pic), all_filters = FILTER_DICT, filters = filters, \
                            account_limit = user.max_insta_accounts, msg = "You cannot monitor more than %d accounts"%user.max_insta_accounts)

    delete_accounts = user.iprofiles
    for x in delete_accounts:
        user.iprofiles.remove(x)

    profiles = []
    for x in correct_accounts:
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
    return render_template('instaaccounts.html', roles = [x.name for x in user.roles], accounts = sorted([x.instagram_id for x in user.iprofiles]), \
            username = user.username.upper(), profile_pic = url_for('static', filename = 'logos/'+user.profile_pic), all_filters = FILTER_DICT, filters = filters, \
            account_limit = user.max_insta_accounts, msg = "Updated the account handles you are monitoring. Come back tomorrow for some interesting info!")

  session.clear()
  return render_template('login.html', msg = "Not allowed to do perform this action.")

@app.route("/admin")
@login_required
def admin(user = None):
    filters = session.get("_filters", ALL_FILTERS)
    if not 'admin' in [x.name for x in user.roles]:
        session.clear()
        return render_template('login.html', msg = "Not allowed to do perform this action.")
    all_users = User.query.all()
    return render_template('admin.html', roles = [x.name for x in user.roles], accounts = sorted([x.instagram_id for x in user.iprofiles]),\
                username = user.username.upper(), profile_pic = url_for('static', filename = 'logos/'+user.profile_pic), all_filters = FILTER_DICT, filters = filters, all_users = all_users)

@app.route("/admin/<int:id>/max_accounts", methods = ["POST"])
@login_required
def max_acc_edit(id, user = None):
    print(user)
    if not 'admin' in [x.name for x in user.roles]:
        session.clear()
        return render_template('login.html', msg = "Not allowed to do perform this action.")
    eduser = User.query.filter_by(id = id).first()
    eduser.max_insta_accounts = int(request.form['value'])
    db.session.add(eduser)
    db.session.commit()

    all_users = User.query.all()
    return render_template('admin.html', roles = [x.name for x in user.roles], accounts = [x.instagram_id for x in user.iprofiles], \
            username = user.username.upper(), profile_pic = url_for('static', filename = 'logos/'+user.profile_pic), all_filters = FILTER_DICT, filters = filters, all_users = all_users)

@app.route('/login', methods = ['GET', 'POST'])
def login():
  print(request)
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
  filters = session.get("_filters", ALL_FILTERS)
  tiers = Tier.query.all()
  return render_template('upgrade.html', roles = [x.name for x in user.roles], accounts = [x.instagram_id for x in user.iprofiles], \
            username = user.username.upper(), profile_pic = url_for('static', filename = 'logos/'+user.profile_pic), all_filters = FILTER_DICT, filters = filters, \
            current_tier = user.tier.name, tiers = tiers)

@app.route('/ppsuccess/<int:planid>', methods = ["GET"])
@login_required
def upgradeplansuccess(planid, user = None):
    filters = session.get("_filters", ALL_FILTERS)
    print(request.args)
    tiers = Tier.query.all()
    if request.args['st'].lower().strip() != "completed":
        return render_template('upgrade.html', roles = [x.name for x in user.roles], accounts = [x.instagram_id for x in user.iprofiles], \
                        username = user.username.upper(), profile_pic = url_for('static', filename = 'logos/'+user.profile_pic), all_filters = FILTER_DICT, filters = filters, \
                        current_tier = user.tier.name, tiers = tiers, msg = "It looks like your transaction didn't go through. Please contact admin in case amount has been withdrawn.")

    paid_amt = request.args['amt'].strip()
    if paid_amt != "":
        return render_template('upgrade.html', roles = [x.name for x in user.roles], accounts = [x.instagram_id for x in user.iprofiles], \
                    username = user.username.upper(), profile_pic = url_for('static', filename = 'logos/'+user.profile_pic), all_filters = FILTER_DICT, filters = filters, \
                    current_tier = user.tier.name, tiers = tiers, msg = "It looks like you haven't paid yet. Please contact admin in case amount has been withdrawn.")

    mod_tier = Tier.filter_by(id = planid).first()
    if not mod_tier:
        return render_template('upgrade.html', roles = [x.name for x in user.roles], accounts = [x.instagram_id for x in user.iprofiles], \
                    username = user.username.upper(), profile_pic = url_for('static', filename = 'logos/'+user.profile_pic), all_filters = FILTER_DICT, filters = filters, \
                    current_tier = user.tier.name, tiers = tiers, msg = "Invalid tier. Please choose from the list of tiers we have.")

    if int(paid_amt) != mod_tier.price_pm:
        return render_template('upgrade.html', roles = [x.name for x in user.roles], accounts = [x.instagram_id for x in user.iprofiles], \
                    username = user.username.upper(), profile_pic = url_for('static', filename = 'logos/'+user.profile_pic), all_filters = FILTER_DICT, filters = filters, \
                    current_tier = user.tier.name, tiers = tiers, msg = "This is not the correct amount for " + mod_tier.name + " plan. Please ensure that you are on the subscription of  " + str(mod_tier.price_pm) + " per month.")

    user.tier = mod_tier
    user.max_insta_accounts = mod_tier.max_accounts
    db.session.add(user)
    db.session.commit()
    print("Updated to user tier " + user.tier.name)
    return render_template('upgrade.html', roles = [x.name for x in user.roles], accounts = [x.instagram_id for x in user.iprofiles], \
                username = user.username.upper(), profile_pic = url_for('static', filename = 'logos/'+user.profile_pic), all_filters = FILTER_DICT, filters = filters, \
                current_tier = user.tier.name, tiers = tiers)


@app.route('/ppcancel/<int:planid>', methods = ["GET"])
@login_required
def upgradeplancancel(planid, user = None):
    filters = session.get("_filters", ALL_FILTERS)
    tiers = Tier.query.all()
    return render_template('upgrade.html', roles = [x.name for x in user.roles], accounts = [x.instagram_id for x in user.iprofiles], \
                username = user.username.upper(), profile_pic = url_for('static', filename = 'logos/'+user.profile_pic), all_filters = FILTER_DICT, filters = filters, \
                current_tier = user.tier.name, tiers = tiers, msg = "Your payment was cancelled.")

@app.route("/upgrade/<int:planid>")
@login_required
def upgrade_plan(planid, user = None):
  filters = session.get("_filters", ALL_FILTERS)
  tiers = Tier.query.all()
  tier = Tier.query.filter_by(id = planid).first()
  if not tier:
    return render_template('upgrade.html', roles = [x.name for x in user.roles], accounts = [x.instagram_id for x in user.iprofiles], \
                username = user.username.upper(), profile_pic = url_for('static', filename = 'logos/'+user.profile_pic), all_filters = FILTER_DICT, filters = filters, \
                current_tier = user.tier.name, tiers = tiers, msg = "Invalid tier. Please choose from the list of tiers we have.")
  if user.tier.id == tier.id:
    return render_template('upgrade.html', roles = [x.name for x in user.roles], accounts = [x.instagram_id for x in user.iprofiles], \
                username = user.username.upper(), profile_pic = url_for('static', filename = 'logos/'+user.profile_pic), all_filters = FILTER_DICT, filters = filters, \
                current_tier = user.tier.name, tiers = tiers, msg = "This is your current tier. Nothing to do.")

  paypalr = "https://www.paypal.com/cgi-bin/webscr?cmd=_s-xclick&hosted_button_id=%s" % tier.paypal_button_link
  return redirect(paypalr)


@app.route('/user', methods = ['GET', 'POST'])
@login_required
def app_user(user = None):
  print("Upload folder", app.config['UPLOAD_FOLDER'])
  filters = session.get("_filters", ALL_FILTERS)
  if request.method == 'GET':
    return render_template('profile.html', roles = [x.name for x in user.roles], accounts = [x.instagram_id for x in user.iprofiles], \
                username = user.username.upper(), profile_pic = url_for('static', filename = 'logos/'+user.profile_pic), all_filters = FILTER_DICT, filters = filters, email = user.email)
  if request.method == "POST":
    if request.form['username'] != '':
        user.username = request.form['username']

    if request.form['password'] != request.form['cpassword']:
        return render_template('profile.html', roles = [x.name for x in user.roles], accounts = [x.instagram_id for x in user.iprofiles], \
                username = user.username.upper(), profile_pic = url_for('static', filename = 'logos/'+user.profile_pic), all_filters = FILTER_DICT, filters = filters, email = user.email)

    if request.form['password'] != '':
        user.hash_password(request.form['password'])

    pp_file = request.files['logo']
    print(pp_file)
    if pp_file.filename == '':
      return render_template('profile.html', roles = [x.name for x in user.roles], accounts = [x.instagram_id for x in user.iprofiles], \
            username = user.username.upper(), profile_pic = url_for('static', filename = 'logos/'+user.profile_pic), all_filters = FILTER_DICT, filters = filters, \
            email = user.email, msg = "Please upload a valid file. Accepted filetypes are png and jpg. Maximum possible file size is 4MB.")

    if not allowed_file(pp_file.filename):
      return render_template('profile.html', roles = [x.name for x in user.roles], accounts = [x.instagram_id for x in user.iprofiles], \
            username = user.username.upper(), profile_pic = url_for('static', filename = 'logos/'+user.profile_pic), all_filters = FILTER_DICT, filters = filters, \
            email = user.email, msg = "Accepted filetypes are png and jpg. Maximum possible file size is 4MB.")

    filename = secure_filename(pp_file.filename)
    filename = str(user.id)+"_"+filename
    pp_file.save(os.path.join(ROOT_DIR, app.config['UPLOAD_FOLDER'], filename))

    user.profile_pic = filename
    db.session.add(user)
    db.session.commit()
    return render_template('profile.html', roles = [x.name for x in user.roles], accounts = [x.instagram_id for x in user.iprofiles], \
            username = user.username.upper(), profile_pic = url_for('static', filename = 'logos/'+user.profile_pic), all_filters = FILTER_DICT, filters = filters, \
            email = user.email, msg = "User details upgraded successfully.")

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
