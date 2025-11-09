import logging
import math
import os
import re
import shutil

import pymupdf

from py_src.data_converters import dir_tree
from py_src.utils import configuration
from py_src.utils import utils

logger = logging.getLogger()


def text_cleaning(text):
    text = re.sub(r'[^a-zA-Zа-яА-ЯёЁ0-9.,\s\n{}\[\]]', '', text)
    text = text.replace(' .', '.')
    text = re.sub(r'\n+', ' ', text)
    text = re.sub(r' +', ' ', text)
    text = re.sub(r'\.+', '.', text)
    return text


def pdg_to_text_and_img(file_name, root_path, doc_index):
    trunc_file_name = file_name[:-4]
    data_path = os.path.join(root_path, f".d-{trunc_file_name}")
    if os.path.isdir(data_path):
        return  # already exist
    tmp_path = str(os.path.join(root_path, f".t-{trunc_file_name}"))
    if os.path.isdir(tmp_path):
        shutil.rmtree(tmp_path)  # start from begin
    os.makedirs(tmp_path, exist_ok=True)
    if not configuration.silent_mode:
        print(f"\rPDF parsing process (pdf->img+text) for file '{file_name}'")

    json_doc_file = str(os.path.join(tmp_path, configuration.doc_data_json_file_name))
    pdf_file_name = str(os.path.join(root_path, file_name))
    doc = pymupdf.open(pdf_file_name)
    json_doc = {'src': pdf_file_name.replace(os.sep, "/"),
                'num_pages': doc.page_count,
                'index': doc_index,
                'pages': []}

    add_json_data_file_name = str(os.path.join(root_path, trunc_file_name+'.jsn')) # confluence2pdf.py
    if os.path.exists(add_json_data_file_name):
        json_doc = {**json_doc, **utils.load_json(add_json_data_file_name)}
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
                f"pdf '{file_name}' clipped by header_height='{header_height}'  footer_height='{footer_height}'")
            break

    for page in doc:  # iterate through the pages
        pix = page.get_pixmap()  # render page to an image
        pix.save(str(os.path.join(tmp_path, f"p{page.number}.png")))
        pages.append({'n': page.number, 'text': text_cleaning(page.get_text(clip=clip_rect))})
        utils.show_spinner(f"{math.ceil(page.number / doc.page_count * 1000) / 10}%")

    utils.save_json(json_doc_file, json_doc)
    os.rename(tmp_path, data_path)


def handle_pdf_files_in_output_path(output_path):
    for root_path, dirs, files in os.walk(output_path):
        files_pdf = [file for file in files if file.lower().endswith('.pdf')]
        doc_index = os.path.normpath(os.path.relpath(root_path, output_path)).split(os.sep)
        logger.debug(f"handle root: '{root_path}' files: {files} ")
        for file_name in files_pdf:
            pdg_to_text_and_img(file_name, root_path, doc_index)

def copy_pdf_files_input2output(input_path, output_path):
    if not configuration.silent_mode:
        print(f"Copy PDF files from {input_path} to {output_path}")
    for root, dirs, files in os.walk(input_path):
        files_pdf = [file for file in files if file.lower().endswith('.pdf')]
        dst_root = output_path + root[root.find(input_path) + len(input_path):]
        for file in files_pdf:
            dst_pdf_file_name = str(os.path.join(dst_root, file))
            src_pdf_file_name = str(os.path.join(root, file))
            if not os.path.exists(dst_pdf_file_name):
                os.makedirs(dst_root, exist_ok=True)
                shutil.copy(src_pdf_file_name, dst_pdf_file_name)
                logger.debug(
                    f"copy_pdf_file_to_output_path. File {src_pdf_file_name} copied into {dst_pdf_file_name} successfully.")
            else:
                logger.debug(
                    f"copy_pdf_file_to_output_path. Destination file '{dst_pdf_file_name}' already exists. No copy performed.")

def process_pdf():
    path_config = configuration.config["path"]
    input_path = path_config['input']
    output_path = path_config["output"]
    # ============
    copy_pdf_files_input2output(input_path, output_path)
    # ============
    dir_tree.build_and_save_tree(output_path)
    # ============
    handle_pdf_files_in_output_path(output_path)
    # ============
