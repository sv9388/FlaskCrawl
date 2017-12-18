# -*- coding: utf-8 -*-

BOT_NAME = 'instacrawl'

SPIDER_MODULES = ['instacrawl.spiders']
NEWSPIDER_MODULE = 'instacrawl.spiders'

# Proxy
RETRY_TIMES = 10
RETRY_HTTP_CODES = [500, 503, 504, 400, 403, 404, 408]
DOWNLOADER_MIDDLEWARES = {
    'scrapy.downloadermiddlewares.retry.RetryMiddleware': 90,
    'scrapy_proxies.RandomProxy': 100,
    'scrapy.downloadermiddlewares.httpproxy.HttpProxyMiddleware': 110,
}
PROXY_LIST = './plist.txt'
PROXY_MODE = 0

# Crawl responsibly by identifying yourself (and your website) on the user-agent
USER_AGENT = 'Mozilla/5.0 (Windows NT 6.1; Win64; x64; rv:47.0) Gecko/20100101 Firefox/47.0'

ROBOTSTXT_OBEY = False
ITEM_PIPELINES = {
    'instacrawl.pipelines.InstacrawlPipeline' : 300
}
