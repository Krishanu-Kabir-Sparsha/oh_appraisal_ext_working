# -*- coding: utf-8 -*-
from odoo import models, api

class ResUsers(models.Model):
    _inherit = 'res.users'

    @api.model
    def get_companies(self):
        """Get allowed companies for current user"""
        return [(c.id, c.name) for c in self.env.companies if self.has_group('base.group_user')]