from odoo import models, fields, api, _
from datetime import timedelta


class LogicRecruitmentForm(models.Model):
    _name = 'logic.recruitment.form'
    _description = 'Logic Recruitment Form'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'display_name'

    designation_id = fields.Many2one('hr.job', string='Designation')
    manager_id = fields.Many2one('hr.employee', string='Manager', related='department_id.manager_id')
    expected_date = fields.Date(string='Expected Date', compute='_on_change_date', store=True, readonly=False)
    date = fields.Date(string='Date', default=fields.Date.today, required=True)
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company)
    job_position = fields.Char(string='Job Position')
    no_of_recruitment = fields.Integer(string='No of Recruitment')
    state = fields.Selection([
        ('draft', 'Draft'), ('hr_approval', 'HR Approval'), ('done', 'Done'), ('rejected', 'Rejected')
    ], default='draft', string='Status', tracking=1)

    def _compute_display_name(self):
        for rec in self:
            rec.display_name = rec.job_position + ' - ' + 'for - ' + str(rec.department_id.name)

    @api.onchange('date')
    def _on_change_job_position(self):
        dep = []
        print(self.env.user.name, 'user')
        if self.date:
            department1 = self.env['hr.department'].sudo().search([('manager_id', '=', self.env.user.employee_id.id)])
            for rec in department1:
                if rec:
                    dep.append(rec.id)
                    print(dep, 'ppp', rec.name)
                else:
                    print('poooo')
        else:
            department2 = self.env['hr.department'].sudo().search([])
            for j in department2:
                dep.append(j.id)
        domain = [('id', 'in', dep)]
        return {'domain': {'department_id': domain}}

    department_id = fields.Many2one('hr.department', string='Department', domain=_on_change_job_position)
    remarks = fields.Text(string='Remarks')

    @api.depends('date')
    def _on_change_date(self):
        for rec in self:
            if rec.date:
                rec.expected_date = rec.date + timedelta(days=15)

    def action_create_job_position(self):
        print('lll')
        self.state = 'hr_approval'
        ss = self.env['logic.recruitment.form'].search([])

        users = ss.env.ref('logic_recruitment.group_recruitment_hr_manager').users
        for j in users:
            self.activity_schedule('logic_recruitment.recruitment_activity_for_hr_manager', user_id=j.id,
                                   note=f'Job recruitment record has been created {self.create_uid.name}. Your decision to approve or reject is awaited')

    active = fields.Boolean(string='Active', default=True)

    def action_hr_approval(self):
        job = self.env['hr.job'].sudo().create({
            'name': self.job_position,
            'company_id': self.company_id.id,
            'department_id': self.department_id.id,
            'no_of_recruitment': self.no_of_recruitment,
            'logic_recruitment_id': self.id,
            'can_publish': True,
            'is_published': True

        })
        self.sudo().write({'state': 'done'})
        activity_id = self.env['mail.activity'].search(
            [('res_id', '=', self.id), ('user_id', '=', self.env.user.id), (
                'activity_type_id', '=', self.env.ref('logic_recruitment.recruitment_activity_for_hr_manager').id)])
        activity_id.action_feedback(feedback=f'approved.')
        return {
            'effect': {
                'fadeout': 'slow',
                'message': 'Job recruitment created.',
                'type': 'rainbow_man',
            }
        }

    def action_archive(self):
        self.write({'active': False})

    def action_unarchive(self):
        self.write({'active': True})

    def action_rejected_recruitment(self):
        activity_id = self.env['mail.activity'].search(
            [('res_id', '=', self.id), ('user_id', '=', self.env.user.id), (
                'activity_type_id', '=', self.env.ref('logic_recruitment.recruitment_activity_for_hr_manager').id)])
        activity_id.action_feedback(feedback=f'rejected.')
        self.sudo().write({'state': 'rejected'})

    def get_current_recruitment_status(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Recruitment',
            'view_mode': 'tree,form',
            'res_model': 'hr.job',
            'domain': [('logic_recruitment_id', '=', self.id)],
            'context': "{'create': False}"
        }

    recruitment_smart_count = fields.Integer(compute='compute_count')

    def compute_count(self):
        for record in self:
            record.recruitment_smart_count = self.env['hr.job'].search_count(
                [('logic_recruitment_id', '=', self.id)])


class JobRecruitment(models.Model):
    _inherit = 'hr.job'

    logic_recruitment_id = fields.Many2one('logic.recruitment.form', string='Recruitment')
