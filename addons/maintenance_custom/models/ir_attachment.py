import base64
import requests
from odoo import models, fields, api, _
from odoo.exceptions import UserError


class IrAttachment(models.Model):
    _inherit = 'ir.attachment'
    image_url = fields.Char(string='Image Url', compute='_get_image_url')

    def _get_image_url(self):
        image_types = ["image/jpeg", "image/png", "image/tiff",
                       "image/vnd.microsoft.icon", "image/x-icon",
                       "image/vnd.djvu", "image/svg+xml", "image/gif"]
        for rec in self:
            if rec.mimetype not in image_types:
                continue
            if rec.url:
                rec.image_url = rec.url
                continue
            if rec.datas:
                base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
                rec.image_url = base_url + '/lf/i/%s' % (base64.urlsafe_b64encode(str(rec.id).encode("utf-8")).decode("utf-8"))