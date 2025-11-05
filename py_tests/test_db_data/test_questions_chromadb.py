import argparse
import csv
import logging
import logging.config
import math
import os
import time
from datetime import timedelta

import chromadb

from py_src.utils import configuration
from py_src.ext_api import ollama_api
from py_src.utils import utils

logger = logging.getLogger()

# check_data.csv format:
# document name;pages;question

def proc_data_loading_for_one_file(root, collection):
    chunks_json_file_name = str(os.path.join(root, configuration.chunks_json_file_name))
    chunks_json = utils.load_json(chunks_json_file_name)
    chunks_list = chunks_json['chunks']
    if not configuration.silent_mode:
        print(f"\rchromadb loading process (vector+payload->chromadb) for file '{chunks_json_file_name}'")
    common_src = chunks_json['src']
    common_index = '|'.join(chunks_json['index'])
    for cnt, chunk in enumerate(chunks_list):
        utils.show_spinner(f"{math.ceil(cnt / len(chunks_list) * 1000) / 10}%. ")
        if 'id' in chunk:
            new_documents = ["This is the third document."]
            collection.add(
                ids=[chunk['id']],
                documents=[chunk['text']],
                metadatas=[{'src': common_src, 'topic': common_index}],
                embeddings=chunk['vector']
            )

def load_chunks(collection):
    output_path = configuration.config["path"]["output"]
    for root, dirs, files in os.walk(output_path):
        files_json = [file for file in files if file == configuration.chunks_json_file_name]
        for file in files_json:
            proc_data_loading_for_one_file(root, collection)


if __name__ == "__main__":
    logging.config.fileConfig('log_config.ini')
    parser = argparse.ArgumentParser(description="Process arguments")
    parser.add_argument("--config", help="config file", default="config.yml")
    args = parser.parse_args()
    configuration.load_config(args.config)

    chromadb_collection = chromadb.Client().get_or_create_collection(name='my_test')
    load_chunks(chromadb_collection)

    t0 = time.time()
    with open('check_data.csv', encoding='utf-8') as csvfile:
        reader = csv.reader(csvfile, delimiter=';')
        data = [row for row in reader]
    for row in data:
        doc_name = row[0]
        question = row[2]
        vector, prompt_eval_count = ollama_api.calculate_embedding(question)
        print(f"\rquestion: '{question}' mast be in: '{doc_name}'")
        result = chromadb_collection.query(query_embeddings=[vector],
                                           n_results=configuration.config['qdrant']['top_results'], )
        # print(result)
        data = []
        for index, ids in enumerate(result['ids'][0]):
            data.append({
                'id': ids,
                'distances': result['distances'][0][index],
                'src': result['metadatas'][0][index]['src'],
                'text': result['documents'][0][index],
            })
        sorted_data = sorted(data, key=lambda x: x['distances'])
        for item in sorted_data:
            print(f"   {item}")
    msg = f"Full work time: {str(timedelta(seconds=(time.time() - t0)))}. top_results={configuration.config['qdrant']['top_results']}"
    print(msg)
