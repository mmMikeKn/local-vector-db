import logging
import os

from py_src.utils import utils

logger = logging.getLogger()

def load_paths_tree_json(output_path):
    json_tree_file = str(os.path.join(output_path, 'tree.json'))
    try:
        tree_json = utils.load_json(json_tree_file)
    except Exception as e:
        logger.warning(f"Failed to load tree from {json_tree_file}: {e}")
        tree_json = {'index': []}
    logger.debug(f"loaded tree: {tree_json}")
    return tree_json


def build_and_save_tree(output_path):
    def traverse(current_path):
        name = os.path.basename(current_path)
        tree = {'name': name}
        children = []
        for path_entry in os.scandir(current_path):
            if path_entry.is_dir() and not path_entry.name.startswith("."):
                children.append(traverse(path_entry.path))
        if children:
            tree["sub"] = children
        return tree

    # Обрабатываем корневой путь
    root_tree = []
    for entry in os.scandir(output_path):
        if entry.is_dir():
            root_tree.append(traverse(entry.path))
    utils.save_json(str(os.path.join(output_path, 'tree.json')), root_tree, json_indent=2)


