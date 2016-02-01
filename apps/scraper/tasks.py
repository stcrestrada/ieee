import xml.etree.ElementTree as ET
from collections import defaultdict

import requests
from celery import task
from django.db import transaction
from django.db import connection

from apps.scraper.models import ArticleModel, ScrapeHistory

QUERY_URL = 'https://ieeexplore.ieee.org/gateway/ipsSearch.jsp'


def int_if_digit(val):
    if val and val.isdigit():
        val = int(val)
    return val


SPECIAL_PROCESSORS = defaultdict(list)
SPECIAL_PROCESSORS['authors'] = [lambda x: map(lambda x: x and x.strip(), (x or '') and x.split(';'))]
SPECIAL_PROCESSORS['*'] = [int_if_digit]


def parse_doc(elem):
    data = {}
    for child in elem.getchildren():
        prop_name = child.tag
        nested_children = child.getchildren()
        if nested_children:
            prop_value = [ns.text for ns in nested_children]
        else:
            prop_value = child.text
            processors = SPECIAL_PROCESSORS['*'] + SPECIAL_PROCESSORS[prop_name]
            for transform in processors:
                prop_value = transform(prop_value)
        data[prop_name] = prop_value
    return data


@task
def scrape_chunk(params):
    print "Scraping chunk with params {}".format(str(params))
    history = params.get('state_obj')
    if not history:
        history = ScrapeHistory.objects.create(state=ScrapeHistory.STATE_PROCESSING, pub_year=params['py'],
                                               limit=params['hc'], seq_number=params['rs'])
    resp = requests.get(QUERY_URL, params=params, timeout=5)
    try:
        resp.raise_for_status()
    except Exception as e:
        print "ERROR: {}".format(str(e))
        history.state = history.STATE_ERROR
        history.save()
        raise
    tree = ET.fromstring(resp.content)
    children = tree.getchildren()
    if not children:
        raise Exception(children.text)
    document_children = filter(lambda x: x.tag == 'document', children)
    document_objs = map(parse_doc, document_children)
    try:
        with transaction.atomic():
            for doc in document_objs:
                new_art = ArticleModel(article_id=doc['arnumber'], article_data=doc)
                new_art.save()
    except Exception as e:
        print "ERROR: {}".format(str(e))
        history.state = history.STATE_ERROR
        history.save()
        raise
    else:
        print "DONE SCRAPING WITH PARAMS {}".format(str(params))
        history.state = history.STATE_DONE
        history.save()


def sequence_generator(total, chunk_size):
    current = 1
    yield current
    while current + chunk_size <= total:
        current += chunk_size
        yield current


def get_params(year, hc=None, rs=None, state_obj=None):
    params = {'py': year, 'sortfield': 'ti', 'sortorder': 'asc'}
    if hc:
        params['hc'] = hc
    if rs:
        params['rs'] = rs
    if state_obj:
        params['state_obj'] = state_obj
    return params


@task
def scrape_year(year):
    print "Prepping scraping year {}".format(year)
    base_params = get_params(year)
    resp_year = requests.get(QUERY_URL, params=base_params)
    resp_year.raise_for_status()
    tree = ET.fromstring(resp_year.content)
    try:
        node = tree.getchildren()[0]
    except IndexError:
        raise Exception(tree.text)
    assert node.tag == 'totalfound', "Tag not right."
    total_articles = int(node.text)
    chunk_size = ScrapeHistory.LIMIT
    sq_gen = sequence_generator(total_articles, chunk_size)
    args_of_requests = [get_params(year, hc=ScrapeHistory.LIMIT, rs=rs) for rs in sq_gen]
    for each in args_of_requests:
        scrape_chunk.apply_async([each])
    print "Done prepping scraping year {}".format(year)


@task
def scrape_all():
    for each in range(1872, 2017):
        scrape_year.apply_async([each])


@task
def scrape_failed_chunks():
    failed = ScrapeHistory.objects.exclude(state=ScrapeHistory.STATE_DONE).all()
    for each in failed:
        params = get_params(each.pub_year, hc=each.limit, rs=each.seq_number, state_obj=each)
        print "REDOING: {}".format(str(params))
        scrape_chunk.apply_async([params])


@task
def drop_dups():
    print "Dropping dups!"
    cursor = connection.cursor()
    cursor.execute("""DELETE FROM scraper_articlemodel
    WHERE id IN (SELECT id
          FROM (SELECT id,
                     ROW_NUMBER() OVER (partition BY article_id ORDER BY id) AS rnum
                 FROM scraper_articlemodel) t
          WHERE t.rnum > 1);""")
    print "Done dropping dups!"
