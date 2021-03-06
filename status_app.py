""" Main genomics-status web application.
"""
import yaml
import base64
import uuid
import collections

from couchdb import Server
from collections import OrderedDict

import tornado.httpserver
import tornado.ioloop
import tornado.web
import tornado.autoreload
from tornado import template

from status.util import *
from status.amanita import *
from status.production import *
from status.applications import *
from status.projects import *
from status.sequencing import *
from status.samples import *
from status.picea import *
from status.flowcells import *
from status.barcode_vs_expected import *
from status.reads_per_lane import *
from status.reads_vs_qv import *
from status.q30 import *
from status.quotas import *
from status.phix_err_rate import *
from status.testing import *
from status.authorization import *

from argparse import ArgumentParser

class Application(tornado.web.Application):
    def __init__(self, settings):
        handlers = [
            ("/", MainHandler),
            ("/login", LoginHandler),
            ("/logout", LogoutHandler),
            ("/unauthorized", UnAuthorizedHandler),
            ("/api/v1", DataHandler),
            ("/api/v1/applications", ApplicationsDataHandler),
            ("/api/v1/applications.png", ApplicationsPlotHandler),
            ("/api/v1/application/([^/]*)$", ApplicationDataHandler),
            ("/api/v1/expected", BarcodeVsExpectedDataHandler),
            ("/api/v1/amanita_home", AmanitaHomeDataHandler),
            ("/api/v1/amanita_home/users/", AmanitaUsersDataHandler),
            ("/api/v1/amanita_home/projects", AmanitaHomeProjectsDataHandler),
            ("/api/v1/amanita_home/projects/([^/]*)$",
                AmanitaHomeProjectDataHandler),
            ("/api/v1/amanita_home/([^/]*)$", AmanitaHomeUserDataHandler),
            ("/api/v1/amanita_box2", AmanitaBox2DataHandler),
            ("/api/v1/amanita_box2/([^/]*)$", AmanitaBox2ProjectDataHandler),
            ("/api/v1/amanita_box2/projects/",
                AmanitaBox2ProjectsDataHandler),
            ("/api/v1/delivered_monthly", DeliveredMonthlyDataHandler),
            ("/api/v1/delivered_monthly.png", DeliveredMonthlyPlotHandler),
            ("/api/v1/delivered_quarterly", DeliveredQuarterlyDataHandler),
            ("/api/v1/delivered_quarterly.png", DeliveredQuarterlyPlotHandler),
            ("/api/v1/flowcells", FlowcellsDataHandler),
            ("/api/v1/flowcell_info/([^/]*)$", FlowcellsInfoDataHandler),
            ("/api/v1/flowcell_qc/([^/]*)$", FlowcellQCHandler),
            ("/api/v1/flowcell_demultiplex/([^/]*)$",
                FlowcellDemultiplexHandler),
            ("/api/v1/flowcell_q30/([^/]*)$", FlowcellQ30Handler),
            ("/api/v1/flowcells/([^/]*)$", FlowcellDataHandler),
            ("/api/v1/instrument_cluster_density",
                InstrumentClusterDensityDataHandler),
            ("/api/v1/instrument_cluster_density.png",
                InstrumentClusterDensityPlotHandler),
            ("/api/v1/instrument_error_rates", InstrumentErrorrateDataHandler),
            ("/api/v1/instrument_error_rates.png",
                InstrumentErrorratePlotHandler),
            ("/api/v1/instrument_unmatched", InstrumentUnmatchedDataHandler),
            ("/api/v1/instrument_unmatched.png", InstrumentUnmatchedPlotHandler),
            ("/api/v1/instrument_yield", InstrumentYieldDataHandler),
            ("/api/v1/instrument_yield.png", InstrumentYieldPlotHandler),
            ("/api/v1/last_updated", UpdatedDocumentsDatahandler),
            ("/api/v1/plot/q30.png", Q30PlotHandler),
            ("/api/v1/plot/samples_per_lane.png",
                SamplesPerLanePlotHandler),
            ("/api/v1/plot/reads_per_lane.png", ReadsPerLanePlotHandler),
            ("/api/v1/plot/barcodes_vs_expected.png",
                BarcodeVsExpectedPlotHandler),
            ("/api/v1/picea_home", PiceaHomeDataHandler),
            ("/api/v1/samples_per_lane", SamplesPerLaneDataHandler),
            ("/api/v1/picea_home/users/", PiceaUsersDataHandler),
            ("/api/v1/picea_home/([^/]*)$", PiceaHomeUserDataHandler),
            ("/api/v1/produced_monthly", ProducedMonthlyDataHandler),
            ("/api/v1/produced_monthly.png", ProducedMonthlyPlotHandler),
            ("/api/v1/produced_quarterly", ProducedQuarterlyDataHandler),
            ("/api/v1/produced_quarterly.png", ProducedQuarterlyPlotHandler),
            ("/api/v1/projects", ProjectsDataHandler),
            ("/api/v1/projects/([^/]*)$", ProjectSamplesDataHandler),
            ("/api/v1/projects_fields", ProjectsFieldsDataHandler),
            ("/api/v1/project_summary/([^/]*)$", ProjectDataHandler),
            ("/api/v1/project_view_presets", ProjectViewPresetsHandler),
            ("/api/v1/qc/([^/]*)$", SampleQCDataHandler),
            ("/api/v1/quotas/(\w+)?", QuotaDataHandler),
            ("/api/v1/reads_vs_quality", ReadsVsQDataHandler),
            ("/api/v1/sample_info/([^/]*)$", SampleInfoDataHandler),
            ("/api/v1/sample_readcount/(\w+)?", SampleReadCountDataHandler),
            ("/api/v1/sample_run_counts/(\w+)?",
                SampleRunReadCountDataHandler),
            ("/api/v1/sample_alignment/([^/]*)$",
                SampleQCAlignmentDataHandler),
            ("/api/v1/sample_coverage/([^/]*)$", SampleQCCoverageDataHandler),
            ("/api/v1/sample_summary/([^/]*)$", SampleQCSummaryDataHandler),
            ("/api/v1/sample_insert_sizes/([^/]*)$",
                SampleQCInsertSizesDataHandler),
            ("/api/v1/samples/start/([^/]*)$", PagedQCDataHandler),
            ("/api/v1/samples/([^/]*)$", SampleRunDataHandler),
            ("/api/v1/samples_applications", SamplesApplicationsDataHandler),
            ("/api/v1/samples_applications.png",
                SamplesApplicationsPlotHandler),
            ("/api/v1/test/(\w+)?", TestDataHandler),
            ("/api/v1/uppmax_projects", UppmaxProjectsDataHandler),
            ("/api/v1/phix_err_rate", PhixErrorRateDataHandler),
            ("/amanita", AmanitaHandler),
            ("/applications", ApplicationsHandler),
            ("/application/([^/]*)$", ApplicationHandler),
            ("/barcode_vs_expected", ExpectedHandler),
            ("/flowcells", FlowcellsHandler),
            ("/flowcells/([^/]*)$", FlowcellHandler),
            ("/q30", Q30Handler),
            ("/picea", PiceaHandler),
            ("/qc/([^/]*)$", SampleQCSummaryHandler),
            ("/quotas", QuotasHandler),
            ("/quotas/(\w+)?", QuotaHandler),
            ("/phix_err_rate", PhixErrorRateHandler),
            ("/production", ProductionHandler),
            ("/all_projects", ProjectsHandler),
            ("/open_projects", OpenProjectsHandler),
            ("/projects/([^/]*)$", ProjectSamplesHandler),
            ("/reads_vs_qv", ReadsVsQvhandler),
            ("/reads_per_lane", ReadsPerLaneHandler),
            ("/samples_per_lane", SamplesPerLaneHandler),
            ("/samples/([^/]*)$", SampleRunHandler),
            ("/sequencing", SequencingStatsHandler)
        ]

        self.declared_handlers = handlers

        # Load templates
        self.loader = template.Loader("design")

        # Global connection to the database
        couch = Server(settings.get("couch_server", None))
        if couch:
            self.illumina_db = couch["illumina_logs"]
            self.uppmax_db = couch["uppmax"]
            self.samples_db = couch["samples"]
            self.projects_db = couch["projects"]
            self.flowcells_db = couch["flowcells"]
            self.amanita_db = couch["amanita"]
            self.picea_db = couch["picea"]
            self.gs_users_db = couch["gs_users"]

        #Load columns and presets from genstat-defaults user in StatusDB
        genstat_id = ''
        for u in self.gs_users_db.view('authorized/users'):
            if u.get('key') == 'genstat-defaults':
                genstat_id = u.get('value')

        #It's important to check that this user exists!
        if not genstat_id:
            raise RuntimeError("genstat-defaults user not found on {}, please " \
                               "make sure that the user is abailable with the " \
                               "corresponding defaults information.".format(settings.get("couch_server", None)))

        # We need to get this database as OrderedDict, so the pv_columns doesn't
        # mess up
        user = settings.get("username", None)
        password = settings.get("password", None)
        headers = {"Accept": "application/json",
                   "Authorization": "Basic " + "{}:{}".format(user, password).encode('base64')[:-1]}
        decoder = json.JSONDecoder(object_pairs_hook=collections.OrderedDict)
        user_url = "{}/gs_users/{}".format(settings.get("couch_server"), genstat_id)
        json_user = requests.get(user_url, headers=headers).content.rstrip()

        self.genstat_defaults = decoder.decode(json_user)

        # Load private instrument listing
        self.instrument_list = settings.get("instruments")

        # If settings states  mode, no authentication is used
        self.test_mode = settings["Testing mode"]

        # google oauth key
        self.oauth_key = settings["google_oauth"]["key"]

        # Load password seed
        self.password_seed = settings.get("password_seed")

        # Setup the Tornado Application
        cookie_secret = base64.b64encode(uuid.uuid4().bytes + uuid.uuid4().bytes)
        settings = {"debug": True,
                    "static_path": "static",
                    "cookie_secret": cookie_secret,
                    "login_url": "/login",
                    "google_oauth": {
                        "key": self.oauth_key,
                        "secret": settings["google_oauth"]["secret"]},
                    "contact_person": settings['contact_person'],
                    "redirect_uri": settings['redirect_uri']
                     }

        tornado.autoreload.watch("design/amanita.html")
        tornado.autoreload.watch("design/application.html")
        tornado.autoreload.watch("design/applications.html")
        tornado.autoreload.watch("design/barcodes.html")
        tornado.autoreload.watch("design/base.html")
        tornado.autoreload.watch("design/expected.html")
        tornado.autoreload.watch("design/flowcell_samples.html")
        tornado.autoreload.watch("design/flowcells.html")
        tornado.autoreload.watch("design/index.html")
        tornado.autoreload.watch("design/phix_err_rate.html")
        tornado.autoreload.watch("design/production.html")
        tornado.autoreload.watch("design/projects.html")
        tornado.autoreload.watch("design/project_samples.html")
        tornado.autoreload.watch("design/q30.html")
        tornado.autoreload.watch("design/quota_grid.html")
        tornado.autoreload.watch("design/quota.html")
        tornado.autoreload.watch("design/reads_per_lane.html")
        tornado.autoreload.watch("design/reads_vs_qv.html")
        tornado.autoreload.watch("design/sample_run_qc.html")
        tornado.autoreload.watch("design/sample_runs.html")
        tornado.autoreload.watch("design/samples.html")
        tornado.autoreload.watch("design/sequencing_stats.html")
        tornado.autoreload.watch("design/login.html")

        tornado.web.Application.__init__(self, handlers, **settings)


def main(args):
    """ Initialte server and start IOLoop.
    """
    with open("settings.yaml") as settings_file:
        server_settings = yaml.load(settings_file)

    server_settings["Testing mode"] = args.testing_mode

    # Instantiate Application
    application = Application(server_settings)

    # Load ssl certificate and key files
    ssl_cert = server_settings.get("ssl_cert", None)
    ssl_key = server_settings.get("ssl_key", None)

    if ssl_cert and ssl_key:
        ssl_options = {"certfile": ssl_cert,
                       "keyfile": ssl_key}
    else:
        ssl_options = None

    # Start HTTP Server
    http_server = tornado.httpserver.HTTPServer(application,
                                                ssl_options = ssl_options)

    http_server.listen(server_settings.get("port", 8888))

    # Get a handle to the instance of IOLoop
    ioloop = tornado.ioloop.IOLoop.instance()

    # Start the IOLoop
    ioloop.start()


if __name__ == '__main__':
    parser = ArgumentParser()
    parser.add_argument('--testing_mode', default=False, action='store_true',
                        help=("WARNING, this option disables "
                              "all security measures, use only "
                              "for testing purposes"))
    args = parser.parse_args()
    main(args)
