# -*- coding: utf-8 -*-
import base64
import logging
import logging.handlers
import argparse
import sys
import os
import simplejson
import requests
import multiprocessing

HTML = 'h'
IMAGE = 'i'
LOG_FILENAME = 'downloader.log'
FORMAT = '%(name)s:%(levelname)s %(module)s:%(lineno)d:%(asctime)s  %(message)s'
logger = logging.getLogger('downloader')


def get_page(url, content_type, timeout=20):
    try:
        res = requests.get(url, timeout=timeout)
        if res.status_code == requests.codes.ok:
            if content_type == HTML:
                return res.text
            elif content_type == IMAGE:
                return res.content
    except requests.HTTPError, e:
        logger.error(u'got http error %s', e)
    except requests.exceptions.Timeout:
        logger.error(u'Timeout fired')
    except requests.exceptions.SSLError, e:
        logger.error(u'SSL error %s ', e)


class ContentToFile(object):
    """Save page to file"""

    root = './'

    def __init__(self, url, content_type, id_str):
        self._url = url
        self._content_type = content_type
        self._id_str = id_str

    @property
    def filename(self):
        return os.path.join(ContentToFile.root, './{0}_{1}'.format(self._id_str, base64.urlsafe_b64encode(self._url)))

    def __call__(self):
        content = get_page(self._url, self._content_type)
        logger.debug(u'Got page %s', self._url)
        if self._content_type == HTML:
            with open(self.filename, 'w') as f:
                f.write(content.encode('utf8'))
        elif self._content_type == IMAGE:
            with open(self.filename, 'wb') as f:
                f.write(content)


def download(urls, max_process):
    """download web pages
       urls - iterable
    """
    logger.info(u'Begin')
    if max_process:
        pool = multiprocessing.Pool(max_process)
        for url in urls:
            pool.apply_async(ContentToFile(*url))

        logger.info(u'Waiting')
        pool.close()
        pool.join()
    else:
        for url in urls:
            apply(ContentToFile(*url))


def get_urls_from_files(root):

    def file_gen():
        for r, _, files in os.walk(root):
            for f in files:
                if f.endswith('.json'):
                    yield os.path.join(r, f)

    for json_file in file_gen():
        with open(json_file) as f:
            try:
                json = simplejson.load(f)
                id_str = json['id_str']
                for url in json['urls']:
                    yield (url, HTML, id_str)

                for url in json['media']:
                    yield (url, IMAGE, id_str)
            except simplejson.JSONDecodeError:
                logger.error(u'wrong file format')
            except KeyError:
                logger.error(u'wrong json format')


if __name__ == "__main__":
    parser = argparse.ArgumentParser()

    parser.add_argument("--loglevel", action="store", dest="loglevel", default='DEBUG', choices=['DEBUG', 'INFO', 'WARNINGS', 'ERROR'], help=u"Уровень логгирования скрипта")

    parser.add_argument("--dir", action="store", dest="dir", default='./', help=u"Path to directory")

    parser.add_argument("--max-process", action="store", dest="max_process", type=int, default=2, help=u"Max processes")

    args = parser.parse_args()

    logging.basicConfig(stream=sys.stdout, format=FORMAT, level=getattr(logging, args.loglevel))
    handler = logging.handlers.RotatingFileHandler(LOG_FILENAME, maxBytes=10 * 1024 * 1024, backupCount=1000)
    fmt = logging.Formatter(FORMAT)
    handler.setFormatter(fmt)
    logger.setLevel(getattr(logging, args.loglevel))
    logger.addHandler(handler)

    urls = get_urls_from_files(args.dir)
    ContentToFile.root = args.dir
    download(urls, args.max_process)
