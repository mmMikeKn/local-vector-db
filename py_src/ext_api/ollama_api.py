import json
import logging
import sys

import aiohttp

from py_src.utils import configuration
from py_src.utils import utils

logger = logging.getLogger()

# https://docs.ollama.com/api

def get_ollama_base_url():
    return configuration.config['ollama']['url']


def get_ollama_embedding_model():
    return configuration.config['ollama']['embedding']['model']


def check_embedding_model_exists(ollama_embedding_model=None):
    if ollama_embedding_model is None:
        ollama_embedding_model = get_ollama_embedding_model()
    data = utils.do_http_get(get_ollama_base_url() + '/api/tags')
    for model in data['models']:
        if model['name'] == ollama_embedding_model:
            return
    msg = f"Model not found. use 'ollama pull {ollama_embedding_model}'"
    print(msg)
    logger.error(msg + '\n' + json.dumps(data, indent=2))
    sys.exit(1)


def calculate_embedding(prompt, ollama_embedding_model=None):
    if ollama_embedding_model is None:
        ollama_embedding_model = get_ollama_embedding_model()
    json_rq = {
        'model': ollama_embedding_model,
        'input': prompt
    }
    embedding_config = configuration.config['ollama']['embedding']
    if 'truncate' in embedding_config:
        json_rq['truncate'] = embedding_config['truncate']
    if 'dimensions' in embedding_config:
        json_rq['dimensions'] = embedding_config['dimensions']
    if 'options' in embedding_config:
        json_rq['options'] = embedding_config['options']

    data = utils.do_http_post(get_ollama_base_url() + '/api/embed', json_rq, 'calc embedding')
    return data['embeddings'][0], data['prompt_eval_count']


# =====================

async def generate_lmm(callback_func, question_text, chunk_text):
    logger.info(
        f"Generating LMM task.  question_text: '{question_text}', chunk_text: '{chunk_text}'")
    http_config = configuration.config['http']
    if any('а' <= char.lower() <= 'я' for char in chunk_text.lower()):
        sys_prompt = http_config['prompt_ru']
    else:
        sys_prompt = http_config['prompt_en']
    sys_prompt = sys_prompt.replace('${question}', question_text)
    json_rq = {
        'model': http_config['llm'],
        'stream': True,
        'system': sys_prompt,
        'prompt': chunk_text,
        'options': http_config['options'] if 'options' in http_config else None,
    }
    url = get_ollama_base_url() + '/api/generate'
    logger.debug(f"Going call POST '{url}' with json data '{json.dumps(json_rq, ensure_ascii=False)}'")
    headers = {
        'Content-Type': 'application/json; charset=utf-8',
        'Accept': 'application/json; charset=utf-8'
    }

    async with aiohttp.ClientSession(headers=headers) as session:
        async with session.post(url, json=json_rq) as response:
            if response.status != 200:
                msg = (
                    f"ERROR. request POST '{url}' with json data '{json.dumps(json_rq, ensure_ascii=False)}' "
                    f"failed with status code: {response.status} resp body: '{response.text}'")
                logger.error(msg)
                callback_func('ERROR. Call ollama')
                return
            # logger.debug('Response HTTP 200 from POST. going to get answer chunks in loop')
            while True:
                chunk = await response.content.readany()
                # logger.debug(f"chunk:{chunk}")
                if not chunk:
                    logger.warning(f"Not next chunk:{chunk}")
                    return
                try:
                    json_data = json.loads(chunk.decode('utf-8'))
                    callback_func(json_data['response'])
                    if json_data.get('done'):
                        return
                except Exception as e:
                    logger.error(e)
