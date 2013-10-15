# -*- coding: utf-8 -*-
import logging
import logging.handlers
import argparse
import sys
import oauth2 as oauth
import simplejson


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


def home_timeline(key, secret, token):
    return send_oauth_req('https://api.twitter.com/1.1/statuses/home_timeline.json', key, secret, token)


def save_timeline(timeline):
    json = simplejson.loads(timeline)
    for obj in json:
        pass
        #print obj


def export(consumer_key, consumer_secret, token=None):
    logger.info(u'Export is started')
    try:
        t = home_timeline(consumer_key, consumer_secret, token)
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

    args = parser.parse_args()

    logging.basicConfig(stream=sys.stdout, format=FORMAT, level=getattr(logging, args.loglevel))
    handler = logging.handlers.RotatingFileHandler(LOG_FILENAME, maxBytes=10 * 1024 * 1024, backupCount=1000)
    fmt = logging.Formatter(FORMAT)
    handler.setFormatter(fmt)
    logger.setLevel(getattr(logging, args.loglevel))
    logger.addHandler(handler)

    token = oauth.Token(key=args.token, secret=args.token_secret) if args.token and args.token_secret else None
    export(args.consumer_key, args.consumer_secret, token)
