"""
BioMed Central harvester of public projects for the SHARE Notification Service
Note: At the moment, this harvester only harvests basic data on each article, and does
not make a seperate request for additional metadata for each record.

Example API query: http://www.biomedcentral.com/webapi/1.0/latest_articles.json
"""

from __future__ import unicode_literals

import json
import logging
from dateutil.parser import parse

from nameparser import HumanName

from scrapi import requests
from scrapi.base import JSONHarvester
from scrapi.base.schemas import CONSTANT
from scrapi.linter.document import RawDocument

logger = logging.getLogger(__name__)


def process_contributors(authors):

    authors = authors.strip().replace('<span class="author-names">', '').replace('</span>', '')
    authors = authors.split(',')

    if ' and ' in authors[-1] or ' <em>et al.</em>' in authors[-1]:
        split_name = authors.pop(-1).replace(' <em>et al.</em>', '').split(' and ')
        authors.extend(split_name)

    contributor_list = []
    for person in authors:
        name = HumanName(person)
        contributor = {
            'prefix': name.title,
            'given': name.first,
            'middle': name.middle,
            'family': name.last,
            'suffix': name.suffix,
            'email': '',
            'ORCID': '',
        }
        contributor_list.append(contributor)

    return contributor_list


class BiomedHarvester(JSONHarvester):
    short_name = 'biomed'
    long_name = 'BioMed Central'
    url = 'http://www.biomedcentral.com/'
    count = 0

    URL = 'http://www.biomedcentral.com/search/results?terms=*&format=json&drpAddedInLast={}&itemsPerPage=250'

    schema = {
        'title': ('bibliographyTitle', 'blurbTitle', lambda x, y: x or y),
        'description': 'blurbText',
        'tags': CONSTANT([]),
        'dateUpdated': ('published Date', lambda x: parse(x).isoformat().decode('utf-8')),
        'id': {
            'serviceID': ('arxId', 'doi', lambda x, y: x.decode('utf-8') or y.decode('utf-8')),
            'url': 'articleFullUrl',
            'doi': 'doi'
        },
        'contributors': ('authorNames', process_contributors),
        'properties': {
            'blurbTitle': 'blurbTitle',
            'imageUrl': 'imageUrl',
            'articleUrl': 'articleUrl',
            'type': 'type',
            'isOpenAccess': 'isOpenAccess',
            'isFree': 'isFree',
            'isHighlyAccessed': 'isHighlyAccessed',
            'status': 'status',
            'abstractPath': 'abstractPath',
            'journal Id': 'journal Id',
            'published Date': 'published Date'
        }
    }

    def harvest(self, days_back=1):
        search_url = self.URL.format(days_back)
        records = self.get_records(search_url)

        record_list = []
        for record in records:
            doc_id = record['arxId']

            record_list.append(
                RawDocument(
                    {
                        'doc': json.dumps(record),
                        'source': self.short_name,
                        'docID': doc_id.decode('utf-8'),
                        'filetype': 'json'
                    }
                )
            )

        return record_list

    def get_records(self, search_url):
        records = requests.get(search_url)
        page = 1

        all_records = []
        current_records = len(records.json()['entries'])
        while current_records > 0:
            record_list = records.json()['entries']

            for record in record_list:
                all_records.append(record)

            page += 1
            records = requests.get(search_url + '&page={}'.format(str(page)), throttle=10)
            current_records = len(records.json()['entries'])

        return all_records