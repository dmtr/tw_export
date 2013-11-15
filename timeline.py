# -*- coding: utf-8 -*-
import logging
import simplejson
import time
import urllib
from collections import namedtuple
import oauth2 as oauth


logger = logging.getLogger('timeline')
TimelineOptions = namedtuple('TimelineOptions', 'count max_id since_id trim_user')


def send_oauth_req(url, consumer_key, consumer_secret, token, http_method="GET", post_body=None, http_headers=None):
    consumer = oauth.Consumer(consumer_key, consumer_secret)
    client = oauth.Client(consumer, token)
    return client.request(url, method=http_method, body=post_body, headers=http_headers, force_auth_header=True)


class Timeline(object):
    """Iterator over timeline"""
    def __init__(self, consumer_key, consumer_secret, token, timeline_options, delay_func=time.sleep):
        self._consumer_key = consumer_key
        self._consumer_secret = consumer_secret
        self._token = token
        self._count = timeline_options.count
        self._max_id = timeline_options.max_id
        self._since_id = timeline_options.since_id
        self._trim_user = timeline_options.trim_user
        self._first_request = True
        self._timeline = []
        self._export_all = not (timeline_options.max_id or timeline_options.since_id)
        self._delay = 0
        self._delay_func = delay_func

    @property
    def max_id(self):
        return self._max_id

    @property
    def since_id(self):
        return self._since_id

    def __repr__(self):
        return 'Timeline, max_id: {self.max_id}, since_id: {self.since_id}'.format(self=self)

    def _prepare_options(self):
        o = dict()
        if self._max_id:
            o['max_id'] = self._max_id
        if self._since_id and self._first_request:
            o['since_id'] = self._since_id
        o['count'] = self._count
        o['trim_user'] = self._trim_user
        return o

    def _check_response(self, resp):
        if resp['status'] not in ('200', '429'):
            raise Exception(u'Status is {0}'.format(resp['status']))

        remaining = int(resp['x-rate-limit-remaining'])
        if remaining == 0:
            reset = int(resp['x-rate-limit-reset'])
            self._delay = reset - int(time.time())

    def _get_user_timeline(self):
        if self._delay:
            logger.debug(u'Waiting %s secs', self._delay)
            self._delay_func(self._delay)
            self._delay = 0

        qs = urllib.urlencode(self._prepare_options())
        url = 'https://api.twitter.com/1.1/statuses/user_timeline.json'
        if qs:
            url = '{0}?{1}'.format(url, qs)
        resp, content = send_oauth_req(url, self._consumer_key, self._consumer_secret, self._token)
        logger.debug(u'Url %s, got response %s', url, resp)
        self._check_response(resp)
        return simplejson.loads(content)

    def next(self):
        if self._first_request:
            self._timeline = self._get_user_timeline()
            self._since_id = self._timeline[0]['id'] if self._timeline else 0
            self._first_request = False
        elif not self._timeline and self._export_all:
            self._timeline = self._get_user_timeline()

        if not self._timeline:
            raise StopIteration

        tw = self._timeline.pop(0)
        self._max_id = tw['id'] - 1
        return tw

    def __iter__(self):
        return self
