# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
import json

class OHAppraisalSimulation(models.TransientModel):
    _name = 'oh.appraisal.simulation'
    _description = 'Simulation Wizard for Appraisal Master'

    master_id = fields.Many2one('oh.appraisal.master', string='Master', required=True, help="Select the master configuration to simulate.")
    employee_id = fields.Many2one('hr.employee', string='Employee', help="Optional employee to use department/role fallbacks.")
    answers_json = fields.Text(string='Answers (JSON)', help='Provide JSON mapping of item codes to values or reviewer dicts. Example: {"code1":4,"code2":{"self":4,"peer":3}}')

    def action_run(self):
        self.ensure_one()
        try:
            answers = json.loads(self.answers_json or '{}')
            if not isinstance(answers, dict):
                raise ValueError("Answers JSON must be an object/dict.")
        except Exception as e:
            raise models.ValidationError(_("Invalid Answers JSON: %s") % e)
        comp = self.master_id.compute_employee_score(self.employee_id, answers_by_item=answers)
        try:
            self.master_id.last_sim_result = json.dumps(comp, indent=2)
        except Exception:
            self.master_id.last_sim_result = str(comp)
        self.master_id.last_sim_final_percentage = comp.get('final_percentage', 0.0)
        self.master_id.last_sim_rating = comp.get('rating_label') or ''
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'oh.appraisal.master',
            'res_id': self.master_id.id,
            'view_mode': 'form',
            'target': 'current',
        }
