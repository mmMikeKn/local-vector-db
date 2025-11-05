import argparse
import csv
import logging.config
import time
from datetime import timedelta

from py_src.utils import configuration
from py_src.ext_api import ollama_api
from py_src.ext_api import qdrant_api

logger = logging.getLogger()

# check_data.csv format:
# document name;pages;question

if __name__ == "__main__":
    logging.config.fileConfig('./log_config.ini')

    parser = argparse.ArgumentParser(description="Process arguments")
    parser.add_argument("--config", help="config file", default="../../config.yml")
    args = parser.parse_args()
    configuration.load_config(args.config)

    t0 = time.time()
    qdrant_api.dump_collection_info()
    with open('check_data.csv', encoding='utf-8') as csvfile:
        reader = csv.reader(csvfile, delimiter=';')
        data = [row for row in reader]
    for row in data:
        doc_name = row[0]
        question = row[2]
        vector, prompt_eval_count = ollama_api.calculate_embedding(question)
        print(f"question: '{question}' mast be in: '{doc_name}'")
        data = qdrant_api.do_search(vector)
        sorted_data = sorted(data, key=lambda x: x['score'])
        for item in sorted_data:
            # src = item['payload']['src']
            print(f"   {item}")
    msg = f"Full work time: {str(timedelta(seconds=(time.time() - t0)))}. top_results={configuration.config['qdrant']['top_results']}"
    print(msg)

