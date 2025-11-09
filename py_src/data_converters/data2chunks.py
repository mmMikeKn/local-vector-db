import logging
import math
import os

from langchain_text_splitters import RecursiveCharacterTextSplitter

from py_src.utils import configuration
from py_src.utils import utils

logger = logging.getLogger()

def proc_chunk_for_one_file(root):
    chunks_json_file_name = str(os.path.join(root, configuration.chunks_json_file_name))
    if os.path.isfile(chunks_json_file_name):
        return  # already exist

    doc_data_json = utils.load_json(os.path.join(root, configuration.doc_data_json_file_name))

    if not configuration.silent_mode:
        print(f"\rchunk building process (data->chunks) for file '{chunks_json_file_name}'")
    embedding_config = configuration.config['ollama']['embedding']
    context_size = embedding_config['context_size']
    token_naive_k = embedding_config['token_naive_k']
    chunk_overlap_percent = embedding_config['chunk_overlap_percent']

    chunk_size = round(context_size * token_naive_k)
    chunk_overlap = round(chunk_size * chunk_overlap_percent / 100.0)
    logger.debug(f"chunk_size={chunk_size}, chunk_overlap={chunk_overlap}")
    chunks_json = {
        'src': doc_data_json['src'],
        'index': doc_data_json['index'],
        'context_size': context_size,
        'token_naive_k': token_naive_k,
        'chunk_overlap_percent': chunk_overlap_percent,
        'link':  doc_data_json.get('link'), # confluence2pdf.py
        'title': doc_data_json.get('title'), # confluence2pdf.py
        'last_date': doc_data_json.get('last_date'), # confluence2pdf.py
        'chunks': []
    }
    chunks_json_list = chunks_json['chunks']
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        separators=["\n", " "]
    )

    json_data_pages = doc_data_json['pages']
    i = 0
    text = ''
    chunks = []
    while i < len(json_data_pages):
        pages = []
        if len(chunks) > 0 and len(text) > 0:
            index = text.find(chunks[-1])
            # logger.debug(f"index={index} for chunk={chunks[-1]} text={text}")
            if index > 0:
                text = text[index:]
                pages.append(i - 1)
            else:
                text = ''
        while len(text) < chunk_size and i < len(json_data_pages):
            pages.append(i)
            text = text + json_data_pages[i]['text']
            i = i + 1
        chunks = text_splitter.split_text(text)
        # logger.debug(f"\n\ttext='{text}'\n\tchunks={chunks}")
        for chunk in chunks:
            chunks_json_list.append({
                'pages': pages,
                'text': chunk
            })
        utils.show_spinner(f"{math.ceil(i / len(json_data_pages) * 1000) / 10}%")
    utils.save_json(chunks_json_file_name, chunks_json)


def proc_data_chunk():
    path_config = configuration.config["path"]
    output_path = path_config["output"]
    for root, dirs, files in os.walk(output_path):
        files_json = [file for file in files if file == configuration.doc_data_json_file_name]
        for file in files_json:
            proc_chunk_for_one_file(root)
