# -*- coding: utf-8 -*-

BOT_NAME = 'instacrawl'

SPIDER_MODULES = ['instacrawl.spiders']
NEWSPIDER_MODULE = 'instacrawl.spiders'


# Crawl responsibly by identifying yourself (and your website) on the user-agent
USER_AGENT = 'Mozilla/5.0 (Windows NT 6.1; Win64; x64; rv:47.0) Gecko/20100101 Firefox/47.0'

ROBOTSTXT_OBEY = False
ITEM_PIPELINES = {
        'instacrawl.pipelines.InstacrawlPipeline' : 300
}
