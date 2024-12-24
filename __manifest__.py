# pylint: disable=missing-module-docstring,pointless-statement
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
{
    ###########################
    # Delete all the commented lines after editing the module
    ###########################
    "name": "Import Own Checks",
    "summary": """
        This module will allow you to import your own emmited checks while implementing a new odoo version""",
    "author": "Be OnlyOne",
    "maintainers": ["onlyone-odoo"],
    "website": "https://onlyone.odoo.com/",
    "license": "AGPL-3",
    "category": "Technical Settings",
    "version": "17.0.1.0.0",
    "development_status": "Production/Stable",
    "application": False,
    "installable": True,
    "depends": [
        "base",
        "account",
        "account_payment_group",
        "l10n_latam_check",  # Asegurate de que este sea el nombre correcto
    ],
    "data": [
        "security/ir.model.access.csv",
        "views/import_own_checks_wizard_view.xml",
        "views/menu.xml",
    ],
    "installable": True,
    "application": False,
}
