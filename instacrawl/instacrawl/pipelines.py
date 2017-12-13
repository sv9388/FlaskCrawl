# -*- coding: utf-8 -*-
import sys
sys.path.append("/home/smsilo/insta")
from insta_cfg import DB_NAME
import sqlite3

stmt_fs = """insert into iprofile_data (iprofile_id, date, followers_count, following_count, media_likes, engagement_rate) values ( '%s', '%s', %d, %d, %d, %f )"""
class InstacrawlPipeline(object):
    def __init__(self):
        self.conn = sqlite3.connect('/home/smsilo/insta/instamanager.db')

    def process_item(self, item, spider):
        c = self.conn.cursor()
        try:
            date = '{:%Y-%m-%d %H:%M:%S}'.format(item['date'])
            stmt = stmt_fs % (item['instagram_id'], date, item['followers_count'], item['following_count'], \
                            item['media_likes'], item['engagement_rate'])
            print(stmt)
            c.execute(stmt)
            self.conn.commit()
        except:
            raise
        finally:
            c.close()
        return item
