/*
 * moduledefs.h (all the module definitions go here)
 * AUTHOR: Muthucumaru Maheswaran
 * DATE: December 18, 2004
 * VERSION: Beta
 */

#ifndef __MODULEDEFINITIONS_H__
#define __MODULEDEFINITIONS_H__

// TODO: Find a better way of defining or reusing some other
// definitions
#define GNET_ADAPTER            10
#define ARP_MODULE              11
#define IP_MODULE               12
#define ICMP_MODULE             13
#define CLI_MODULE              14




// setup the information needed to bootstrap the modules
// we need this information to start the individual modules
// TO ADD A NEW MODULE: Add the module signature here.

// define your modules here...
// Each entry should define the {protocol ID, module name, and module handler}
// list below shows the modules that are defined and initialized by
// default...
#define LIST_OF_MODULES   moduledirectory_t moddir[] = { \
	{  \
		GNET_ADAPTER, \
		"GINI ETHERNET MODULE", \
		gnetHandler, \
	}, \
	{  \
		ARP_MODULE, \
		"GINI ARP MODULE", \
		arpHandler, \
	}, \
	{ \
		IP_MODULE, \
		"GINI IP MODULE", \
		ipHandler, \
	}, \
	{ \
		ICMP_MODULE, \
		"GINI ICMP MODULE", \
		icmpHandler, \
	}, \
	{ \
		CLI_MODULE, \
		"GINI CLI MODULE", \
		cliHandler, \
	} \
} 


void *arpHandler(void *arg);
void *ipHandler(void *arg);
void *icmpHandler(void *arg);
void *cliHandler(void *arg);
void *gnetHandler(void *arg);

#endif
