# -*- coding: utf-8 -*-
import logging
import logging.handlers
import argparse
import sys
import oauth2 as oauth
import os
import simplejson
import urllib
from collections import namedtuple


TimelineOptions = namedtuple('TimelineOptions', 'count max_id since_id trim_user')
LOG_FILENAME = 'tw_export.log'
FORMAT = '%(name)s:%(levelname)s %(module)s:%(lineno)d:%(asctime)s  %(message)s'
logger = logging.getLogger('tw_export')


def send_oauth_req(url, consumer_key, consumer_secret, token, http_method="GET", post_body=None, http_headers=None):
    consumer = oauth.Consumer(consumer_key, consumer_secret)
    client = oauth.Client(consumer, token)
    resp, content = client.request(url, method=http_method, body=post_body, headers=http_headers, force_auth_header=True)
    logger.debug(u'Url %s, got response %s', url, resp)
    if resp['status'] != '200':
        raise Exception(u'Status is {0}, url {1}'.format(resp['status'], url))
    return content


class Timeline(object):
    """Iterator over timeline"""
    def __init__(self, consumer_key, consumer_secret, token, timeline_options):
        self._consumer_key = consumer_key
        self._consumer_secret = consumer_secret
        self._token = token
        self._count = timeline_options.count
        self._max_id = timeline_options.max_id
        self._since_id = timeline_options.since_id
        self._trim_user = timeline_options.trim_user
        self._first_request = True
        self._timeline = []

    @property
    def max_id(self):
        return self._max_id

    @property
    def since_id(self):
        return self._since_id

    def __repr__(self):
        return u'Timeline, max_id: {self.max_id}, since_id: {self.since_id}'.format(self=self)

    def _prepare_options(self):
        o = dict()
        if self._max_id:
            o['max_id'] = self._max_id
        if self._since_id and self._first_request:
            o['since_id'] = self._since_id
        o['count'] = self._count
        o['trim_user'] = self._trim_user
        return o

    def _get_user_timeline(self):
        qs = urllib.urlencode(self._prepare_options())
        url = 'https://api.twitter.com/1.1/statuses/user_timeline.json'
        if qs:
            url = '{0}?{1}'.format(url, qs)
        res = send_oauth_req(url, self._consumer_key, self._consumer_secret, self._token)
        return simplejson.loads(res)

    def next(self):
        if not self._timeline:
            self._timeline = self._get_user_timeline()
            if self._first_request:
                self._since_id = self._timeline[0]['id'] if self._timeline else 0
                self._first_request = False

        if not self._timeline:
            raise StopIteration

        tw = self._timeline.pop(0)
        self._max_id = tw['id'] - 1
        return tw

    def __iter__(self):
        return self


class TweetToFile(object):
    """Save tweets to disk"""
    def __init__(self, root='./'):
        self._root = root

    def __call__(self, tweet):
        with open(os.path.join(self._root, tweet['id_str']), 'w') as f:
            text = tweet['text']
            f.write(text.encode('utf8'))


def export(consumer_key, consumer_secret, token, timeline_options, save_timeline=TweetToFile()):
    logger.info(u'Export is started')
    try:
        timeline = Timeline(consumer_key, consumer_secret, token, timeline_options)
        for t in timeline:
            logger.debug(u'Got tweet %s from timeline %s', t, timeline)
            save_timeline(t)
    except Exception, e:
        logger.error(u'Got error %s', e)
    logger.info(u'Export is finished')


if __name__ == "__main__":
    parser = argparse.ArgumentParser()

    parser.add_argument("--loglevel", action="store", dest="loglevel", default='DEBUG', choices=['DEBUG', 'INFO', 'WARNINGS', 'ERROR'], help=u"Уровень логгирования скрипта")

    parser.add_argument("--consumer-key", action="store", dest="consumer_key", help=u"Key")

    parser.add_argument("--consumer-secret", action="store", dest="consumer_secret", help=u"Secret")

    parser.add_argument("--token", action="store", dest="token", help=u"Token")

    parser.add_argument("--token-secret", action="store", dest="token_secret", help=u"Token secret")

    parser.add_argument("--count", action="store", dest="count", default=10, help=u"Count")

    parser.add_argument("--max-id", action="store", dest="max_id", default=0, help=u"Max id")

    parser.add_argument("--since-id", action="store", dest="since_id", default=0, help=u"Since id")

    parser.add_argument("--trim-user", action="store", dest="trim_user", default=True, help=u"Trim user info")

    args = parser.parse_args()

    logging.basicConfig(stream=sys.stdout, format=FORMAT, level=getattr(logging, args.loglevel))
    handler = logging.handlers.RotatingFileHandler(LOG_FILENAME, maxBytes=10 * 1024 * 1024, backupCount=1000)
    fmt = logging.Formatter(FORMAT)
    handler.setFormatter(fmt)
    logger.setLevel(getattr(logging, args.loglevel))
    logger.addHandler(handler)

    token = oauth.Token(key=args.token, secret=args.token_secret)
    timeline_options = TimelineOptions(args.count, args.max_id, args.since_id, args.trim_user)
    export(args.consumer_key, args.consumer_secret, token, timeline_options)
