# -*- coding: utf-8 -*-
import logging
import logging.handlers
import argparse
import sys
import os
import simplejson
import oauth2 as oauth
from evernote.api.client import EvernoteClient
from evernote.edam.type import ttypes
from evernote.edam.error import ttypes as Errors
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


class TweetToEvernote(object):
    """Save tweets to Evernote"""
    def __init__(self, ev_token, notebook_name='My tweets'):
        self._token = ev_token
        client = EvernoteClient(token=ev_token, sandbox=True)
        self._note_store = client.get_note_store()
        self._notebook = self._create_notebook(notebook_name)

    def _create_notebook(self, notebook_name):
        notebooks = self._note_store.listNotebooks(self._token)
        for n in notebooks:
            if n.name == notebook_name:
                return n
        notebook = ttypes.Notebook()
        notebook.name = notebook_name
        return self._note_store.createNotebook(notebook)
        
    def make_note(self, note_title, note_body):
        body = "<?xml version=\"1.0\" encoding=\"UTF-8\"?>"
        body += "<!DOCTYPE en-note SYSTEM \"http://xml.evernote.com/pub/enml2.dtd\">"
        body += "<en-note>%s</en-note>" % note_body

        note = ttypes.Note()
        note.title = note_title
        note.content = body
        note.notebookGuid = self._notebook.guid

        try:
            note = self._note_store.createNote(self._token, note)
        except Errors.EDAMUserException, e:
            logger.exception(u'Got error %s', e)
        except Errors.EDAMNotFoundException, e:
            logger.exception(u'Got error %s', e)

    def __call__(self, tweet):
        self.make_note(tweet['id_str'], tweet['text'].encode('utf8'))


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

    parser.add_argument("--loglevel", action="store", dest="loglevel", default='DEBUG', choices=['DEBUG', 'INFO', 'WARNINGS', 'ERROR'], help=u"Log level")

    parser.add_argument("--destination", action="store", dest="dest", default='disk', choices=['disk', 'Evernote'], help=u"Where save tweets")

    tw_group = parser.add_argument_group('Twitter options')

    tw_group.add_argument("--tw-consumer-key", action="store", dest="tw_consumer_key", required=True, help=u"Twitter consumer Key")

    tw_group.add_argument("--tw-consumer-secret", action="store", dest="tw_consumer_secret", required=True, help=u"Twitter consumer secret")

    tw_group.add_argument("--tw-token", action="store", dest="tw_token", required=True, help=u"Twitter token")

    tw_group.add_argument("--tw-token-secret", action="store", dest="tw_token_secret", required=True, help=u"Twitter token secret")

    parser.add_argument("--ev-token", action="store", dest="ev_token", help=u"Evernote developer token")

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

    token = oauth.Token(key=args.tw_token, secret=args.tw_token_secret)
    timeline_options = TimelineOptions(args.count, args.max_id, args.since_id, args.trim_user)

    if args.dest == 'disk':
        export(args.tw_consumer_key, args.tw_consumer_secret, token, timeline_options, TweetToFile(args.dir))
    elif args.dest == 'Evernote':
        export(args.tw_consumer_key, args.tw_consumer_secret, token, timeline_options, TweetToEvernote(args.ev_token))
