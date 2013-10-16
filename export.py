# -*- coding: utf-8 -*-
import logging
import logging.handlers
import argparse
import sys
import oauth2 as oauth
import simplejson
import urllib


LOG_FILENAME = 'tw_export.log'
FORMAT = '%(name)s:%(levelname)s %(module)s:%(lineno)d:%(asctime)s  %(message)s'
logger = logging.getLogger('tw_export')


def send_oauth_req(url, consumer_key, consumer_secret, token, http_method="GET", post_body=None, http_headers=None):
    consumer = oauth.Consumer(consumer_key, consumer_secret)
    client = oauth.Client(consumer, token)
    resp, content = client.request(url, method=http_method, body=post_body, headers=http_headers, force_auth_header=True)
    logger.debug(u'Url %s, got response %s', url, resp)
    if resp['status'] != '200':
        raise Exception(u'Status is %s, url %s', resp['status'], url)
    return content


def user_timeline(key, secret, token, timeline_options):
    qs = urllib.urlencode(timeline_options)
    url = 'https://api.twitter.com/1.1/statuses/user_timeline.json'
    if qs:
        url = '{0}?{1}'.format(url, qs)
    return send_oauth_req(url, key, secret, token)


def save_timeline(timeline):
    json = simplejson.loads(timeline)
    for obj in json:
        pass
        print obj


def export(consumer_key, consumer_secret, token, timeline_options):
    logger.info(u'Export is started')
    try:
        t = user_timeline(consumer_key, consumer_secret, token, timeline_options)
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

    args = parser.parse_args()

    logging.basicConfig(stream=sys.stdout, format=FORMAT, level=getattr(logging, args.loglevel))
    handler = logging.handlers.RotatingFileHandler(LOG_FILENAME, maxBytes=10 * 1024 * 1024, backupCount=1000)
    fmt = logging.Formatter(FORMAT)
    handler.setFormatter(fmt)
    logger.setLevel(getattr(logging, args.loglevel))
    logger.addHandler(handler)

    token = oauth.Token(key=args.token, secret=args.token_secret)

    timeline_options = dict()
    for p in [('count', args.count), ('max_id', args.max_id), ('since_id', args.since_id)]:
        k, v = p
        if v:
            timeline_options[k] = v

    export(args.consumer_key, args.consumer_secret, token, timeline_options)
