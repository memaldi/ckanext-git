from sqlalchemy import Table
from sqlalchemy import Column
from sqlalchemy import ForeignKey
from sqlalchemy import types

from ckan.model.meta import metadata, mapper, Session
from ckan import model
from ckan.model.domain_object import DomainObject

import logging
log = logging.getLogger(__name__)


git_branch_table = None


def setup():
    if git_branch_table is None:
        define_git_branch_table()
        log.debug('GitBranchTable table defined in memory')

    if model.resource_table.exists():
        if not git_branch_table.exists():
            git_branch_table.create()
            log.debug('GitBranchTable table create')
        else:
            log.debug('GitBranchTable table already exists')
    else:
        log.debug('GitBranchTable table creation deferred')


class GitBranch(DomainObject):
    @classmethod
    def filter(cls, **kwargs):
        return Session.query(cls).filter_by(**kwargs)

    @classmethod
    def exists(cls, **kwargs):
        if cls.filter(**kwargs).first():
            return True
        else:
            return False

    @classmethod
    def get(cls, **kwargs):
        instance = cls.filter(**kwargs).first()
        return instance

    @classmethod
    def create(cls, **kwargs):
        instance = cls(**kwargs)
        Session.add(instance)
        Session.commit()
        return instance.as_dict()


def define_git_branch_table:
    global git_branch_table

    git_branch_table = Table(
        'git_branch', metadata,
        Column('id', types.Integer,
               primary_key=True,
               nullable=False,
               autoincrement=True),
        Column('resource_id', types.UnicodeText,
               ForeignKey('resource.id',
                          ondelete='CASCADE',
                          onupdate='CASCADE'),
               nullable=False),
        Column('user_id', types.UnicodeText,
               ForeignKey('user.id',
                           ondelete='CASCADE',
                           onupdate='CASCADE'),
               nullable=False),
        Column('branch', types.UnicodeText,
               nullable=False),
        Column('title', types.Text,
                nullable=False),
        Column('description', types.Text,
               nullable=True),
        Column('status', types.UnicodeText,
               nullable=False)
    )

    mapper(
        GitBranch,
        git_branch_table,
    )
