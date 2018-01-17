import scrapy, json, logging, datetime, os, psycopg2

insta_fs = "https://www.instagram.com/%s/?__a=1"
MAX_ENGAGEMENT_POSTS = 10
DB_NAME = os.environ.get('DATABASE_URL')

def get_handles():
    conn = psycopg2.connect(DB_NAME)
    c = conn.cursor()
    insta_handles = []
    try:
        c.execute("SELECT instagram_id from iprofile")
        op = c.fetchall()
        insta_handles = list(set([x[0] for x in op]))
    except:
        pass
    c.close()
    return insta_handles

class InstaSpider(scrapy.Spider):
    name = "ifeed"
    def start_requests(self):
        insta_handles = get_handles()
        self.log("Handles =  are %s"%str(insta_handles), level = logging.INFO)
        for url in insta_handles:
            yield scrapy.Request(url= insta_fs % url, callback=self.parse)

    def parse(self, response):
        idata = json.loads(response.body.decode())
        today = datetime.date.today()
        followed_by = idata['user']['followed_by']['count']
        follows =  idata['user']['follows']['count']
        posts = idata['user']['media']['count']
        media = idata['user']['media']['nodes']
        max_pc = min(len(media), 10)
        media_avg_likes = 0
        if max_pc > 0:
            media_avg_likes = sum([ media[i]['likes']['count'] for i in range(max_pc)])/max_pc
        end = min(len(media), MAX_ENGAGEMENT_POSTS + 1)
        engagement_rate =  sum([x['likes']['count'] for x in media[1:end]]) * 1./(MAX_ENGAGEMENT_POSTS * followed_by) if followed_by > 0 else 0.0
        data = {'instagram_id' : idata['user']['username'], 'followers_count' : followed_by, 'following_count' : follows , 'date' : today, 'media_likes' : media_avg_likes, 'posts_count' : posts, 'engagement_rate' : engagement_rate}
        return data
