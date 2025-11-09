import argparse
import logging.config
import os
import subprocess

from py_src.utils import configuration, utils

logger = logging.getLogger()


# LibreOffice mast be installed

def process_docx():
    path_config = configuration.config["path"]
    input_path = path_config['input']
    output_path = path_config["output"]

    if not configuration.silent_mode:
        print(f"Convert DOCX->PDF. from {input_path} to {output_path} ")
    all_cnt = 0
    already_cnt = 0
    converted_cnt = 0
    error_cnt = 0
    error_cmd = []
    for root, dirs, files in os.walk(input_path):
        files_docx = [file for file in files if file.lower().endswith('.docx') and not file.startswith('~$')]
        dst_root = output_path + root[root.find(input_path) + len(input_path):]
        for file in files_docx:
            utils.show_spinner(f" {all_cnt}/{already_cnt}/{converted_cnt}  ")
            all_cnt += 1
            dst_pdf_file_name = str(os.path.join(dst_root, file.replace('.docx', '.pdf')))
            src_docx_file_name = str(os.path.join(root, file))
            if not os.path.exists(dst_pdf_file_name):
                os.makedirs(dst_root, exist_ok=True)
                cmd = [r'"C:\Program Files\LibreOffice\program\soffice.exe"', '--headless', '--convert-to', 'pdf',
                       '--outdir', '"' + dst_root + '"',
                       '"' + src_docx_file_name + '"']
                cmd_str = " ".join(cmd)
                logger.debug(f"run cmd: {cmd_str}")
                try:
                    subprocess.run(cmd, check=True, capture_output=True, text=True)
                    converted_cnt += 1
                    logger.debug(
                        f"DOCX->PDF. File {src_docx_file_name} converted into {dst_pdf_file_name} successfully.")
                except Exception as e:
                    if isinstance(e, subprocess.CalledProcessError):
                        logger.error(f"file '{src_docx_file_name}'->'{dst_pdf_file_name}' failed. error: {e}"
                                 f"\n\tcmd: {cmd_str}"
                                 f"\n\tstdout: {e.stdout}"
                                 f"\n\tstderr: {e.stderr}")
                    else:
                        logger.error(f"RUN error: {e}\n\tcmd: {cmd_str}")
                    error_cmd.append(cmd_str)
                    error_cnt += 1
            else:
                already_cnt += 1
                logger.debug(
                    f"DOCX->PDF. Destination file '{dst_pdf_file_name}' already exists. No converting performed.")

    msg = f"DOCX->PDF finished. all_cnt:{all_cnt}, error_cnf:{error_cnt} already_cnt:{already_cnt}, converted_cnt:{converted_cnt}"
    print('\r' + msg)
    logger.info(msg)
    if error_cmd:
        with open('./doc2pdf.cmd', 'w', encoding='cp866') as f:
            for line in error_cmd:
                f.write(str(line) + '\n')

if __name__ == "__main__":
    logging.config.fileConfig('log_config.ini')
    parser = argparse.ArgumentParser(description="Process arguments")
    parser.add_argument("--config", help="config file", default="config.yml")
    args = parser.parse_args()
    configuration.load_config(args.config)
    process_docx()
