""" Handlers for sequencing project information.
"""
import json
import string

import tornado.web
import dateutil.parser
import datetime

from collections import OrderedDict
from status.util import dthandler, SafeHandler

class ProjectViewPresetsHandler(SafeHandler):
    """Handler to GET and POST/PUT personalized and default set of presets in

    project view.
    """
    def get(self):
        """Get preset choices of columns from StatusDB

        It will return a JSON with two lists of presets, the default ones and the user defined
        presets.
        """
        self.set_header("Content-type", "application/json")
        presets = {
            "default": self.application.genstat_defaults.get('pv_presets'),
            "user": {}
        }
        #Get user presets
        user_id = ''
        user = self.get_secure_cookie('email')
        for u in self.application.gs_users_db.view('authorized/users'):
            if u.get('key') == user:
                user_id = u.get('value')
                break
        presets['user'] = self.application.gs_users_db.get(user_id).get('pv_presets', {})
        self.write(json.dumps(presets))


class ProjectsBaseDataHandler(SafeHandler):
    def keys_to_names(self, columns):
        d = {}
        for column_category, column_tuples in columns.iteritems():
            for key, value in column_tuples.iteritems():
                d[value] = key
        return d

    def project_summary_data(self, row):
        # the details key gives values containing multiple udfs on project level
        # and project_summary key gives 'temporary' udfs that will move to 'details'.
        # Include these as normal key:value pairs
        if 'project_summary' in row.value:
            for summary_key, summary_value in row.value['project_summary'].iteritems():
                row.value[summary_key] = summary_value
            row.value.pop("project_summary", None)

        # If key is in both project_summary and details, details has precedence
        if 'details' in row.value:
            for detail_key, detail_value in row.value['details'].iteritems():
                row.value[detail_key] = detail_value
            row.value.pop("details", None)

        if row.key[0] == 'open' and 'queued' in row.value:
            #Add days in production field
            now = datetime.datetime.now()
            queued = row.value['queued']
            diff = now - dateutil.parser.parse(queued)
            row.value['days_in_production'] = diff.days
        return row

    def list_projects(self, all_projects=True):
        projects = OrderedDict()

        summary_view = self.application.projects_db.view("project/summary", descending=True)
        if not all_projects:
            summary_view = summary_view[["open",'Z']:["open",'']]

        for row in summary_view:
            row = self.project_summary_data(row)
            projects[row.key[1]] = row.value

        # Include dates for each project:
        for row in self.application.projects_db.view("project/summary_dates", descending=True, group_level=1):
            if row.key[0] in projects:
                for date_type, date in row.value.iteritems():
                    projects[row.key[0]][date_type] = date

        return projects

    def list_project_fields(self, undefined=False, project_list=None, all_projects=True):
        # If undefined=True is given, only return fields not in columns defined
        # in constants in this module
        columns = self.application.genstat_defaults.get('pv_columns')
        if project_list is None:
            project_list = self.list_projects(all_projects=all_projects)
        field_items = set()
        for project_id, value in project_list.iteritems():
            for key, _ in value.iteritems():
                field_items.add(key)
        if undefined:
            for column_category, column_dict in columns.iteritems():
                field_items = field_items.difference(set(column_dict.values()))
        return field_items

def prettify_css_names(s):
    return s.replace("(","_").replace(")", "_")

class ProjectsDataHandler(ProjectsBaseDataHandler):
    """ Serves brief information for each open project in the database.

    Loaded through /api/v1/projects
    """
    def get(self):
        self.set_header("Content-type", "application/json")
        all_projects = self.get_argument("all_projects", "True")
        all_projects = (str(all_projects).lower() == "true")

        self.write(json.dumps(self.list_projects(all_projects)))


class ProjectsFieldsDataHandler(ProjectsBaseDataHandler):
    """ Serves all fields occuring in the values of the ProjectsDataHandler
    json object.

    Loaded through /api/v1/projects_fields
    """
    def get(self):
        undefined = self.get_argument("undefined", "False")
        undefined = (string.lower(undefined) == "true")
        all_projects = self.get_argument("all_projects", "True")
        all_projects = (str(all_projects).lower() == "true")
        field_items = self.list_project_fields(undefined=undefined, all_projects=all_projects)
        self.write(json.dumps(list(field_items)))

class ProjectDataHandler(ProjectsBaseDataHandler):
    """ Serves brief information of a given project.

    Loaded through /api/v1/project_summary/([^/]*)$
    """
    def get(self, project):
        self.set_header("Content-type", "application/json")
        self.write(json.dumps(self.project_info(project)))

    def project_info(self, project):
        view = self.application.projects_db.view("project/summary")["open", project]
        if not view.rows:
            view = self.application.projects_db.view("project/summary")["closed", project]
        if not len(view.rows) == 1:
            return {}

        summary_row = view.rows[0]
        summary_row = self.project_summary_data(summary_row)

        date_view = self.application.projects_db.view("project/summary_dates",
                                                      descending=True,
                                                      group_level=1)
        date_result = date_view[[project + 'ZZZZ']:[project]]
        if date_result.rows:
            for date_row in date_view.rows:
                for date_type, date in date_row.value.iteritems():
                    summary_row.value[date_type] = date
        return summary_row.value


class ProjectSamplesDataHandler(SafeHandler):
    """ Serves brief info about all samples in a given project.

    Loaded through /api/v1/projects/([^/]*)$
    """
    def sample_data(self, sample_data):
        sample_data["sample_run_metrics"] = []
        sample_data["prep_status"] = []
        sample_data["prep_finished_date"] = []
        if "library_prep" in sample_data:
            for lib_prep, content in sample_data["library_prep"].iteritems():
                if "sample_run_metrics" in content:
                    for run, id in content["sample_run_metrics"].iteritems():
                        sample_data["sample_run_metrics"].append(run)
                if "prep_status" in content:
                    if content["prep_status"] == "PASSED":
                        sample_data["prep_status"].append("P")
                    else:
                        sample_data["prep_status"].append("F")
                if "prep_finished_date" in content:
                    sample_data["prep_finished_date"].append(content["prep_finished_date"])

        if "details" in sample_data:
            for detail_key, detail_value in sample_data["details"].iteritems():
                sample_data[detail_key] = detail_value
        return sample_data

    def list_samples(self, project):
        samples = OrderedDict()
        sample_view = self.application.projects_db.view("project/samples")
        result = sample_view[project]
        samples = result.rows[0].value
        output = OrderedDict()
        for sample, sample_data in sorted(samples.iteritems(), key=lambda x: x[0]):
            sample_data = self.sample_data(sample_data)
            output[sample] = sample_data
        return output

    def get(self, project):
        self.set_header("Content-type", "application/json")
        # self.write(json.dumps(self.sample_list(project), default=dthandler))
        self.write(json.dumps(self.list_samples(project), default=dthandler))

    def sample_list(self, project):
        sample_view = self.application.projects_db.view("project/samples")
        result = sample_view[project]

        samples = result.rows[0].value
        samples = OrderedDict(sorted(samples.iteritems(), key=lambda x: x[0]))
        return samples


class ProjectSamplesHandler(SafeHandler):
    """ Serves a page which lists the samples of a given project, with some
    brief information for each sample.
    """
    def get(self, project):
        t = self.application.loader.load("project_samples.html")
        self.write(t.generate(project=project,
                              user=self.get_current_user_name(),
                              columns = self.application.genstat_defaults.get('pv_columns'),
                              prettify = prettify_css_names))


class ProjectsHandler(SafeHandler):
    """ Serves a page with all projects listed, along with some brief info.
    """
    def get(self):
        t = self.application.loader.load("projects.html")
        columns = self.application.genstat_defaults.get('pv_columns')
        self.write(t.generate(columns=columns, all_projects=True, user=self.get_current_user_name()))


class OpenProjectsHandler(SafeHandler):
    """ Serves a page with all OPEN projects listed, along with some brief info.
    """
    def get(self):
        t = self.application.loader.load("projects.html")
        columns = self.application.genstat_defaults.get('pv_columns')
        self.write(t.generate(columns=columns, all_projects=False, user=self.get_current_user_name()))



class UppmaxProjectsDataHandler(SafeHandler):
    """ Serves a list of UPPNEX projects where the storage quota have
    been logged.

    Loaded through /api/v1/uppmax_projects
    """
    def get(self):
        self.set_header("Content-type", "application/json")
        self.write(json.dumps(self.list_projects()))

    def list_projects(self):
        project_list = []
        view = self.application.uppmax_db.view("status/projects", group_level=1)
        for row in view:
            project_list.append(row.key)

        return project_list
