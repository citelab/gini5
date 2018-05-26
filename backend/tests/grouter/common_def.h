
#include "packetcore.h"
#include "classifier.h"
#include "filter.h"
#include "openflow_flowtable.h"
#include "openflow_ctrl_iface.h"

// Global objects defined in grouter.c, which is not included in tests, as it contains main.

router_config rconfig = {
	.router_name="Test", .gini_home=NULL, .cli_flag=0, .config_file=NULL,
	.config_dir=NULL, .openflow=1000, .ghandler=0, .clihandler= 0, .scheduler=0, 
	.worker=0, .openflow_worker=0, .openflow_controller_iface=0,
	.schedcycle=10000
};
pktcore_t *pcore;
classlist_t *classifier;
filtertab_t *filter;
