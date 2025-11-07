import logging
import math
import os
import re
import shutil

import pymupdf

from py_src.utils import configuration
from py_src.utils import utils

logger = logging.getLogger()


def copy_pdf_file_to_output_path(pdf_file, src_path, dst_path, dst_file_pdf):
    src_file = str(os.path.join(src_path, pdf_file))
    if not os.path.exists(dst_file_pdf):
        os.makedirs(dst_path, exist_ok=True)
        shutil.copy(src_file, dst_file_pdf)
        logger.debug(f"copy_pdf_file_to_output_path. File {src_file} copied into {dst_file_pdf} successfully.")
    else:
        logger.debug(
            f"copy_pdf_file_to_output_path. Destination file '{dst_file_pdf}' already exists. No copy performed.")


def text_cleaning(text):
    text = re.sub(r'[^a-zA-Zа-яА-ЯёЁ0-9.,\s\n{}\[\]]', '', text)
    text = text.replace(' .', '.')
    text = re.sub(r'\n+', ' ', text)
    text = re.sub(r' +', ' ', text)
    text = re.sub(r'\.+', '.', text)
    return text


def pdg_to_test_and_img(pdf_file, dst_path, dst_file_pdf, doc_index):
    trunc_file_name = pdf_file[:-4]
    data_path = os.path.join(dst_path, f".d-{trunc_file_name}")
    if os.path.isdir(data_path):
        return # already exist
    tmp_path = str(os.path.join(dst_path, f".t-{trunc_file_name}"))
    if os.path.isdir(tmp_path):
        shutil.rmtree(tmp_path) # start from begin
    os.makedirs(tmp_path, exist_ok=True)
    if not configuration.silent_mode:
        print(f"\rPDF parsing process (pdf->img+text) for file '{pdf_file}'")

    json_doc_file = str(os.path.join(tmp_path, configuration.doc_data_json_file_name))
    doc = pymupdf.open(dst_file_pdf)
    json_doc = {'src': str(os.path.join(dst_path, pdf_file)).replace(os.sep, "/"),
                'num_pages': doc.page_count,
                'index': doc_index,
                'pages': []}
    pages = json_doc['pages']
    page0 = doc[0]
    clip_rect = page0.rect
    for item in configuration.config['process']['pdf_clip']:
        text = page0.get_text()
        # logger.debug(f">>>>>>>>>>>text='{text}'\n>>>>>>>item {item}")
        if item['text'] in text:
            header_height = item['header_height']
            footer_height = item['footer_height']
            clip_rect.y0 += header_height  # Adjust top to exclude header
            clip_rect.y1 -= footer_height
            logger.debug(
                f"pdf '{pdf_file}' clipped by header_height='{header_height}'  footer_height='{footer_height}'")
            break

    for page in doc:  # iterate through the pages
        pix = page.get_pixmap()  # render page to an image
        pix.save(str(os.path.join(tmp_path, f"p{page.number}.png")))
        pages.append({'n': page.number, 'text': text_cleaning(page.get_text(clip=clip_rect))})
        utils.show_spinner(f"{math.ceil(page.number / doc.page_count * 1000) / 10}%")

    utils.save_json(json_doc_file, json_doc)
    os.rename(tmp_path, data_path)


def handle_pdf_file(pdf_file, src_path, dst_path, doc_index):
    logger.debug(f"----- handle_pdf_file. src_path: {src_path} dst_path: {dst_path} file: {pdf_file}")
    dst_file_pdf = str(os.path.join(dst_path, pdf_file))
    copy_pdf_file_to_output_path(pdf_file, src_path, dst_path, dst_file_pdf)
    pdg_to_test_and_img(pdf_file, dst_path, dst_file_pdf, doc_index)


def process_pdf():
    path_config = configuration.config["path"]
    input_path = path_config['input']
    output_path = path_config["output"]
    json_tree_file = str(os.path.join(output_path, 'tree.json'))
    try:
        tree_json = utils.load_json(json_tree_file)
    except Exception as e:
        logger.warning(f"Failed to load tree from {json_tree_file}: {e}")
        tree_json = {'index': []}
    logger.debug(f"loaded tree: {tree_json}")

    logger.info(f"Processing PDF files from {input_path}")
    for root, dirs, files in os.walk(input_path):
        files_pdf = [file for file in files if file.lower().endswith('.pdf')]
        if len(files_pdf):
            dst_root = output_path + root[root.find(input_path) + len(input_path):]
            sub_paths = os.path.normpath(os.path.relpath(root, input_path)).split(os.sep)
            logger.debug(f"input_subpath '{sub_paths}'")
            tree_list = tree_json['index']
            for sub_path in sub_paths:
                # noinspection PyTypeChecker
                item = next((item for item in tree_list if item['name'] == sub_path), None)
                if item is None:
                    item = {'name': sub_path, 'sub': []}
                    tree_list.append(item)
                tree_list = item["sub"]
            logger.debug(f"handle input_root: '{root}'  output_root: '{dst_root}' files: {files} ")
            for file in files_pdf:
                handle_pdf_file(file, root, dst_root, sub_paths)

    utils.save_json(json_tree_file, tree_json)
