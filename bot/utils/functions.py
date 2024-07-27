import os as _os
import pkgutil as _pkgutil
from typing import Iterator as _Iterator

from discord.ext.commands import Context as _Context
from discord.ui import View
from yaml import SafeLoader as _SafeLoader
from yaml import load as _load
import re as _re

from ..core.settings import settings as _settings
from typing import Union as _Union , Dict as _Dict, Any as _Any, Sequence as _Sequence, Optional as _Optional


def chunker(text, chunk_size: int) -> list:
    length = len(text)
    num = 0
    chunks = []

    while num < len(text):
        chunks.append(text[num:length-(length-(chunk_size))+num:])
        num+=chunk_size

    return chunks

def list_all_dirs(root_dir):
        
    for dirpath, dirnames, filenames in _os.walk(root_dir):
        for dirname in dirnames:
            full_path = _os.path.join(dirpath, dirname)
            yield full_path
    
def search_directory(path: str) -> _Iterator[str]:
    """Walk through a directory and yield all modules.

    Parameters
    ----------
    path: :class:`str`
        The path to search for modules

    Yields
    ------
    :class:`str`
        The name of the found module. (usable in load_extension)
    """
    relpath = _os.path.relpath(path)  # relative and normalized
    if ".." in relpath:
        raise ValueError("Modules outside the cwd require a package to be specified")

    abspath = _os.path.abspath(path)
    if not _os.path.exists(relpath):
        raise ValueError(f"Provided path '{abspath}' does not exist")
    if not _os.path.isdir(relpath):
        raise ValueError(f"Provided path '{abspath}' is not a directory")

    prefix = relpath.replace(_os.sep, ".")
    if prefix in ("", "."):
        prefix = ""
    else:
        prefix += "."

    for _, name, ispkg in _pkgutil.iter_modules([path]):
        if ispkg:
            yield from search_directory(_os.path.join(path, name))
        else:
            yield prefix + name

async def disable_all_items(
        view: View
):
    for item in view.children:
        try:
            item.disabled = True
        except:
            pass
    else:

        try:
            await view.message.edit(
                view=view
            )
        except:
            pass

def chunker(text, chunk_size: int):
    length = len(text)
    num = 0
    chunks = []

    while num < len(text):
        chunks.append(text[num:length-(length-(chunk_size))+num:])
        num+=chunk_size

    return chunks

def load_yaml(path: str) -> dict:
    with open(path, 'r') as f:
        data = _load(f, Loader=_SafeLoader)
    
    return data

def extract_emoji_info_from_text(text: str) -> _Union[_Dict, _Any]:
    pattern = r"<:(\w+):(\d+)>"
    matches = _re.findall(pattern, text)
    
    extracted_info = []
    for match in matches:
        name = match[0]
        id = match[1]
        extracted_info.append({"name": name, "id": id})
    
    return extracted_info



def remove_duplicates_preserve_order(
        input_list: _Sequence[_Any]
):
    seen = []
    output_list = []
    for item in input_list:
        if not item in seen:
            seen.append(item)
            output_list.append(item)
    
    return output_list