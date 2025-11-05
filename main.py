import argparse
import logging.config
import sys
import time
from datetime import timedelta

logger = logging.getLogger()

sys.path.append('./data_convert')

from py_src.utils import configuration
from py_src.data_converters import data2chunks
from py_src.data_converters import chunks2embedding
from py_src.http import http_server
from py_src.data_converters import pdf2data
from py_src.data_converters import embedding2qdrant
from py_src.ext_api import ollama_api

if __name__ == "__main__":

    logging.config.fileConfig('log_config.ini')
    parser = argparse.ArgumentParser(description="Process arguments")
    parser.add_argument("--config", help="config file", default="config.yml")
    parser.add_argument("--exec", help="ALL,PDF,CHUNK,EMBEDDING,LOAD_QDRANT", default="ALL")
    parser.add_argument("--http", help="run http", action="store_true")
    args = parser.parse_args()
    configuration.load_config(args.config)

    if args.http:
        http_server.run()
    else:
        print(f"start with model {ollama_api.get_ollama_embedding_model()}")
        start_time = time.time()
        if args.exec == "ALL" or "PDF" in args.exec:
            pdf2data.process_pdf()
        if args.exec == "ALL" or "CHUNK" in args.exec:
            data2chunks.proc_data_chunk()
        if args.exec == "ALL" or "EMBEDDING" in args.exec:
            chunks2embedding.proc_embedding()
        if args.exec == "ALL" or "LOAD_QDRANT" in args.exec:
            embedding2qdrant.proc_data_loading()

        msg = f"Full work time: {str(timedelta(seconds=(time.time() - start_time)))}"
        print('\r' + msg)
        logger.info(msg)
