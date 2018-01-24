import datetime, requests, json

DB_DATE_FS = '{:%Y-%m-%d 00:00:00}'
default_summary = {'Follower Change' : 0, 'Following Change' : 0, 'Post Change' : 0, 'Engagement Rate Change' : "0.0 %"}
diffact = lambda s, e : [e, "{:.2f} %".format((s-e)*100./s if s > 0 else 0.0), 0] if s>e else [e, "{:.2f} %".format((e-s)*100./e if e > 0 else 0.0), 1]

from models import IprofileData

def get_likes_moving_average(handle, start_date, end_date):
  iprofiles = IprofileData.query.filter_by(iprofile_id = handle).filter(IprofileData.date >= DB_DATE_FS.format(start_date)).filter(IprofileData.date <= DB_DATE_FS.format(end_date)).order_by(IprofileData.date).all()
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


def get_chart_data(handle, start_date, end_date, filters):
  reqd = set(filters)
  iprofiles = IprofileData.query.filter_by(iprofile_id = handle).filter(IprofileData.date >= DB_DATE_FS.format(start_date)).filter(IprofileData.date <= DB_DATE_FS.format(end_date)).order_by(IprofileData.date).all()
  db_date = lambda dt : dt.strftime('%Y/%m/%d')
  following_raw_data =   [[db_date(x.date), x.following_count] for x in iprofiles ]
  followers_raw_data =   [[db_date(x.date), x.followers_count] for x in iprofiles] if "followersc" in reqd or "fvsmnlikec" in reqd else None
  engagement_rate_raw_data = [[db_date(x.date), x.engagement_rate] for x in iprofiles] if "engagementc" in reqd else None
  media_likes_raw_data = [[db_date(x.date), x.media_likes] for x in iprofiles] if "likesc" in reqd else None
  return following_raw_data, followers_raw_data, engagement_rate_raw_data, media_likes_raw_data

def get_summary(handle, start_date, end_date):
    startp = IprofileData.query.filter_by(iprofile_id = handle).filter_by(date = DB_DATE_FS.format(start_date)).first()
    endp = IprofileData.query.filter_by(iprofile_id = handle).filter_by(date = DB_DATE_FS.format(end_date)).first()
    if not endp:
        return default_summary
    return {'Follower Change' : endp.followers_count - (startp.followers_count if startp else 0),
                       'Following Change' : endp.following_count -  (startp.following_count if startp else 0),
                       'Post Change' : endp.posts_count -  (startp.posts_count if startp else 0),
                       'ER Change' : "{:3.1f} %".format((endp.engagement_rate - (startp.engagement_rate if startp else 0))*100)}


def get_activity(handle):
  tstart_date = datetime.datetime.today()-datetime.timedelta(days=1)
  mstart_date = datetime.datetime.today()-datetime.timedelta(days=31)
  end_date = datetime.datetime.today()
  tsp = IprofileData.query.filter_by(iprofile_id = handle).filter_by(date = DB_DATE_FS.format(tstart_date)).first()
  msp = IprofileData.query.filter_by(iprofile_id = handle).filter_by(date = DB_DATE_FS.format(mstart_date)).first()
  ep = IprofileData.query.filter_by(iprofile_id = handle).filter_by(date = DB_DATE_FS.format(end_date)).first()

  if not ep:
    daily_activity = {'following' : 0, 'followers' : 0, 'engagement' : 0, 'likes' : 0}
    monthly_activity = {'following' : 0, 'followers' : 0, 'engagement' : 0, 'likes' : 0}
    return daily_activity, monthly_activity

  deng = diffact(tsp.engagement_rate if tsp else 0, ep.engagement_rate)
  deng = ["{:.2f} %".format(deng[0] *100), deng[1], deng[2]]
  daily_activity = {'following' : diffact(tsp.following_count if tsp else 0, ep.following_count), \
                    'followers' : diffact(tsp.followers_count if tsp else 0, ep.followers_count), \
                    'engagement' : deng, \
                    'likes' : diffact(tsp.posts_count if tsp else 0, ep.posts_count)}#, 'media' : [tsp.media_count if tsp else 0, ep.media_count]})

  meng = diffact(msp.engagement_rate if msp else 0, ep.engagement_rate)
  meng = ["{:.2f} %".format(meng[0] * 100), meng[1], meng[2]]
  monthly_activity = {'following' : diffact(msp.following_count if msp else 0, ep.following_count), \
                      'followers' : diffact(msp.followers_count if msp else 0, ep.followers_count), \
                      'engagement' : meng, \
                      'likes' : diffact(tsp.media_likes if tsp else 0, ep.media_likes)}
  return daily_activity, monthly_activity


def get_insta_profile_pic(handle):
    r = requests.get("""https://www.instagram.com/%s/?__a=1"""%handle)
    return json.loads(r.content)['user']['profile_pic_url']
