import argparse
import logging
import logging.config
import math
import sys
import time
from datetime import timedelta

import chromadb
import numpy as np
from sympy.physics.control.control_plots import plt

sys.path.append('../../')

from py_src.utils import configuration
from py_src.ext_api.ollama_api import calculate_embedding
from py_src.utils import utils

from test_local_data_en import texts_en
from test_local_data_en import questions_en
from test_local_data_ru import texts_ru
from test_local_data_ru import questions_ru

logger = logging.getLogger()

def load_chunks(collection, texts, model):
    if not configuration.silent_mode:
        print(f'\r{model}. chromadb loading process (vector+payload->chromadb) for test data')
    for i, document in enumerate(texts):
        utils.show_spinner(f'{math.ceil(i / len(texts) * 1000) / 10}%. ')
        document_vector, document_prompt_eval_count = calculate_embedding(document, model)
        collection.add(
            ids=[str(i)],
            documents=[document],
            metadatas=[{'src': 'test', 'topic': 'test'}],
            embeddings=document_vector
        )


def do_test(chromadb_collection, texts, questions, model, model_prefix, questions_lang):
    load_chunks(chromadb_collection, texts, model)
    t0 = time.time()
    top_results = 5
    statistics_data = []
    for index, question in enumerate(questions):
        prompt_vector, prompt_eval_count = calculate_embedding(question, model)
        # print(f"\r[{questions_lang}] right text index={index} question: '{question}'.")
        logging.info(f"[{questions_lang}] right text index={index} question: '{question}'.")
        result = chromadb_collection.query(query_embeddings=[prompt_vector], n_results=top_results)
        # print(result)
        data = []
        for n, ids in enumerate(result['ids'][0]):
            data.append({
                'id': ids,
                'distances': result['distances'][0][n],
                'text': result['documents'][0][n],
            })
        sorted_data = sorted(data, key=lambda x: x['distances'])
        statistics_row = []
        has_ok_value = False
        for item in sorted_data:
            is_eq = item['id'] == str(index)
            statistics_row.append([item['distances'], is_eq])
            if is_eq:
                has_ok_value = True
            # print(f'   {item}')
            logging.info(item)
        if not has_ok_value:
            logger.warning(f"!!! No correct answer found for question: '{question}' ")
        statistics_data.append(statistics_row)
    dt = str(timedelta(seconds=(time.time() - t0)))
    msg = f'\rFull work time: {dt}. top_results={top_results}'
    print(msg)
    # -------------------
    x_values = []
    y_values = []
    colors = []
    alphas = []
    for i, row in enumerate(statistics_data):
        has_ok_value = False
        for val, is_true in row:
            if is_true:
                has_ok_value = True
        if has_ok_value:
            for val, is_true in row:
                x_values.append(i)
                y_values.append(val)
                colors.append('green' if is_true else 'gray')
                alphas.append(1 if is_true else 0.5)
        else:
            for val, is_true in row:
                x_values.append(i)
                y_values.append(val)
                colors.append('red')
                alphas.append(1)

    # -------------------
    plt.figure(figsize=(10, 6))
    plt.scatter(x_values, y_values, color=colors, alpha=alphas)
    plt.xticks(np.arange(0, len(statistics_data) + 1, step=5))
    plt.title(f"model: '{model}'. dt:{dt}")
    plt.xlabel(f'[{questions_lang}] question number')
    plt.ylabel('distances')
    plt.grid(True)
    plt.savefig('./plt/'+model_prefix + '_' + questions_lang + '.png', dpi=300)


if __name__ == '__main__':
    logging.config.fileConfig('log_config.ini')
    parser = argparse.ArgumentParser(description='Process arguments')
    parser.add_argument('--config', help='config file', default='../config.yml')
    args = parser.parse_args()
    configuration.load_config(args.config)

    models = [
        'qwen3-embedding:0.6b',
        'qwen3-embedding:latest',
        'bge-large:latest',
        'mxbai-embed-large:latest',
        'nomic-embed-text:latest',
        'evilfreelancer/enbeddrus:latest',
        'embeddinggemma:latest',
    ]

    for model in models:
        prefix = model.replace(':', '_').replace('/', '_')
        do_test(chromadb.Client().get_or_create_collection(name=prefix + '_en'), texts_en, questions_en,
                model, prefix, 'en')
        do_test(chromadb.Client().get_or_create_collection(name=prefix + '_ru'), texts_ru, questions_ru,
                model, prefix, 'ru')
    print("all plots images saved")
