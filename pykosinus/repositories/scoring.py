from typing import List, Optional

import peewee as pw

from pykosinus import Conf

db = pw.SqliteDatabase(None)


class BaseModel(pw.Model):
    class Meta:
        database = db


class BaseData(BaseModel):
    _id = pw.PrimaryKeyField()
    identifier = pw.TextField(null=True)
    content = pw.TextField()
    section = pw.TextField(null=True)


class ProcessedData(BaseModel):
    _id = pw.PrimaryKeyField()
    base_data = pw.ForeignKeyField(BaseData, backref="backrefs")
    content = pw.TextField()


def init_database(dbname: str) -> None:
    db.init(dbname)
    db.connect(reuse_if_open=True)
    db.create_tables([BaseData, ProcessedData])


def base_data_exists(
    content: str, identifier: Optional[str] = None, section: Optional[str] = None
) -> bool:
    return (
        BaseData.select(BaseData._id)
        .where(
            (BaseData.identifier == identifier)
            & (BaseData.content == content)
            & (BaseData.section == section)
        )
        .exists()
    )


def create_base_data(
    content: str, identifier: Optional[str] = None, section: Optional[str] = None
) -> None:
    if not base_data_exists(content, identifier, section):
        data = BaseData(identifier=identifier, content=content, section=section)
        data.save()


def get_all_base_data(
    offset: Optional[int] = None, size: Optional[int] = None
) -> List[BaseData]:
    if offset is not None and size is not None:
        offset = int(offset / size) + 1
        return results if (results := BaseData.select().paginate(offset, size)) else []
    return list(results) if (results := BaseData.select()) else []


def count_total_base_data() -> int:
    return BaseData.select().count()


def processed_data_exists(base_data: BaseData, content: str) -> bool:
    return (
        ProcessedData.select(ProcessedData._id)
        .where(
            (ProcessedData.base_data == base_data) & (ProcessedData.content == content)
        )
        .exists()
    )


def create_processed_data(base_data: BaseData, content: str) -> None:
    if not processed_data_exists(base_data, content):
        data = ProcessedData(base_data=base_data, content=content)
        data.save()


def get_processed_data_by_id(_id: int) -> ProcessedData:
    return ProcessedData.get_by_id(_id)


def get_processed_data_by_content(content: str) -> List[ProcessedData]:
    return list(ProcessedData.select().where(ProcessedData.content == content))


def get_all_processed_data() -> List[ProcessedData]:
    return list(ProcessedData.select())


def count_total_processed_data() -> int:
    return ProcessedData.select().count()


def initialize(conf: Conf) -> None:
    init_database(conf.sqlite_location)
