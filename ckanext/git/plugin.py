import ckan.plugins as plugins
import ckan.plugins.toolkit as toolkit
import git
import ConfigParser
import os
import requests
import shutil

from routes.mapper import SubMapper
from ckanext.git.model import setup as model_setup

config = ConfigParser.ConfigParser()
config.read(os.environ['CKAN_CONFIG'])

PLUGIN_SECTION = 'plugin:git'
REPO_DIR = config.get(PLUGIN_SECTION, 'repo_dir')


class GitPlugin(plugins.SingletonPlugin):
    plugins.implements(plugins.IConfigurer)
    plugins.implements(plugins.IResourceController)
    plugins.implements(plugins.IRoutes, inherit=True)
    plugins.implements(plugins.IConfigurable)

    # IConfigurer

    def update_config(self, config_):
        toolkit.add_template_directory(config_, 'templates')
        toolkit.add_public_directory(config_, 'public')
        toolkit.add_resource('fanstatic', 'git')

    # IConfigurable

    def configure(self, config):
        model_setup()

    # IRoutes

    def before_map(self, map):
        with SubMapper(
                map,
                controller='ckanext.git.controller:GitController') as m:
            m.connect('branch_list',
                      '/dataset/{id}/resource/{resource_id}/git/branches',
                      action='branch_list', ckan_icon='edit')
            m.connect('create_branch',
                      '/dataset/{id}/resource/{resource_id}/git/new',
                      action='create_branch', ckan_icon='plus')
            m.connect(
                'edit_branch',
                '/dataset/{id}/resource/{resource_id}/git/edit/{branch_id}',
                action='create_branch', ckan_icon='plus'
            )
            m.connect(
                'check_branches',
                '/dataset/{id}/resource/{resource_id}/git/list',
                action='check_branches', ckan_icon='plus'
            )
            m.connect(
                'check_branch',
                '/dataset/{id}/resource/{resource_id}/git/check/{branch_id}',
                action='check_branch', ckan_icon='plus'
            )
            m.connect('accept_branch',
                      '/dataset/{id}/resource/{resource_id}/git/check/{branch_id}/accept',
                      action='accept_branch', ckan_icon='plus')
            m.connect('discard_branch',
                      '/dataset/{id}/resource/{resource_id}/git/check/{branch_id}/discard',
                      action='discard_branch', ckan_icon='plus')

        return map

    # IResourceController

    def after_create(self, context, resource):
        repo = git.Repo.init(os.path.join(REPO_DIR, resource['id']))
        response = requests.get(resource['url'])
        resource_file_name = response.url.rsplit('/', 1)[-1]
        resource_path = os.path.join(REPO_DIR, resource['id'],
                                     resource_file_name)
        f = open(resource_path, 'w')
        f.write(response.text.encode('utf-8'))
        f.close()
        repo.index.add([resource_path])
        repo.index.commit("First commit")
        return resource

    def before_show(self, resource_dict):
        return resource_dict

    def before_create(self, context, resource):
        return resource

    def before_delete(self, context, resource, resources):
        print resource
        shutil.rmtree(os.path.join(REPO_DIR, resource['id']))
        return resource

    def after_delete(self, context, resources):
        return resources
