# -*- coding: utf-8 -*-

import logging

_logger = logging.getLogger(__name__)


def search_paginated(env, model_name, company, domain=None, limit_max=2000, offset=0, limit=100):
    """
    Method that created pagination

    :param model_name: specifies the model to which the search will be performed
    :param company: specifies the company
    :param domain: specify search conditions
    :param limit_max: specifies the maximum limit of records to be returned
    :param offset: optional value that specify initial value from where to start paginating
    :param limit: optional value that specify maximum number of records to return on a page
    :return: a dictionary with the paginated search results
    """
    ModelToSearch = env[model_name].with_company(company).sudo()
    # get records with pagination
    records = ModelToSearch.search(domain or [], offset=offset, limit=limit, order='id asc')

    # get totals of records
    total_records = len(ModelToSearch.search(domain or [], limit=limit_max, order='id asc'))
    return {
        'total_records': total_records,
        'offset': offset,
        'limit': limit,
        'limit_max': limit_max,
        'records': records
    }