import asyncio
import json
import logging
import os
import re
from http.server import BaseHTTPRequestHandler, HTTPServer
from json import JSONDecodeError
from urllib.parse import unquote

from py_src.ext_api import ollama_api
from py_src.ext_api import qdrant_api
from py_src.utils import configuration, utils

logger = logging.getLogger()


class RequestHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        logger.debug(f"received GET '{self.path}'")
        if self.path == '/':
            self.handle_get_http_file('text/html', 'index.html')
        elif self.path.endswith('favicon.ico'):
            self.handle_get_http_file('image/x-icon', 'favicon.ico')
        elif self.path.startswith('/' + configuration.config['path']['output']):
            self.handle_get_data_file(self.path)
        else:
            self.send_error(404, f'Path {self.path} was not found.')

    def do_POST(self):
        content_length = int(self.headers['Content-Length'])
        post_data = self.rfile.read(content_length).decode('utf-8')
        logger.debug(f"received POST '{self.path}' body=[{post_data}]")
        try:
            request_json = json.loads(post_data)
        except JSONDecodeError as e:
            logger.error(f"JSON decode error {e} for POST '{self.path}' body=[{post_data}]")
            self.send_error(400, f'Bad request: {e}')
            return

        if self.path == '/api/question':
            if 'substr' in request_json and request_json['substr']:
                chunks = handle_question_substr_search(request_json)
            else:
                chunks = handle_question_context_search(request_json)
            response = {
                'chunks': chunks,
                'llm': configuration.config['http']['llm'],
            }
            self.send_response(200)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.end_headers()
            self.wfile.write(json.dumps(response, indent=2, ensure_ascii=False).encode('utf-8'))
        elif self.path == '/api/llm':
            self.send_response(200)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.send_header('Transfer-Encoding', 'chunked')
            self.end_headers()
            asyncio.run(ollama_api.generate_lmm(self.handle_llm_response, request_json['question'], request_json['chunk']))
            self.wfile.write(b"0\r\n\r\n")
            self.wfile.flush()
            return
        else:
            self.send_error(404, f'Unknown path {self.path}.')
            return

    def handle_get_http_file(self, content_type, file_name):
        try:
            with open('./py_src/http/' + file_name, "rb") as file:
                content = file.read()
            self.send_response(200)
            self.send_header('Content-type', content_type)
            self.end_headers()
            self.wfile.write(content)
        except FileNotFoundError:
            self.send_error(404, f'File {file_name} not found.')

    def handle_get_data_file(self, file_name):
        full_file_name = '.' + unquote(file_name)  # TODO correct name for any case. lazy....
        try:
            logger.info(f"Reading file {full_file_name}")
            with open(full_file_name, "rb") as file:
                content = file.read()
            self.send_response(200)
            self.send_header('Content-type', 'image/png' if file_name.lower().endswith('.png') else 'application/pdf')
            self.end_headers()
            self.wfile.write(content)
        except FileNotFoundError:
            self.send_error(404, f'File {full_file_name} not found.')

    def handle_llm_response(self, answer_text):
        chunk_bytes = answer_text.encode('utf-8')
        chunk_length = hex(len(chunk_bytes)).lstrip('0x')  # Length in hex
        self.wfile.write(f"{chunk_length}\r\n".encode('utf-8'))
        self.wfile.write(chunk_bytes)
        self.wfile.write(b"\r\n")
        self.wfile.flush()

def handle_question_context_search(request_json):
    vector, prompt_eval_count = ollama_api.calculate_embedding(request_json['question'])
    data = qdrant_api.do_search(vector, request_json.get('topic'), request_json.get('top_results'))
    sorted_data = sorted(data, key=lambda x: x['score'])
    chunks = []
    for item in sorted_data:
        payload = item['payload']
        root_path = payload['root']
        src_doc = payload['src']
        pages_num = payload['pages']
        pages_png = []
        for page in pages_num:
            pages_png.append(root_path + '/p' + str(page) + '.png')
        chunks.append({
            'id': item['id'],
            'text': payload['text'],
            'document': src_doc,
            'images': pages_png,
        })
    return chunks


def handle_question_substr_search(request_json):
    substr_tokens = re.split(r'[,\\s]+', request_json['question'])
    substr_tokens = [item.strip().lower() for item in substr_tokens if item.strip()]
    logger.info(f"handle_question_substr_search. substr_tokens: {substr_tokens}")
    top_results = configuration.config['qdrant']['top_results']
    output_path = configuration.config["path"]["output"]
    chunks = []
    for root_path, dirs, files in os.walk(output_path):
        files_json = [file for file in files if file == configuration.chunks_json_file_name]
        for chunks_json_file_name in files_json:
            chunks_json = utils.load_json(str(os.path.join(root_path, chunks_json_file_name)))
            src_doc = chunks_json['src']
            for chunk in chunks_json['chunks']:
                text = chunk['text'].lower()
                if all(token in text for token in substr_tokens):
                    pages_num = chunk['pages']
                    pages_png = []
                    for page in pages_num:
                        pages_png.append(root_path + '/p' + str(page) + '.png')
                    chunks.append({
                        'id': chunk['id'],
                        'text': text,
                        'document': src_doc,
                        'images': pages_png,
                    })
                    if len(chunks) == top_results:
                        return chunks
    return chunks

def run():
    port = configuration.config['http']['port']
    host = configuration.config['http']['host']
    # noinspection PyTypeChecker
    httpd = HTTPServer((host, port), RequestHandler)
    print(f'Server running at http://{host}:{port}')
    logger.info(f'Server running at http://{host}:{port}')
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        httpd.server_close()
        logger.info(f'Server stopped by user')
