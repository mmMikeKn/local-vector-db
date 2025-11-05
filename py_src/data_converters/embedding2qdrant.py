import logging
import math
import os

from py_src.utils import configuration
from py_src.ext_api import qdrant_api
from py_src.utils import utils

logger = logging.getLogger()

def proc_data_loading_for_one_file(root):
    chunks_json_file_name = str(os.path.join(root, configuration.chunks_json_file_name))
    chunks_json = utils.load_json(chunks_json_file_name)
    chunks_list = chunks_json['chunks']
    if not configuration.silent_mode:
        print(f"\rqdrant loading process (vector+payload->qdrant) for file '{chunks_json_file_name}'")
    common_src = chunks_json['src']
    common_index = '|'.join(chunks_json['index'])
    for cnt, chunk in enumerate(chunks_list):
        utils.show_spinner(f"{math.ceil(cnt / len(chunks_list) * 1000) / 10}%. ")
        if 'id' in chunk:
            qdrant_api.add_point_if_not_exist(chunk['id'], chunk['vector'], {
                'topic': common_index,
                'root': root,
                'src': common_src,
                'text': chunk['text'],
                'pages': chunk['pages'],
            })

def proc_data_loading():
    if not qdrant_api.is_collection_exists():
        qdrant_api.create_collection()
    qdrant_api.create_inexes_if_not_exist('topic')

    output_path = configuration.config["path"]["output"]
    for root, dirs, files in os.walk(output_path):
        files_json = [file for file in files if file == configuration.chunks_json_file_name]
        for file in files_json:
            proc_data_loading_for_one_file(root)
    qdrant_api.dump_collection_info()
