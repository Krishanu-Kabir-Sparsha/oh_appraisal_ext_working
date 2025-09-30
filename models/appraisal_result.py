# -*- coding: utf-8 -*-
from odoo import api, fields, models
import json

class OHAppraisalResult(models.Model):
    _name = 'oh.appraisal.result'
    _description = 'Appraisal Result (historic)'
    _order = 'date desc, id desc'

    name = fields.Char(string='Reference', required=True, copy=False, help="Generated reference for audit.")
    appraisal_id = fields.Many2one('hr.appraisal', string='Appraisal', ondelete='cascade')
    employee_id = fields.Many2one('hr.employee', string='Employee', required=True, ondelete='cascade')
    master_id = fields.Many2one('oh.appraisal.master', string='Master')
    date = fields.Datetime(default=lambda self: fields.Datetime.now())
    data_json = fields.Text(string='Result JSON', help='Raw result JSON for audit')
    functional_score = fields.Float(string='Functional (0..100)', digits=(6,2))
    role_score = fields.Float(string='Role (0..100)', digits=(6,2))
    common_score = fields.Float(string='Common (0..100)', digits=(6,2))
    final_percentage = fields.Float(string='Final %', digits=(6,2))
    rating_label = fields.Char(string='Rating')
    notes = fields.Text(string='Manager Notes / Improvement Plan')
    state = fields.Selection([('draft','Draft'),('confirmed','Confirmed')], default='draft')
    company_id = fields.Many2one('res.company', default=lambda self: self.env.company, required=True)

    @api.model
    def create_result(self, master, appraisal, employee, computation_result, notes=''):
        """
        Persist computation_result (the dict returned by compute_employee_score) as a result record.
        """
        vals = {
            'name': f"AR-{employee.id}-{fields.Date.today()}",
            'appraisal_id': appraisal.id if appraisal else False,
            'employee_id': employee.id,
            'master_id': master.id if master else False,
            'data_json': json.dumps(computation_result),
            'functional_score': round((computation_result.get('functional', {}).get('percent', 0.0) or 0.0), 2),
            'role_score': round((computation_result.get('role', {}).get('percent', 0.0) or 0.0), 2),
            'common_score': round((computation_result.get('common', {}).get('percent', 0.0) or 0.0), 2),
            'final_percentage': round(computation_result.get('final_percentage', 0.0) or 0.0, 2),
            'company_id': appraisal.company_id.id if appraisal and appraisal.company_id else self.env.company.id,
            'notes': notes,
            'state': 'confirmed',
            'rating_label': computation_result.get('rating_label') or ''
        }
        return self.create(vals)
