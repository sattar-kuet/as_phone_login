# -*- coding: utf-8 -*-

import odoo
from odoo import http, _
from odoo.http import request
from odoo.addons.auth_signup.controllers.main import AuthSignupHome
from odoo.addons.auth_signup.models.res_users import SignupError
from odoo.addons.web.controllers.main import ensure_db, Home, SIGN_UP_REQUEST_PARAMS
from odoo.exceptions import UserError

class AuthSignupHomeExtend(AuthSignupHome):

    def _prepare_signup_values(self, qcontext):
            res = super(AuthSignupHomeExtend, self)._prepare_signup_values(qcontext)
            merchant_group = request.env['res.groups'].sudo().search([
                ('name', '=', 'Courier Merchant')
            ])
            res.update({
                'phone':qcontext.get("phone",""),
                'sel_groups_1_9_10': 1,
                'in_group_'+str(merchant_group.id): True
            })
            return res

    def get_auth_signup_qcontext(self):
        res = super(AuthSignupHomeExtend, self).get_auth_signup_qcontext()
        merchant_group = request.env['res.groups'].sudo().search([
            ('name', '=', 'Courier Merchant')
        ])
        res.update({
            'phone': request.params.get('phone',''),
            'sel_groups_1_9_10': 1,
            'in_group_' + str(merchant_group.id): True
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
                partner_obj = request.env['res.partner'].sudo().search([('phone','=',request.params['phone'])])
                if len(partner_obj):
                    login = partner_obj.user_ids[0].login
                else:
                    login = request.env['res.users'].sudo().search([('login', '=', request.params['phone'])]).login

                if login:
                    uid = request.session.authenticate(request.session.db, login, request.params['password'])
                    request.params['login_success'] = True
                    if redirect != None:
                        if len(redirect.strip()) == 0:
                            url = self._redirect_loggedin_user()
                            return request.redirect(url)
                    return request.redirect(self._login_redirect(uid, redirect=redirect))
                else:
                    values['error'] = _("Wrong Email OR Phone OR password")
            except odoo.exceptions.AccessDenied as e:
                request.uid = old_uid
                if e.args == odoo.exceptions.AccessDenied().args:
                    values['error'] = _("Wrong Phone/password")
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
                error = _("You do not have access to this database or your invitation has expired. Please ask for an invitation and be sure to follow the link in your invitation email.")
            else:
                error = None

            response.qcontext['providers'] = providers
            if error:
                response.qcontext['error'] = error
        return response

    def _redirect_loggedin_user(self):
        action_pickup_point_bank_id = request.env.ref('smart_courier.action_add_pickup_point_bank_merchant_wizard').id
        action_bank_id = request.env.ref('smart_courier.action_merchant_bank').id
        action_dashboard_id = request.env.ref('smart_courier.action_dashboard').id
        url = f'/web#action={action_dashboard_id}'
        if request.env.user.has_group('smart_courier.group_courier_merchant'):
            if request.env['courier.merchant.pickup.points'].is_merchant_pickup_point_missing():
                url = f'/web#action={action_pickup_point_bank_id}&model=courier.merchant.pickup.point.bank.wizard&view_type=form'
            elif request.env['courier.merchant.banks'].is_merchant_bank_missing():
                url = f'/web#action={action_bank_id}&model=courier.merchant.banks&view_type=form'
        return url

    def _signup_with_values(self, token, values):
        if 'phone' in values.keys():
            phone_number = request.env['res.users'].sudo().search([('phone','=',values['phone'])])
            if len(phone_number):
                raise UserError(_('Another user is already registered using this phone number.'))
            else:
                db, login, password = request.env['res.users'].sudo().signup(values, token)
                request.env.cr.commit()
                uid = request.session.authenticate(db, login, password)
                if not uid:
                    raise SignupError(_('Authentication Failed.'))
        else:
            raise SignupError(_('Authentication Failed.'))
