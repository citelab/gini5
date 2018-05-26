#include "openflow_config.h"
#include "mut.h"
#include <stdint.h>



#include "common_def.h"

TESTSUITE_BEGIN
// Initial required objects


// begin tests

TEST_BEGIN("Simple openflow_config_gnet_to_of_port_num calls")
uint16_t result = openflow_config_get_of_port_num(0);
CHECK(result==1);
result = openflow_config_get_of_port_num(65534);
CHECK(result==65535)
TEST_END

TEST_BEGIN("Simple openflow_config_of_to_gnet_port_num calls")
uint16_t result = openflow_config_get_gnet_port_num(1);
CHECK(result==0);
result = openflow_config_get_gnet_port_num(65535);
CHECK(result==65534)
TEST_END

TEST_BEGIN("Assert gnet to openflow to gnet")
uint8_t i;
for(i=0; i<100; i++){
  CHECK(i==openflow_config_get_of_port_num(openflow_config_get_gnet_port_num(i)))
}
TEST_END

TEST_BEGIN("Assert openflow to gnet to openflow")
uint8_t i;
for(i=1; i<101; i++){
  CHECK(i==openflow_config_get_gnet_port_num(openflow_config_get_of_port_num(i)))
}
TEST_END

TESTSUITE_END
