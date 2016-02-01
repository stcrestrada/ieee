from django.db import transaction
from collections import namedtuple
from collections import defaultdict
import requests
import xml.etree.ElementTree as ET

from celery import task

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
    history = ScrapeHistory.objects.create(state=ScrapeHistory.STATE_PROCESSING, pub_year=params['py'], limit=params['hc'], seq_number=params['rs'])
    resp = requests.get(QUERY_URL, params=params, timeout=5)
    try:
        resp.raise_for_status()
    except Exception:
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

@task
def scrape_year(year):
    base_params = {'py': year, 'sortfield' : 'ti', 'sortorder' : 'asc'}
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
    chunk_base_params = dict(base_params.copy().items() + [('hc', chunk_size)])
    sq_gen = sequence_generator(total_articles, chunk_size)
    args_of_requests = [dict(chunk_base_params.items() + [('rs', each)]) for each in sq_gen]
    for each in args_of_requests:
        scrape_chunk.apply_async([each])

@task
def scrape_all():
    for each in range(1880, 2016):
        scrape_year.apply_async([each])
