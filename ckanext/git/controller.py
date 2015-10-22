from ckan.controllers.package import PackageController
from ckan.plugins import toolkit as tk
import ckan.logic as logic
import ckan.model as model
from ckan.common import _, request, c
import ckan.lib.base as base
from ckanext.git.model import GitBranch
import git
import ConfigParser
import uuid
import os

config = ConfigParser.ConfigParser()
config.read(os.environ['CKAN_CONFIG'])

PLUGIN_SECTION = 'plugin:git'
REPO_DIR = config.get(PLUGIN_SECTION, 'repo_dir')


render = tk.render
abort = base.abort

get_action = logic.get_action
check_access = logic.check_access


def get_vars(self, id, resource_id):
    PackageController.resource_read(self, id, resource_id)

    context = {'model': model, 'session': model.Session,
               'user': c.user or c.author,
               'auth_user_obj': c.userobj,
               'for_view': True}

    dataset_type = c.pkg.type or 'dataset'

    resource_views = get_action('resource_view_list')(
        context, {'id': resource_id})
    c.resource['has_views'] = len(resource_views) > 0

    current_resource_view = None
    view_id = request.GET.get('view_id')
    if c.resource['can_be_previewed'] and not view_id:
        current_resource_view = None
    elif c.resource['has_views']:
        if view_id:
            current_resource_view = [rv for rv in resource_views
                                     if rv['id'] == view_id]
            if len(current_resource_view) == 1:
                current_resource_view = current_resource_view[0]
            else:
                abort(404, _('Resource view not found'))
        else:
            current_resource_view = resource_views[0]

    vars = {'resource_views': resource_views,
            'current_resource_view': current_resource_view,
            'dataset_type': dataset_type}

    return vars


class GitController(PackageController):
    def branch_list(self, id, resource_id):
        vars = get_vars(self, id, resource_id)

        user = model.User.by_name(c.user)
        print dir(GitBranch)
        branches = GitBranch.filter(user_id=user.id,
                                    resource_id=resource_id).all()

        c.branches = branches
        print branches
        print dir(branches)

        return render('git/branches.html', extra_vars=vars)

    def create_branch(self, id, resource_id):
        vars = get_vars(self, id, resource_id)
        repo = git.Repo(os.path.join(REPO_DIR, resource_id))
        if request.method == 'POST':
            title = request.POST.get('title')
            notes = request.POST.get('notes')
            modifications = request.POST.get('modifications')
            user = model.User.by_name(c.user)
            new_branch = repo.create_head(
                '%s-%s' % (user.name, uuid.uuid4())
            )
            resource_file_name = c.resource['url'].rsplit('/', 1)[-1]
            f = open(os.path.join(REPO_DIR, resource_id, resource_file_name),
                     'w')
            f.write(modifications.encode('utf-8'))
            f.close()
            repo.head.reference = new_branch
            resource_path = os.path.join(REPO_DIR, resource_id,
                                         resource_file_name)
            repo.index.add([resource_path])
            repo.index.commit(notes)
            GitBranch.create(user_id=user.id, resource_id=resource_id,
                             title=title, description=notes,
                             branch=new_branch.name, status='pending')
            model.repo.commit()
            # REDIRECT
        if request.method == 'GET':
            resource_file_name = c.resource['url'].rsplit('/', 1)[-1]
            repo.git.checkout('master')
            f = open(os.path.join(REPO_DIR, resource_id, resource_file_name),
                     'r')
            c.resource_content = f.read().decode('utf-8')
            f.close()
        return render('git/create_branch.html', extra_vars=vars)
