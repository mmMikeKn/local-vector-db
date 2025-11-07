import yaml
import logging

silent_mode = False
def_config = {
    'process': {
        'json_ident': False,
        'silent': False,
        'pdf_clip': [
            {'text': 'Протокол и основные функциональные',
             'header_height': 50, 'footer_height': 50},
        ]
    },
    'path': {
        'input': 'input',
        'output': 'db-data'
    },
    'qdrant': {
        'url': 'http://192.168.0.101:6333',
        'collection_name': 'my_documents',
        'vector_sz': 768,
        'distance': 'Cosine',
        'top_results': 10
    },
    'ollama': {
        'url': 'http://192.168.0.101:11434',
        'embedding': {
            'model': 'embeddinggemma:latest',
            'context_size': 2048,
            'token_naive_k': 2.2,
            'chunk_overlap_percent': 40,
            'keep_alive': '24h'
        }
    },
    'http': {
        'port': 8085,
        'host': '0.0.0.0',
        'llm': 'Qwen3-Coder-REAP-25B-A3B-MXFP4_MOE-GGUF:latest',
        'prompt_ru': 'Пользователь хочет знать о "${question}". Дай короткое обобщение по тому что хочет знать пользователь, используя данные предоставлненные им',
        'prompt_en': 'User wants to know about "${question}". Shorten this user query to its core meaning. Then use the extracted passages from our knowledge base (below) to form the best answer you can. Show the final answer clearly.',
        'stream': False,
        'options:': {
            'num_predict': 1000
        }
    }
}
config = def_config

doc_data_json_file_name = 'doc_data.json'
chunks_json_file_name = 'chunks.json'

logger = logging.getLogger()


def load_config(config_file):
    global silent_mode, config
    try:
        with open(config_file, "r", encoding='utf-8') as f:
            config = yaml.safe_load(f)
            logger.info(f"Config loaded from {config_file}: {config}")
    except FileNotFoundError:
        print("Going to create default configuration file.")
        with open(config_file, 'x', encoding='utf-8') as f:
            yaml.dump(config, f, allow_unicode=True)
            logger.info(f"Config saved into {config_file}: {config}")
    silent_mode = config['process']['silent']
