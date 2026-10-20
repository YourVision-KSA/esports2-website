"""Create the three staff groups with their narrow permissions (docs/product.md §2).

Roles: admin (superuser, created separately with createsuperuser),
referee (enter results), door (check in invitations).
Run once after migrate: python manage.py setup_roles
"""

from django.contrib.auth.models import Group, Permission
from django.core.management.base import BaseCommand

ROLE_PERMS = {
    "referee": [
        ("bracket", "view_match"),
        ("bracket", "change_match"),
    ],
    "door": [
        ("invitations", "view_invitation"),
        ("invitations", "change_invitation"),
    ],
}


class Command(BaseCommand):
    help = "Create staff groups: referee, door (admins use superuser accounts)."

    def handle(self, *args, **options):
        for role, perms in ROLE_PERMS.items():
            group, _ = Group.objects.get_or_create(name=role)
            group.permissions.set(
                Permission.objects.get(content_type__app_label=app, codename=code)
                for app, code in perms
            )
            self.stdout.write(f"group '{role}': {len(perms)} permission(s)")
        self.stdout.write(self.style.SUCCESS("Roles ready."))
