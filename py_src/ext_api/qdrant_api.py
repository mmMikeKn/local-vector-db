import json
import logging
import sys

import requests

from py_src.utils import configuration
from py_src.utils import utils

logger = logging.getLogger()

# https://qdrant.github.io/qdrant/redoc/index.html

def get_qdrant_base_url():
    return configuration.config['qdrant']['url']


def get_qdrant_collection_name():
    return configuration.config['qdrant']['collection_name']


def get_point(point_id):
    collection_name = get_qdrant_collection_name()
    url = get_qdrant_base_url() + '/collections/' + collection_name + '/points/' + point_id
    logger.debug(f"Going to get point. GET '{url}'")
    response = requests.get(url)
    if response.status_code == 200:
        data = response.json()
        logger.debug(f"HTTP response '{json.dumps(data, indent=2)}'")
        return data['result']
    elif response.status_code == 404:
        logger.debug(f"Point '{point_id}' not found")
        return None
    else:
        msg = f"ERROR. Request 'get point' GET '{url}' failed with status code: {response.status_code} resp body: '{response.text}'"
        print(msg)
        logger.error(msg)
        sys.exit(1)


def add_point_if_not_exist(point_id, vector, payload):
    collection_name = get_qdrant_collection_name()
    point = get_point(point_id)  # may be updates without check existence
    if point is None:
        utils.do_http_put(get_qdrant_base_url() + '/collections/' + collection_name + '/points?wait=true', {
            'points': [
                {
                    'id': int(point_id),
                    'vector': vector,
                    'payload': payload,
                }
            ]

        }, 'qdrant add point')


def is_collection_exists():
    data = utils.do_http_get(get_qdrant_base_url() + '/collections')
    # vs {protocol}://{hostname}:{port}/collections/{collection_name}/exists
    collection_name = get_qdrant_collection_name()
    for collection in data['result']['collections']:
        if collection['name'] == collection_name:
            data = utils.do_http_get(get_qdrant_base_url() + '/collections/' + collection_name)
            status = data['result']['status']
            if status != 'green':
                logger.warning(f"Collection '{collection_name}' is not green status: {status}")
                print(f"WARN. Collection '{collection_name}' is not green status: {status}")
            return True
    return False


def create_collection():
    collection_name = get_qdrant_collection_name()
    qdrant_config = configuration.config['qdrant']
    json_rq = {
        'vectors': {
            'size': qdrant_config['vector_sz'],
            'distance': qdrant_config['distance'],
        },
    }
    utils.do_http_put(get_qdrant_base_url() + '/collections/' + collection_name, json_rq, 'qdrant create collection')


def dump_collection_info():
    collection_name = get_qdrant_collection_name()
    data = utils.do_http_get(get_qdrant_base_url() + '/collections/' + collection_name, 'qdrant get collection info fro dump')['result']
    collection_config_param = data['config']['params']
    msg = (f"Collection '{collection_name}' status='{data['status']}' points_count={data['points_count']} "
           f"vectors.size={collection_config_param['vectors']['size']} distance={collection_config_param['vectors']['distance']}")
    print('\r'+msg)
    logger.info(msg)


def create_inexes_if_not_exist(field_name):
    collection_name = get_qdrant_collection_name()
    data = utils.do_http_get(get_qdrant_base_url() + '/collections/' + collection_name, 'qdrant get collection info')
    payload_schema = data['result']['payload_schema']
    if field_name not in payload_schema:
        # {protocol}: // {hostname}: {port} / collections / {collection_name} / index
        utils.do_http_put(get_qdrant_base_url() + '/collections/' + collection_name + '/index?wait=true', {
            'field_name': field_name,
            'field_schema': 'keyword',
        }, 'qdrant create index')


def do_search(vector, topic=None, top_results=None):
    collection_name = get_qdrant_collection_name()
    json_rq = {
        'vector': vector,
        'top': top_results if top_results is not None else configuration.config['qdrant']['top_results'],
        'with_payload': True,
    }
    if topic:
        json_rq['filter'] = {
            'should': {
                'key': 'topic',
                'match': {
                    'value': topic
                }
            }
        }
    data = utils.do_http_post(get_qdrant_base_url() + '/collections/' + collection_name + '/points/search', json_rq, 'qdrant search')
    return data['result']
