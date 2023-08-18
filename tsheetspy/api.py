import requests
import os
import json
import functools
import datetime

API_BASE = 'https://rest.tsheets.com/api/v1'

def _now_str():
    return datetime.datetime.now().astimezone().replace(microsecond=0).isoformat()

def _today_str():
    return datetime.date.today().strftime('%Y-%m-%d')

def _1wkago_str():
    return (datetime.date.today() - datetime.timedelta(weeks = 1)).strftime('%Y-%m-%d')

class TSheets:
    def __init__(self, token = None):
        if token is None:
            token = open(os.path.expanduser("~/.config/tsheets/token"), "r").read().strip()
        self.token = token

    def _request(self, endpoint, method = "GET", payload = None, params = None):
        headers = { 'Authorization': f"Bearer {self.token}" }
        if payload is None:
            payload = ""
        else:
            payload = json.dumps(payload)
            headers['Content-Type'] = 'application/json'
    
        response = requests.request(method, f"{API_BASE}/{endpoint}",
                                    data=payload, params=params,
                                    headers=headers)
        if response.status_code != 200:
            raise RuntimeError(f"request to {endpoint} failed with status {response.status_code}")
        return response.json()

    @functools.cache
    def user(self):
        return self._request("current_user")['results']['users'].popitem()[1]

    @functools.cache
    def customfields_raw(self):
        return self._request("customfields")['results']['customfields']

    @functools.cache
    def customfielditems_raw(self, field):
        return self._request("customfielditems", params = {'customfield_id': str(field)})['results']['customfielditems']

    def customfields(self):
        raw = self.customfields_raw()
        def mkfield(id):
            f = raw[id]
            ritems = self.customfielditems_raw(id)
            return {
                'id': int(id),
                'name': f['name'],
                'required': f['required'],
                'items': { int(id): ritems[id]['name'] for id in ritems if ritems[id]['active'] }
            }
        return { int(id): mkfield(id) for id in raw if raw[id]['active'] }

    @functools.cache
    def jobcodes_raw(self):
        jobcodes = {}
        page = 1
        while True:
            rv = self._request("jobcodes", params = { 'page': page })
            jobcodes.update(rv['results']['jobcodes'])
            page += 1
            if not rv['more']:
                break
        return jobcodes

    def jobcodes(self):
        j = self.jobcodes_raw()
        ps = {}
        def mkproj(id):
            proj = j[str(id)]
            name = proj['name']
            if 'parent_id' in proj and proj['parent_id'] != 0:
                name = f"{mkproj(proj['parent_id'])['name']} : {proj['name']}"
            return { 'id': int(id), 'name': name,
                'customfielditems': { int(id): vals for id,vals in proj['filtered_customfielditems'].items() } if proj['filtered_customfielditems'] != '' else {}
            }
        
        return { int(id): mkproj(id) for id in j }

    @functools.cache
    def jobcodes_avail(self):
        j = self.jobcodes()
        asns = self._request("jobcode_assignments", params = { "user_ids": str(self.user()['id']) })
        return { asn['jobcode_id']: j[asn['jobcode_id']] for id,asn in asns['results']['jobcode_assignments'].items() if asn['active'] and asn['jobcode_id'] in j }

    def timesheet_cur(self):
        rv = self._request("timesheets", params = {"on_the_clock": "yes", "start_date": _1wkago_str(), "user_ids": self.user()['id'] })['results']['timesheets']
        if len(rv) == 0:
            return None
        if len(rv) != 1:
            raise ValueError("too many timesheets currently")
        return Timesheet(api = self, json = list(rv.items())[0][1])

    def timesheet_last(self):
        rv = self._request("timesheets", params = {"on_the_clock": "both", "start_date": _1wkago_str(), "user_ids": self.user()['id'] })['results']['timesheets']
        if len(rv) == 0:
            return None
        return Timesheet(api = self, json = list(rv.items())[len(rv)-1][1])
    
    def timesheet_from_yaml(self, yaml):
        return Timesheet(api = self, yaml = yaml)

    def totals(self):
        total1 = self._request("reports/current_totals", method = 'POST', payload = { "data": {"on_the_clock": "both", "user_ids": self.user()['id'] }})['results']['current_totals'].popitem()[1]
        # total1['shift_seconds'], ['day_seconds']
        wkstart = datetime.date.today() - datetime.timedelta(days = datetime.date.today().weekday() + 1)
        wkend = wkstart + datetime.timedelta(days = 8)
        total2 = self._request("reports/payroll", method = 'POST', payload = { "data": { "start_date": wkstart.isoformat(), "end_date": wkend.isoformat(), 'include_zero_time': 'yes', "user_ids": self.user()['id'] }})['results']['payroll_report'].popitem()[1]
        return { 'item': datetime.timedelta(seconds = total1['shift_seconds']),
                 'day': datetime.timedelta(seconds = total1['day_seconds']),
                 'week': datetime.timedelta(seconds = total2['total_work_seconds']) + datetime.timedelta(seconds = total1['shift_seconds']) }

class Timesheet:
    def __init__(self, api, json = None, yaml = None):
        self.api = api
        if json:
            self.id = json['id']
            self.user_id = json['user_id']
            self.jobcode_id = json['jobcode_id']
            self.notes = json['notes']
            self.customfields = json['customfields'] # note: str(id) -> stringvalue!
            self.on_the_clock = json['on_the_clock']
            self.start = datetime.datetime.fromisoformat(json['start'])
            try:
                self.end = datetime.datetime.fromisoformat(json['end'])
            except:
                self.end = None
            self.date = datetime.date.fromisoformat(json['date'])
            self.exists = True
        elif yaml:
            self.id = yaml.get('id', None)
            self.user_id = yaml.get('user_id', self.api.user()['id'])
            self.jobcode_id = yaml['jobcode']
            if yaml['jobcode'] not in self.api.jobcodes_avail():
                # maybe it's a textual version?
                for code,val in self.api.jobcodes_avail().items():
                    if yaml['jobcode'] == val['name']:
                        self.jobcode_id = code
            self.notes = yaml.get('notes', '')
            self.customfields = {}
            for k,v in yaml.get('fields',{}).items():
                if k not in self.api.customfields():
                    for id,val in self.api.customfields().items():
                        if val['name'] == k:
                            k = str(id)
                self.customfields[k] = v
            self.start = datetime.datetime.now().astimezone().replace(microsecond=0)
            if 'start' in yaml:
                self.start = datetime.datetime.fromisoformat(yaml['start'])
            self.end = None
            if 'end' in yaml:
                self.end = datetime.datetime.fromisoformat(yaml['end'])
            self.exists = self.id is not None
            self.on_the_clock = self.id is not None
    
    def clock_in(self):
        if self.exists:
            raise ValueError("this timesheet already exists")
        rv = self.api._request("timesheets", method = 'POST',
            payload = { "data": [ {
                'user_id': int(self.user_id),
                'type': 'regular',
                'start': self.start.isoformat(),
                'end': self.end.isoformat() if self.end else '',
                'jobcode_id': str(self.jobcode_id),
                'notes': self.notes,
                'customfields': self.customfields
            } ] })
        self.id = rv['results']['timesheets']['1']['id']
        self.exists = True
        self.on_the_clock = True
    
    def clock_out(self):
        if not self.exists or not self.on_the_clock:
            raise ValueError('cannot clock out of timesheet that we have not clocked into')
        self.end = datetime.datetime.now().astimezone().replace(microsecond=0)
        rv = self.api._request("timesheets", method = 'PUT',
            payload = { "data": [{
                'id': self.id,
                'end': self.end.isoformat()
            }]})
        self.on_the_clock = False
    
    def delete(self):
        self.api._request("timesheets", method = 'DELETE', params = {"ids": str(self.id)})
        self.exists = False
        self.id = None
    
    def to_yaml(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'jobcode': self.api.jobcodes_avail()[self.jobcode_id]['name'],
            'start': self.start.isoformat(),
            'end': self.end.isoformat() if self.end else None,
            'fields': { self.api.customfields()[int(k)]['name']: v for k,v in self.customfields.items()},
            'notes': self.notes,
        }
        # yaml.dump(to_yaml(), sort_keys = False)
    
    def update(self, yaml = None):
        if 'jobcode' in yaml:
            self.jobcode_id = yaml['jobcode']
            if yaml['jobcode'] not in self.api.jobcodes_avail():
                # maybe it's a textual version?
                for code,val in self.api.jobcodes_avail().items():
                    if yaml['jobcode'] == val['name']:
                        self.jobcode_id = code
        self.notes = yaml.get('notes', self.notes)
        if 'fields' in yaml:
            self.customfields = {}
            for k,v in yaml['fields'].items():
                if k not in self.api.customfields():
                    for id,val in self.api.customfields().items():
                        if val['name'] == k:
                            k = str(id)
                self.customfields[k] = v
        if 'start' in yaml:
            self.start = datetime.datetime.fromisoformat(yaml['start'])
        if 'end' in yaml:
            try:
                self.end = datetime.datetime.fromisoformat(yaml['end'])
            except:
                self.end = None
        
        self.api._request("timesheets", method = 'PUT',
            payload = { "data": [{
                'id': self.id,
                'start': self.start.isoformat(),
                'end': self.end.isoformat() if self.end else '',
                'jobcode_id': str(self.jobcode_id),
                'notes': self.notes,
                'customfields': self.customfields,
            }]})
        
        if self.end:
            self.on_the_clock = False
