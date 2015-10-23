from ckan.controllers.package import PackageController
from ckan.plugins import toolkit as tk
import ckan.logic as logic
import ckan.model as model
from ckan.common import _, request, c
import ckan.lib.base as base
from ckanext.git.model import GitBranch
from pygments import highlight
from pygments.formatters import HtmlFormatter
from pygments.lexers.diff import DiffLexer
from pylons.controllers.util import redirect
import git
import ConfigParser
import uuid
import os
import shutil

config = ConfigParser.ConfigParser()
config.read(os.environ['CKAN_CONFIG'])

PLUGIN_SECTION = 'plugin:git'
REPO_DIR = config.get(PLUGIN_SECTION, 'repo_dir')

STORAGE_DIR = config.get('app:main', 'ckan.storage_path')

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
        branches = GitBranch.filter(user_id=user.id,
                                    resource_id=resource_id).all()

        c.branches = branches

        return render('git/branches.html', extra_vars=vars)

    def create_branch(self, id, resource_id, branch_id=None):
        vars = get_vars(self, id, resource_id)
        repo = git.Repo(os.path.join(REPO_DIR, resource_id))
        if request.method == 'POST':
            title = request.POST.get('title')
            notes = request.POST.get('notes')
            modifications = request.POST.get('modifications')
            user = model.User.by_name(c.user)
            resource_file_name = c.resource['url'].rsplit('/', 1)[-1]
            resource_path = os.path.join(REPO_DIR, resource_id,
                                         resource_file_name)
            if branch_id is None:
                new_branch = repo.create_head(
                    '%s-%s' % (user.name, uuid.uuid4())
                )

                repo.head.reference = new_branch

                f = open(os.path.join(REPO_DIR, resource_id,
                                      resource_file_name), 'w')
                f.write(modifications.encode('utf-8'))
                f.close()

                repo.index.add([resource_path])
                repo.index.commit(notes)
                GitBranch.create(user_id=user.id, resource_id=resource_id,
                                 title=title, description=notes,
                                 branch=new_branch.name, status='pending')
                model.repo.commit()
            else:
                branch = GitBranch.get(id=branch_id)
                repo.git.checkout(branch.branch)
                f = open(os.path.join(REPO_DIR, resource_id,
                                      resource_file_name), 'w')
                f.write(modifications.encode('utf-8'))
                f.close()
                repo.index.add([resource_path])
                repo.index.commit(notes)
                branch.title = title
                branch.description = notes
                branch.save()
                model.repo.commit()
            return redirect('/dataset/%s/resource/%s/git/branches' %
                            (id, resource_id))

        if request.method == 'GET':
            resource_file_name = c.resource['url'].rsplit('/', 1)[-1]
            if branch_id is not None:
                branch = GitBranch.get(id=branch_id)
                repo.git.checkout(branch.branch)
                c.branch = branch
            else:
                repo.git.checkout('master')
            f = open(os.path.join(REPO_DIR, resource_id, resource_file_name),
                     'r')
            c.resource_content = f.read().decode('utf-8')
            f.close()
        return render('git/create_branch.html', extra_vars=vars)

    def check_branches(self, id, resource_id):
        vars = get_vars(self, id, resource_id)
        branches = GitBranch.filter(resource_id=resource_id,
                                    status='pending').all()
        c.branches = branches

        return render('git/list_branches.html', extra_vars=vars)

    def check_branch(self, id, resource_id, branch_id):
        vars = get_vars(self, id, resource_id)
        branch = GitBranch.get(id=branch_id)
        repo = git.Repo(os.path.join(REPO_DIR, resource_id))
        repo.git.checkout(branch.branch)
        patch = repo.git.format_patch('master', '--stdout')
        c.patch_code = highlight(patch, DiffLexer(), HtmlFormatter(full=True))
        c.branch_id = branch_id

        return render('git/check_branch.html', extra_vars=vars)

    def accept_branch(self, id, resource_id, branch_id):
        get_vars(self, id, resource_id)
        branch = GitBranch.get(id=branch_id)
        branch.status = 'accepted'
        branch.save()
        model.repo.commit()
        repo = git.Repo(os.path.join(REPO_DIR, resource_id))
        repo.git.checkout('master')
        repo.git.merge(branch.branch)

        resource_file_name = c.resource['url'].rsplit('/', 1)[-1]
        resource_dir = resource_id[:3]
        resource_subdir = resource_id[3:6]
        resource_dir_filename = resource_id[6:]
        shutil.copyfile(os.path.join(REPO_DIR,
                                     resource_id, resource_file_name),
                        os.path.join(STORAGE_DIR, 'resources',
                                     resource_dir, resource_subdir,
                                     resource_dir_filename))

        return redirect('/dataset/%s/resource/%s/git/list' %
                        (id, resource_id))

    def discard_branch(self, id, resource_id, branch_id):
        branch = GitBranch.get(id=branch_id)
        branch.status = 'discarded'
        branch.save()
        model.repo.commit()

        return redirect('/dataset/%s/resource/%s/git/list' %
                        (id, resource_id))
