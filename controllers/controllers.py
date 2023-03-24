# -*- coding: utf-8 -*-

import odoo
from odoo import http, _
from odoo.http import request
from odoo.addons.auth_signup.controllers.main import AuthSignupHome
from odoo.addons.auth_signup.models.res_users import SignupError
from odoo.addons.web.controllers.main import ensure_db, Home, SIGN_UP_REQUEST_PARAMS
from odoo.exceptions import UserError

"""
Arif's comment:
------------------------------
There are some settings are needed to be changed from Settings menu of the application.

As Admin after logging in go to,

1. Settings > Customer Account > Default Access rights >>

2. In the `Default Access rights` window (If it is 'archived' then 'unarchieve' it from top action menu)
 => Access Rights > Allowed Companies > Select all the companies' where a merchant can be added from signup form. 

Caution: Only in selected companies a merchant can be added from signup form. 
Otherwise it will 'Could not create a new account.'
"""


class AuthSignupHomeExtend(AuthSignupHome):
    def _prepare_signup_values(self, qcontext):
        res = super(AuthSignupHomeExtend, self)._prepare_signup_values(qcontext)
        rider_group = request.env['res.groups'].sudo().search([
            ('name', '=', 'Courier Rider')
        ])
        admin_group = request.env['res.groups'].sudo().search([
            ('name', '=', 'Company Owner')
        ])
        merchant_group = request.env['res.groups'].sudo().search([
            ('name', '=', 'Courier Merchant')
        ])

        res.update({
            # Arif Added this code
            # ---------------------------------------------------------------
            'company_name': qcontext.get("company_name", ""),
            # ---------------------------------------------------------------
            'phone': qcontext.get("phone", ""),
            'sel_groups_1_9_10': 1
        })
        return res

    def get_auth_signup_qcontext(self):
        res = super(AuthSignupHomeExtend, self).get_auth_signup_qcontext()
        rider_group = request.env['res.groups'].sudo().search([
            ('name', '=', 'Courier Rider')
        ])
        admin_group = request.env['res.groups'].sudo().search([
            ('name', '=', 'Company Owner')
        ])
        merchant_group = request.env['res.groups'].sudo().search([
            ('name', '=', 'Courier Merchant')
        ])
        res.update({
            # Arif added this code
            # -----------------------------------------------------
            'company_name': request.params.get('company_name', ''),
            # -----------------------------------------------------
            'phone': request.params.get('phone', ''),
            'sel_groups_1_9_10': 1
        })
        return res


class HomeExtend(Home):
    @http.route()
    def web_login(self, redirect=None, **kw):
        ensure_db()
        if request.httprequest.method == 'GET' and request.session.uid and request.params.get('redirect'):
            # Redirect if already logged in and redirect param is present
            return request.redirect(request.params.get('redirect'))
        providers = self.list_providers()

        request.params['login_success'] = False
        if request.httprequest.method == 'GET' and redirect and request.session.uid:
            return request.redirect(redirect)

        if not request.uid:
            request.uid = odoo.SUPERUSER_ID

        values = {k: v for k, v in request.params.items() if k in SIGN_UP_REQUEST_PARAMS}
        try:
            values['databases'] = http.db_list()
        except odoo.exceptions.AccessDenied:
            values['databases'] = None

        if request.httprequest.method == 'POST':
            old_uid = request.uid
            try:
                login = request.params['phone']
                user = request.env['res.users'].sudo().search([('phone', '=', request.params['phone'])])
                if user:
                    login = user.login

                uid = request.session.authenticate(request.session.db, login, request.params['password'])
                request.params['login_success'] = True
                if redirect != None:
                    if len(redirect.strip()) == 0:
                        url = self._redirect_loggedin_user()
                        return request.redirect(url)
                return request.redirect(self._login_redirect(uid, redirect=redirect))
            except odoo.exceptions.AccessDenied as e:
                request.uid = old_uid
                if e.args == odoo.exceptions.AccessDenied().args:
                    values['error'] = _("Wrong Email OR Phone OR password")
                else:
                    values['SELF_READABLE_FIELDS'] = e.args[0]
        else:
            if 'error' in request.params and request.params.get('error') == 'access':
                values['error'] = _('Only employees can access this database. Please contact the administrator.')

        if 'login' not in values and request.session.get('auth_login'):
            values['login'] = request.session.get('auth_login')

        if not odoo.tools.config['list_db']:
            values['disable_database_manager'] = True

        response = request.render('web.login', values)
        response.headers['X-Frame-Options'] = 'DENY'
        response.qcontext.update(self.get_auth_signup_config())
        if response.is_qweb:
            error = request.params.get('oauth_error')
            if error == '1':
                error = _("Sign up is not allowed on this database.")
            elif error == '2':
                error = _("Access Denied")
            elif error == '3':
                error = _(
                    "You do not have access to this database or your invitation has expired. Please ask for an invitation and be sure to follow the link in your invitation email.")
            else:
                error = None

            response.qcontext['providers'] = providers
            if error:
                response.qcontext['error'] = error
        return response

    def _redirect_loggedin_user(self):
        action_pickup_point_bank_id = request.env.ref('smart_courier.action_add_pickup_point_bank_merchant_wizard').id
        action_bank_id = request.env.ref('smart_courier.action_merchant_bank').id
        action_dashboard_id = request.env.ref('odoo_dynamic_dashboard.action_dynamic_dashboard').id
        url = f'/web#action={action_dashboard_id}'
        if request.env.user.has_group('smart_courier.group_courier_merchant'):
            if request.env['courier.merchant.pickup.points'].is_merchant_pickup_point_missing():
                url = f'/web#action={action_pickup_point_bank_id}&model=courier.merchant.pickup.point.bank.wizard&view_type=form'
            elif request.env['courier.merchant.banks'].is_merchant_bank_missing():
                url = f'/web#action={action_bank_id}&model=courier.merchant.banks&view_type=form'
        return url

    def _signup_with_values(self, token, values):

        if 'phone' in values.keys():
            phone_number = request.env['res.users'].sudo().search([('phone', '=', values['phone'])])
            if len(phone_number):
                raise UserError(_('Another user is already registered using this phone number.'))
            else:
                db, login, password = request.env['res.users'].sudo().signup(values, token)
                # Arif added this code
                # -----------------------------------------------------
                # Arif added this code
                # -----------------------------------------------------
                # raising error if this company already exists
                if 'company_name' in values.keys():
                    company_name = request.env['res.company'].sudo().search([('name', '=', values['company_name'])])
                    if len(company_name):
                        raise UserError(_('Company is already exists.'))
                    else:
                        # --------------------------------------------------
                        # creating a partner
                        partner_obj = request.env['res.partner'].sudo().create({
                            'name': values['company_name'],
                            'company_type': 'company'
                        })
                        # finding the currency
                        currency_obj = request.env['res.currency'].sudo().search([
                            ('name', '=', 'BDT'),
                        ], limit=1)
                        # --------------------------------------------------
                        # creating company if company does not exist
                        company_obj = request.env['res.company'].sudo().create({
                            'name': values['company_name'],
                            'partner_id': partner_obj.id if partner_obj else 1,
                            'currency_id': currency_obj.id if currency_obj else 1
                        })
                # -----------------------------------------------------
                # assigning the company to the user
                user_obj = request.env['res.users'].sudo().search([('login', '=', login)], limit=1)
                for user in user_obj:
                    user.company_ids = [(4, company_obj.id)]
                    user.company_id = company_obj.id
                # -----------------------------------------------------
                request.env.cr.commit()
                uid = request.session.authenticate(db, login, password)
                if not uid:
                    raise SignupError(_('Authentication Failed.'))
        else:
            raise SignupError(_('Authentication Failed.'))
