import ckan.plugins as plugins
import ckan.plugins.toolkit as toolkit
import git
import ConfigParser
import os
import requests
import shutil

config = ConfigParser.ConfigParser()
config.read(os.environ['CKAN_CONFIG'])

PLUGIN_SECTION = 'plugin:git'
REPO_DIR = config.get(PLUGIN_SECTION, 'repo_dir')


class GitPlugin(plugins.SingletonPlugin):
    plugins.implements(plugins.IConfigurer)
    plugins.implements(plugins.IResourceController)

    # IConfigurer

    def update_config(self, config_):
        toolkit.add_template_directory(config_, 'templates')
        toolkit.add_public_directory(config_, 'public')
        toolkit.add_resource('fanstatic', 'git')

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