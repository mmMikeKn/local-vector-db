import logging
import math
import os
import sys
import time

from py_src.utils import configuration
from py_src.ext_api import ollama_api
from py_src.utils import utils

logger = logging.getLogger()

def proc_embedding_for_one_file(root):
    chunks_json_file_name = str(os.path.join(root, configuration.chunks_json_file_name))
    chunks_json = utils.load_json(chunks_json_file_name)

    ollama_embedding_model = ollama_api.get_ollama_embedding_model()
    if 'embedding_model' not in chunks_json:
        chunks_json['embedding_model'] = ollama_embedding_model
    else:
        if chunks_json['embedding_model'] != ollama_embedding_model:
            msg = f"ERROR. File {chunks_json_file_name} does not match current model '{ollama_embedding_model}'. Model '{chunks_json['embedding_model']}' was used."
            print(msg, file=sys.stderr)
            logger.error(msg)
            sys.exit(1)
    chunks_list = chunks_json['chunks']
    nof_filled_count = sum(1 for item in chunks_list if 'vector' not in item)
    if not configuration.silent_mode:
        print(f"\rEmbedding process (chunk->vector) for file '{chunks_json_file_name}'")
    cnt = 0
    sum_dt = 0
    max_dt = 0
    max_prompt_eval_count = 0
    sum_prompt_eval_count = 0
    start_time = time.time()
    vector_sz = 0
    for chunk in chunks_list:
        if 'vector' not in chunk:
            t0 = time.time()
            vector, prompt_eval_count = ollama_api.calculate_embedding(chunk['text'])
            if vector_sz != 0 and vector_sz != len(vector):
                logger.warning(f"diff vector size!!! {vector_sz} != {len(vector)}")
            vector_sz = len(vector)
            dt = (time.time() - t0) * 1000
            chunk['vector'] = vector
            chunk['prompt_eval_count'] = prompt_eval_count
            chunk['id'] = str(round(t0 * 1000))
            cnt = cnt + 1
            nof_filled_count = nof_filled_count - 1
            sum_dt = sum_dt + dt
            sum_prompt_eval_count = sum_prompt_eval_count + prompt_eval_count
            if max_dt < dt:
                max_dt = dt
            if max_prompt_eval_count < prompt_eval_count:
                max_prompt_eval_count = prompt_eval_count
            if cnt % 10 == 0:  # save intermediate results
                utils.save_json(chunks_json_file_name, chunks_json)
            utils.show_spinner(f"{math.ceil((len(chunks_list) - nof_filled_count) / len(chunks_list) * 1000) / 10}%. "
                               f"dtMax={round(max_dt)}ms dtOver={round(sum_dt / cnt)}ms "
                               f"maxEvalCnt={max_prompt_eval_count} overEvalCnt={round(sum_prompt_eval_count / cnt)}")
    utils.save_json(chunks_json_file_name, chunks_json)
    if cnt > 0:
        logger.info(f"Embedding (vector_sz={vector_sz}) statistics: "
                    f"cnt={cnt} {round((time.time() - start_time) * 1000)}ms "
                    f"dtMax:{round(max_dt)}ms dtOver:{round(sum_dt / cnt)}ms "
                    f"for file '{chunks_json_file_name}'")


def proc_embedding():
    ollama_api.check_embedding_model_exists()

    path_config = configuration.config["path"]
    output_path = path_config["output"]
    for root, dirs, files in os.walk(output_path):
        files_json = [file for file in files if file == configuration.chunks_json_file_name]
        for file in files_json:
            proc_embedding_for_one_file(root)
