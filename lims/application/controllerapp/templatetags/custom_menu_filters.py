from django import template
from django.conf import settings
from jazzmin.utils import make_menu

register = template.Library()


def get_settings():
    return getattr(settings, 'JAZZMIN_SETTINGS', {})


@register.simple_tag(takes_context=True)
def filtered_top_menu(context, user, admin_site='admin'):
    request = context['request']
    options = get_settings()
    if "icons" not in options:
        options["icons"] = {}

    if "default_icon_children" not in options:
        options["default_icon_children"] = "fas fa-folder"

    topmenu_links = options.get('topmenu_links', [])

    # Fetch user jobtype from session
    current_jobtype_raw = request.session.get('currentjobtype', '')
    if '-' in current_jobtype_raw:
        user_jobtype = current_jobtype_raw.split('-')[1].lower()
    else:
        user_jobtype = current_jobtype_raw.lower()

    # Define disallowed modules for jobtypes (modules inside 'sample' app)
    disallowed_modules_for_jobtype = {
        'accessioning': {
            'sample': ['samples'],
            'tests': ['tests'],
        },
        'ihc': {
            'sample': ['samples'],
        },
    }

    disallowed_modules = disallowed_modules_for_jobtype.get(user_jobtype, {})

    # Build full menu
    full_menu = make_menu(user, topmenu_links, options, allow_appmenus=True, admin_site=admin_site)

    def filter_models(menu_items):
        filtered_items = []
        for item in menu_items:
            url = item.get('url', '').lower()
            module_name = item.get('name', '').lower()

            cleaned_url = url.strip('/')

            segmented = cleaned_url.split('/')
            app_name = ''
            if len(segmented) >= 2:
                app_name = segmented[1]

            disallowed_by_app = disallowed_modules.get(app_name, [])

            if module_name in disallowed_by_app:
                continue

            children = item.get('children')
            if children is None:
                filtered_children = []
            else:
                filtered_children = filter_models(children)

            if children is not None and not filtered_children:
                continue

            item['children'] = filtered_children
            filtered_items.append(item)

        return filtered_items

    filtered_menu = filter_models(full_menu)
    return filtered_menu
