# coding: utf-8
import logging
from odoo import tools
import csv

_logger = logging.getLogger(__name__)

def post_init_hook(env):
    mx_country = env["res.country"].search([("code", "=", "MX")])
    # Load cities
    res_city_vals_list = []
    with tools.file_open("solt_l10n_mx_partner_address/data/res.city.csv") as csv_file:
        for row in csv.DictReader(csv_file, delimiter='|', fieldnames=['l10n_mx_code', 'name', 'state_xml_id']):
            state = env.ref('base.%s' % row['state_xml_id'], raise_if_not_found=False)
            res_city_vals_list.append({
                'l10n_mx_code': row['l10n_mx_code'],
                'name': row['name'],
                'state_id': state.id if state else False,
                'country_id': mx_country.id,
            })
    city_obj = env['res.city']
    existing_codes = set(city_obj.search([('l10n_mx_code', 'in', [v['l10n_mx_code'] for v in res_city_vals_list])]).mapped('l10n_mx_code'))
    res_city_vals_list = [city for city in res_city_vals_list if city['l10n_mx_code'] not in existing_codes]
    if res_city_vals_list:
        cities = city_obj.create(res_city_vals_list)
        env.cr.execute('''
           INSERT INTO ir_model_data (name, res_id, module, model, noupdate)
               SELECT
                    'res_city_mx_' || lower(res_country_state.code) || '_' || res_city.l10n_mx_code,
                    res_city.id,
                    'solt_l10n_mx_partner_address',
                    'res.city',
                    TRUE
               FROM res_city
               JOIN res_country_state ON res_country_state.id = res_city.state_id
               WHERE res_city.id IN %s
        ''', [tuple(cities.ids)])

    # ==== Load lres.locality ====
    locality_obj = env['res.locality']
    if not locality_obj.search_count([]):
        res_locality_vals_list = []
        with tools.file_open("solt_l10n_mx_partner_address/data/res.locality.csv") as csv_file:
            for row in csv.DictReader(csv_file, delimiter='|', fieldnames=['code', 'name', 'state_xml_id']):
                state = env.ref('base.%s' % row['state_xml_id'], raise_if_not_found=False)
                res_locality_vals_list.append({
                    'code': row['code'],
                    'name': row['name'],
                    'state_id': state.id if state else False,
                    'country_id': mx_country.id,
                })

        localities = locality_obj.create(res_locality_vals_list)

        if localities:
            env.cr.execute('''
               INSERT INTO ir_model_data (name, res_id, module, model, noupdate)
                   SELECT 
                        'res_locality_mx_' || lower(res_country_state.code) || '_' || res_locality.code,
                        res_locality.id,
                        'solt_l10n_mx_partner_address',
                        'res.locality',
                        TRUE
                   FROM res_locality
                   JOIN res_country_state ON res_country_state.id = res_locality.state_id
                   WHERE res_locality.id IN %s
            ''', [tuple(localities.ids)])

    # ==== Load res.city.district ====
    district_obj = env['res.city.district']
    if not district_obj.search_count([]):
        district_vals_list = []
        with tools.file_open("solt_l10n_mx_partner_address/data/res.city.district.csv") as csv_file:
            for row in csv.DictReader(csv_file):
                district_vals_list.append({
                    'name': row['name'],
                    'zip_code': row['zipcode'],
                    'city_id': env.ref(row['city_id'], raise_if_not_found=False).id,
                })

        districties = district_obj.create(district_vals_list)
        if districties:
            env.cr.execute('''
INSERT INTO ir_model_data (name, res_id, module, model, noupdate)
   SELECT 
        'colony_' || lower(replace(res_city_district.name, ' ', '_')) || '_' || res_city_district.zip_code || '_' || res_city_district.id,
         res_city_district.id,
        'solt_l10n_mx_partner_address',
        'res.city.district',
        TRUE
   FROM res_city_district
   JOIN res_city ON res_city.id = res_city_district.city_id
   WHERE res_city_district.id IN %s
                    ''', [tuple(districties.ids)])