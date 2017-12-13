import json, datetime, requests

insta_id_to_name_fs = "https://www.instagram.com/web/friendships/%s/follow/" #get final redirect url from this.

def get_insta_accounts_by_handles(handles):
    pass
    """
    op_arr = []
    for handle in handles:
        r = requests.get(insta_fs % handle)
        idata = json.loads(r.content)
        today = datetime.date.today()
        followed_by = idata['user']['followed_by']['count']
        follows =  idata['user']['follows']['count']
        media = idata['user']['media']['count']
        engagement_rate =  sum([x['likes']['count'] for x in idata['user']['media']['nodes'][0][1:MAX_ENGAGEMENT_POSTS + 1]]) * 1./(MAX_ENGAGEMENT_POSTS * followed_by)
        data = {'followers_count' : followed_by, 'following_count' : follows , 'date' : today, 'start_post_likes' : media} #TODO: start_post_like = post_likes, engagement_rate =
        op_arr.append({'handle' : data})
    return op_arr
    """

def get_handle_from_id(insta_id):
    pass