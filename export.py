# -*- coding: utf-8 -*-
import logging
import logging.handlers
import argparse
import sys
import os
import simplejson
import oauth2 as oauth
from timeline import Timeline
from timeline import TimelineOptions


LOG_FILENAME = 'tw_export.log'
FORMAT = '%(name)s:%(levelname)s %(module)s:%(lineno)d:%(asctime)s  %(message)s'
logger = logging.getLogger('tw_export')


def prepare_tweet(tweet):
    try:
        res = dict()
        res['text'] = tweet['text']
        res['created_at'] = tweet['created_at']
        res['id_str'] = tweet['id_str']
        get_url = lambda a: a.get('expanded_url')
        res['media'] = map(get_url, tweet['entities'].get('media', []))
        res['urls'] = map(get_url, tweet['entities'].get('urls', []))
        return res
    except KeyError, e:
        logger.error(u'Key not found %s', e)


class TweetToFile(object):
    """Save tweets to disk"""
    def __init__(self, root='./', prepare_tweet=prepare_tweet):
        if not os.path.isdir(root):
            os.mkdir(root)
        self._root = root
        self._prepare_tweet = prepare_tweet

    def __call__(self, tweet):
        with open(os.path.join(self._root, '{0}.json'.format(tweet['id_str'])), 'w') as f:
            tw = self._prepare_tweet(tweet)
            if tw:
                simplejson.dump(tw, f)


def export(consumer_key, consumer_secret, token, timeline_options, save_timeline):
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

    parser.add_argument("--dir", action="store", dest="dir", default='./', help=u"Path to directory")

    args = parser.parse_args()

    logging.basicConfig(stream=sys.stdout, format=FORMAT, level=getattr(logging, args.loglevel))
    handler = logging.handlers.RotatingFileHandler(LOG_FILENAME, maxBytes=10 * 1024 * 1024, backupCount=1000)
    fmt = logging.Formatter(FORMAT)
    handler.setFormatter(fmt)
    logger.setLevel(getattr(logging, args.loglevel))
    logger.addHandler(handler)

    token = oauth.Token(key=args.token, secret=args.token_secret)
    timeline_options = TimelineOptions(args.count, args.max_id, args.since_id, args.trim_user)
    export(args.consumer_key, args.consumer_secret, token, timeline_options, TweetToFile(args.dir))
