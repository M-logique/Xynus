import os as _os
import pkgutil as _pkgutil
import re as _re
from ast import Expr, If, Return, With, fix_missing_locations
from base64 import b64decode as _b64decode
from base64 import b64encode as _b64encode
from datetime import timedelta as _timedelta
from difflib import get_close_matches as _get_close_matches
from inspect import Parameter as _Parameter
from typing import Any as _Any
from typing import Dict as _Dict
from typing import Iterator as _Iterator
from typing import Optional as _Optional
from typing import Sequence as _Sequence
from typing import Union as _Union

from discord import Forbidden as _Forbidden
from discord import HTTPException as _HTTPException
from discord.ext.commands import Cog as _Cog
from discord.ext.commands import Command as _Command
from discord.ext.commands import Group as _Group
from discord.ui import View
from yaml import SafeLoader as _SafeLoader
from yaml import load as _load


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

        if hasattr(item, "disabled"):
            item.disabled = True

    else:

        try:

            await view.message.edit(
                view=view
            )

        except (_Forbidden, _HTTPException):
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


def split_camel_case(
        text: str
):
    return _re.sub(r'(?<!^)(?=[A-Z])', ' ', text)



def parse_time(
        time_str: str
):
    """ Parse a time string like '1d2h3m4s' into a timedelta object. """
    time_regex = _re.compile(r"(\d+)([smhd])")


    total_seconds = 0
    matches = time_regex.findall(time_str)
    for value, unit in matches:
        unit = unit.lower() if unit else None
        if unit == 's':
            total_seconds += int(value)
        elif unit == 'm':
            total_seconds += int(value) * 60
        elif unit == 'h':
            total_seconds += int(value) * 3600
        elif unit == 'd':
            total_seconds += int(value) * 86400

    
    return _timedelta(seconds=total_seconds)

def get_all_commands(
        cog: _Optional[_Cog] = None,
        commands: _Sequence[_Command] = None
):

    if cog is None and commands is None: 
        raise ValueError("Invalid usage")


    raw_commands: _Sequence[_Union[_Command, _Group]] = []
    all_commands: _Sequence[_Command] = []

    if cog:
        raw_commands+=[*cog.get_commands()]
    
    if commands:
        raw_commands+=[*commands]

    
    for command in raw_commands:
        all_commands.append(command)
        if isinstance(command, _Group):
            all_commands+=[*command.commands]
            for command in command.commands:
                if isinstance(command, _Group):
                    all_commands+=[*command.commands]

    

    return all_commands



filter_prefix = lambda prefix: [prefix] if isinstance(prefix, str) else [*set([i.strip() for i in filter(lambda x: "@" not in x, prefix)])]


def format_command_params(
        command: _Command
) -> str:
    """
    Formats the parameters of a command into a string signature.
    """

    # Co-Authored by catssomecat aka ElysianCat

    # Initialize an empty list to collect the signature components
    signature_parts: _Sequence[str] = []

    # Get the cleaned parameters from the command
    params: _Dict[str, _Any] = command.clean_params

    for name, param in params.items():
        # Check if the parameter has no default value and no annotation
        if param.default is param.empty and param.annotation is param.empty or (param.default is _Parameter.empty):
            # Add the parameter as a required one
            signature_parts.append(f"<{name}>")
        else:
            # Initialize the signature for optional parameters
            param_signature: str = f"[{name}"
            
            # Append the default value if it exists
            if param.default is not param.empty:
                param_signature += f"={param.default}"
                
            param_signature += "]"
            
            # Add the optional parameter to the signature parts
            signature_parts.append(param_signature)

    # Join all the parts into a single string separated by spaces
    return " ".join(signature_parts)


def suggest_similar_strings(
        target: str, 
        string_list: _Sequence[str], 
        n: _Optional[int] = 3, 
        cutoff: _Optional[int] =0.6
) -> _Union[str, _Sequence[str]]:
    close_matches = _get_close_matches(target, string_list, n=n, cutoff=cutoff)
    

    return close_matches

def insert_returns(body):
    # insert return stmt if the last expression is an expression statement
    if isinstance(body[-1], Expr):
        body[-1] = Return(body[-1].value)
        fix_missing_locations(body[-1])

    # for if statements, we insert returns into the body and the orelse
    if isinstance(body[-1], If):
        insert_returns(body[-1].body)
        insert_returns(body[-1].orelse)

    # for with blocks, again we insert returns into the body
    if isinstance(body[-1], With):
        insert_returns(body[-1].body)


def encrypt(text: str, /) -> str:
    """To quickly encode a text to base64."""

    if text is not None:
        return _b64encode(str(text).encode("utf-8")).decode("utf-8")

def decrypt(text: str, /) -> str:
    """To quickly decode an encrypted text."""
    
    if text is not None:
        return _b64decode(str(text).encode("utf-8")).decode("utf-8")
    
    
