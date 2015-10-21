from ckan.controllers.package import PackageController
from ckan.plugins import toolkit as tk
import ckan.logic as logic
import ckan.model as model
from ckan.common import _, request, c
import ckan.lib.base as base

render = tk.render
abort = base.abort

get_action = logic.get_action
check_access = logic.check_access


class GitController(PackageController):
    def branch_list(self, id, resource_id):
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
        return render('git/branches.html', extra_vars=vars)
