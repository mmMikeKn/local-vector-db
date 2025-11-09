import argparse
import json
import logging.config
import math
import os
import shutil
from datetime import datetime
from pathlib import Path

from atlassian import Confluence

from py_src.utils import configuration, utils

logger = logging.getLogger()


def scan_confluence_space(confluence_base_url, confluence_ptr, space_name):
    limit = configuration.get_config_value(['confluence', 'scan_pages_chunk_size'], 10)
    date_threshold = configuration.get_config_value(['confluence', 'date_threshold'], None)
    if date_threshold is not None:
        date_threshold = datetime.fromisoformat(str(date_threshold))
        if date_threshold.tzinfo is None:
            date_threshold = date_threshold.replace(tzinfo=datetime.now().astimezone().tzinfo)
    include_pages = configuration.get_config_value(['confluence', 'include_pages'], None)
    exclude_pages = configuration.get_config_value(['confluence', 'exclude_pages'], None)

    logger.debug(
        f"date_threshold: {date_threshold} limit: {limit} include_pages: {include_pages} exclude_pages: {exclude_pages}")
    if not configuration.silent_mode:
        print(f"\rScan Confluence pages info for '{confluence_base_url}' space '{space_name}'")
    all_pages = []
    start = 0
    while True:
        utils.show_spinner(f" get info for {len(all_pages)} pages    ")
        pages_chunk = confluence_ptr.get_all_pages_from_space(
            space=space_name,
            start=start,
            limit=limit,
            status='current',  # ('current', 'draft', 'trashed')
            expand='history.lastUpdated',
            content_type='page'
        )
        all_pages.extend(pages_chunk)
        if len(pages_chunk) < limit:
            break
        start += limit
    scan_results = []
    for page in all_pages:
        page_history = page['history']
        page_id = page['id']
        page_date = datetime.fromisoformat(
            page_history['lastUpdated']['when'] if 'lastUpdated' in page_history and 'when' in page_history[
                'lastUpdated'] else page_history['createdDate'])
        if (date_threshold is not None and page_date > date_threshold
                and (not include_pages or page_id in include_pages)
                and (not exclude_pages or page_id not in exclude_pages)):
            short_page_info = {
                'id': page_id,
                'title': page['title'],
                'link': confluence_base_url + '/' + page['_links']['webui'],
                'last_date': str(page_date),
            }
            # logger.debug(f" src {json.dumps(page, indent=2,  ensure_ascii=False)}  short: \t{json.dumps(short_page_info, indent=2,  ensure_ascii=False)}")
            scan_results.append(short_page_info)
    if not configuration.silent_mode:
        print(f"\rFind Confluence pages {len(scan_results)} (all {len(all_pages)} pages)")
    return scan_results


def confluence_page2pdf(confluence_ptr, space_name, scan_results):
    root_path = str(os.path.join(configuration.config['path']['output'], 'Confluence', space_name))
    if not os.path.exists(root_path):
        os.makedirs(root_path, exist_ok=True)
    if not configuration.silent_mode:
        print(f"\rSave Confluence pages as pdf into '{root_path}'")
    updated_cnt = 0
    saved_cnt = 0
    error_cnt = 0
    for i, page in enumerate(scan_results):
        page_id = page['id']
        page_last_date = datetime.fromisoformat(str(page['last_date']))
        pdf_file_name = str(os.path.join(root_path, f"{page_id}.pdf"))
        add_info_json_file_name = str(os.path.join(root_path, f"{page_id}.jsn"))
        if os.path.exists(add_info_json_file_name):
            add_info_json = utils.load_json(add_info_json_file_name)
            saved_page_last_date = datetime.fromisoformat(str(add_info_json['last_date']))
            if page_last_date > saved_page_last_date:
                updated_cnt = updated_cnt  + 1
                Path(pdf_file_name).unlink(missing_ok=True)
                Path(add_info_json_file_name).unlink(missing_ok=True)
                tmp_path = str(os.path.join(root_path, f".t-{page_id}"))
                if os.path.isdir(tmp_path):
                    shutil.rmtree(tmp_path)
                data_path = os.path.join(root_path, f".d-{page_id}")
                if os.path.isdir(data_path):
                    shutil.rmtree(data_path)
        if not os.path.exists(pdf_file_name):
            try:
                pdf_content = confluence_ptr.get_page_as_pdf(page_id)
                with open(pdf_file_name, 'wb') as f:
                    f.write(pdf_content)
                utils.save_json(add_info_json_file_name, {
                    'title': page['title'],
                    'link': page['link'],
                    'last_date': page['last_date'],
                })
                saved_cnt = saved_cnt + 1
            except Exception as e:
                error_cnt = error_cnt + 1
                logger.warning(f"Failed to get_page_as_pdf [{json.dumps(page, indent=2, ensure_ascii=False)}]: {e}")
                print(f"Failed to get page_as_pdf id=[{page_id}] title: '{page['title']}' utl: '{page['link']}'  {e.args[0] if e.args else 'Unknown error'}")

        utils.show_spinner(f"{math.ceil(i / len(scan_results) * 1000) / 10}%")
    if not configuration.silent_mode:
        print(f"\rFinish pdf save. new saved {saved_cnt-updated_cnt}. updated {updated_cnt} errors: {error_cnt}")


if __name__ == "__main__":
    logging.config.fileConfig('log_config.ini')
    parser = argparse.ArgumentParser(description="Process arguments")
    parser.add_argument("--config", help="config file", default="config.yml")
    parser.add_argument("--url", required=True, help="confluence url like 'https://confluence.blabla.ru/'")
    parser.add_argument("--username", required=True, help="user name")
    parser.add_argument("--password", required=True, help="user password")
    parser.add_argument("--space", required=True, help="confluence space name")
    args = parser.parse_args()
    configuration.load_config(args.config)

    confluence = Confluence(
        url=args.url,
        username=args.username,
        password=args.password,
        # api_token=..
    )
    pages = scan_confluence_space(args.url, confluence, args.space)
    logger.debug(f"pages: {json.dumps(pages, indent=2, ensure_ascii=False)}")
    confluence_page2pdf(confluence, args.space, pages)

    print("\nDo not forget to run 'python main.py' for processing pdf files from confluence.")