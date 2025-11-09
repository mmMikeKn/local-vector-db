import json
import logging
import sys

import requests

from py_src.utils import configuration

spinner = ['⣾', '⣷', '⣯', '⣟', '⡿', '⢿', '⣻', '⣽']
spinner_index = 0

logger = logging.getLogger()

headers = {
    "Content-Type": "application/json"
}


def show_spinner(msg):
    if not configuration.silent_mode:
        global spinner_index
        spinner_index = spinner_index + 1 if spinner_index < len(spinner) - 1 else 0
        sys.stdout.write(f'\r{spinner[spinner_index]} {msg}            ')
        sys.stdout.flush()


def save_json(json_file, json_data, json_indent=None):
    with open(json_file, 'w', encoding='utf-8') as f:
        json.dump(json_data, f, ensure_ascii=False, indent=configuration.get_config_value(['process','json_indent'], json_indent))


def load_json(json_file):
    with open(json_file, 'r', encoding='utf-8') as f:
        return json.load(f)


def do_http_post(url, json_rq, type_str=''):
    logger.debug(f"Going call {type_str} POST '{url}' with json data '{json.dumps(json_rq, ensure_ascii=False)}'")
    response = requests.post(url, json=json_rq, headers={
        'Content-Type': 'application/json; charset=utf-8',
        'Accept': 'application/json; charset=utf-8'
    })
    if response.status_code == 200:
        data = response.json()
        logger.debug(f"{type_str} HTTP response '{json.dumps(data, ensure_ascii=False),}'")
        return data
    else:
        msg = (f"ERROR. {type_str} request POST '{url}' with json data '{json.dumps(json_rq, ensure_ascii=False)}' "
               f"failed with status code: {response.status_code} resp body: '{response.text}'")
        print(msg)
        logger.error(msg)
        sys.exit(1)


def do_http_put(url, json_rq, type_str=''):
    logger.debug(f"Going call {type_str} PUT '{url}' with json data '{json.dumps(json_rq, ensure_ascii=False)}'")
    response = requests.put(url, json=json_rq, headers={
        'Content-Type': 'application/json; charset=utf-8',
        'Accept': 'application/json; charset=utf-8'
    })
    if response.status_code == 200:
        data = response.json()
        logger.debug(f"{type_str} HTTP response '{json.dumps(data, ensure_ascii=False)}'")
        return data
    else:
        msg = (f"ERROR. {type_str} Request PUT '{url}' with json data '{json.dumps(json_rq, ensure_ascii=False)}' "
               f"failed with status code: {response.status_code} resp body: '{response.text}'")
        print(msg)
        logger.error(msg)
        sys.exit(1)


def do_http_get(url, type_str=''):
    logger.debug(f"Going to call {type_str} GET '{url}'")
    response = requests.get(url, headers={
        'Accept': 'application/json; charset=utf-8'
    })
    if response.status_code == 200:
        data = response.json()
        logger.debug(f"{type_str} HTTP response '{json.dumps(data, ensure_ascii=False)}'")
        return data
    else:
        msg = f"ERROR. {type_str} request GET '{url}' failed with status code: {response.status_code} resp body: '{response.text}'"
        print(msg)
        logger.error(msg)
        sys.exit(1)
