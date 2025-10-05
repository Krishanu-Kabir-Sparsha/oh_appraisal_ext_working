# -*- coding: utf-8 -*-
from odoo import api, models

class ResUsersInherit(models.Model):
    _inherit = 'res.users'

    @api.model
    def get_dashboard_config(self):
        """
        Get current user's dashboard configuration including allowed companies
        """
        user = self.env.user
        
        return {
            'user_id': user.id,
            'company_ids': user.company_ids.ids,
            'current_company_id': user.company_id.id,
        }