from odoo import models

from odoo.addons.envia.hooks import (
    _sync_envia_settings_field_translations,
    _sync_envia_settings_view_translations,
)


class IrModuleModule(models.Model):
    _inherit = "ir.module.module"

    def _update_translations(self, filter_lang=None, overwrite=False):
        res = super()._update_translations(filter_lang=filter_lang, overwrite=overwrite)
        if any(module.name == "envia" for module in self):
            _sync_envia_settings_field_translations(self.env.cr)
            _sync_envia_settings_view_translations(self.env)
        return res
