# ---------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# ---------------------------------------------------------
from os import PathLike
from pathlib import Path
from typing import IO, AnyStr, Optional, Union

from dotenv import dotenv_values

from .._utils.logger_utils import get_cli_sdk_logger
from .._utils.yaml_utils import load_yaml
from .entities import Run
from .entities._connection import CustomConnection, _Connection
from .entities._flow import Flow

logger = get_cli_sdk_logger()


def load_common(
    cls,
    source: Union[str, PathLike, IO[AnyStr]],
    relative_origin: str = None,
    params_override: Optional[list] = None,
    **kwargs,
):
    """Private function to load a yaml file to an entity object.

    :param cls: The entity class type.
    :type cls: type[Resource]
    :param source: A source of yaml.
    :type source: Union[str, PathLike, IO[AnyStr]]
    :param relative_origin: The origin of to be used when deducing
        the relative locations of files referenced in the parsed yaml.
        Must be provided, and is assumed to be assigned by other internal
        functions that call this.
    :type relative_origin: str
    :param params_override: _description_, defaults to None
    :type params_override: list, optional
    """
    if relative_origin is None:
        if isinstance(source, (str, PathLike)):
            relative_origin = source
        else:
            try:
                relative_origin = source.name
            except AttributeError:  # input is a stream or something
                relative_origin = "./"

    params_override = params_override or []
    yaml_dict = load_yaml(source)

    logger.debug(f"Resolve cls and type with {yaml_dict}, params_override {params_override}.")
    # pylint: disable=protected-access
    cls, type_str = cls._resolve_cls_and_type(data=yaml_dict, params_override=params_override)

    try:
        return cls._load(
            data=yaml_dict,
            yaml_path=relative_origin,
            params_override=params_override,
            **kwargs,
        )
    except Exception as e:
        raise Exception(f"Load entity error: {e}") from e


def load_flow(
    source: Union[str, PathLike, IO[AnyStr]],
    **kwargs,
) -> Flow:
    """Load flow from YAML file.

    :param source: The local yaml source of a flow. Must be a path to a local file.
        If the source is a path, it will be open and read.
        An exception is raised if the file does not exist.
    :type source: Union[PathLike, str]
    :return: A Flow object
    :rtype: Flow
    """
    return Flow.load(source, **kwargs)


def load_run(
    source: Union[str, PathLike, IO[AnyStr]],
    params_override: Optional[list] = None,
    **kwargs,
) -> Run:
    """Load run from YAML file.

    :param source: The local yaml source of a run. Must be a path to a local file.
        If the source is a path, it will be open and read.
        An exception is raised if the file does not exist.
    :type source: Union[PathLike, str]
    :param params_override: Fields to overwrite on top of the yaml file.
        Format is [{"field1": "value1"}, {"field2": "value2"}]
    :type params_override: List[Dict]
    :return: A Run object
    :rtype: Run
    """
    data = load_yaml(source=source)
    return Run._load(data=data, yaml_path=source, params_override=params_override, **kwargs)


def load_connection(
    source: Union[str, PathLike, IO[AnyStr]],
    **kwargs,
):
    if Path(source).name.endswith(".env"):
        return _load_env_to_connection(source, **kwargs)
    return load_common(_Connection, source, **kwargs)


def _load_env_to_connection(
    source,
    params_override: Optional[list] = None,
    **kwargs,
):
    source = Path(source)
    name = next((_dct["name"] for _dct in params_override if "name" in _dct), None)
    if not name:
        raise Exception("Please specify --name when creating connection from .env.")
    if not source.exists():
        raise FileNotFoundError(f"File {source.absolute().as_posix()!r} not found.")
    try:
        data = dict(dotenv_values(source))
        if not data:
            # Handle some special case dotenv returns empty with no exception raised.
            raise ValueError(
                f"Load nothing from dotenv file {source.absolute().as_posix()!r}, "
                "please make sure the file is not empty and readable."
            )
        return CustomConnection(name=name, secrets=data)
    except Exception as e:
        raise Exception(f"Load entity error: {e}") from e
