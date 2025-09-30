# -*- coding: utf-8 -*-
from odoo import api, fields, models
import logging
_logger = logging.getLogger(__name__)

class HRAppraisalInherited(models.Model):
    _inherit = 'hr.appraisal'

    result_id = fields.Many2one('oh.appraisal.result', string='Appraisal Result', copy=False)
    is_result_computed = fields.Boolean(string='Result Computed', default=False)
    final_percentage = fields.Float(string='Final Percentage', digits=(6,2), readonly=True)
    final_rating = fields.Char(string='Final Rating', readonly=True)
    final_result_json = fields.Text(string='Final Result JSON', readonly=True)

    def action_done(self):
        res = super(HRAppraisalInherited, self).action_done()
        for app in self:
            try:
                master = self.env['oh.appraisal.master'].search([('company_id','=',app.company_id.id)], limit=1)
                if not master:
                    _logger.debug("No oh.appraisal.master found for company %s", app.company_id.id)
                    continue

                answers = {}
                survey_inputs = self.env['survey.user_input'].search([('appraisal_id','=', app.id)])
                for su in survey_inputs:
                    for line in su.user_input_line_ids:
                        q = line.question_id
                        key = (q.variable or '').strip() or str(q.id)
                        try:
                            val = float(line.value) if line.value not in (None, '') else 0.0
                        except Exception:
                            try:
                                val = float(getattr(line, 'value', 0) or 0.0)
                            except Exception:
                                val = 0.0
                        answers[key] = val

                comp = master.compute_employee_score(app.employee_id, answers_by_item=answers)
                result = self.env['oh.appraisal.result'].create_result(master, app, app.employee_id, comp, notes=app.final_interview or '')
                app.result_id = result.id
                app.is_result_computed = True
                app.final_percentage = result.final_percentage
                app.final_rating = result.rating_label
                try:
                    app.final_result_json = result.data_json
                except Exception:
                    app.final_result_json = str(comp)
            except Exception as e:
                _logger.exception("Failed to compute/store appraisal result for appraisal %s: %s", app.id, e)
        return res
