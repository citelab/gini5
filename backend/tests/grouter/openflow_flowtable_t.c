#include "openflow_flowtable.h"
#include "mut.h"
#include <stdint.h>


#include "common_def.h"

extern void openflow_flowtable_set_defaults(void);
extern uint8_t openflow_flowtable_ip_compare(uint32_t ip_1, uint32_t ip_2,
        uint8_t ip_len);

TESTSUITE_BEGIN

TEST_BEGIN("Flowtable Modification")
	openflow_flowtable_init();
	ofp_flow_mod mod;
  uint16_t error_code, error_type;
  memset(&mod, 0, sizeof(ofp_flow_mod));
  mod.flags = htons(OFPFF_SEND_FLOW_REM);
	mod.command = htons(OFPFC_ADD);
	mod.match.wildcards = htons(OFPFW_ALL);
	mod.out_port = htons(OFPP_NONE);
  mod.header.length = htons(0);
  mod.priority = htons(19);

	openflow_flowtable_modify(&mod, &error_type, &error_code);
	openflow_flowtable_release();
TEST_END

TESTSUITE_END
