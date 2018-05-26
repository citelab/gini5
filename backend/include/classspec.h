/*
 * classspec.h (include file for the classifier specifications)
 * AUTHOR: Muthucumaru Maheswaran
 * DATE: June 27, 2008
 *
 * The class specifications are used by the classifier to compose traffic classes.
 * The traffic classes are used in defining the packet filters (stateless firewalls)
 * and packet queues. The packets queues are defined to group packets into
 * aggregates to give differential treatment for the packets.
  */

#ifndef __CLASS_SPEC_H__
#define __CLASS_SPEC_H__

#include "grouter.h"


typedef struct _ip_spec_t
{
	uchar ip_addr[4];
	int preflen;
} ip_spec_t;


typedef struct _port_range_t
{
	int minport;
	int maxport;
} port_range_t;


#define INIT_ANY_NET		{.ip_addr={0,0,0,0}, .preflen=0}
#define INIT_ALL_PORTS		{.minport=0, .maxport=0}
#define INIT_ALL_PROT		-1

#define IS_ANY_NET(X)		bcmp((char *)X, (char *)&ANY_NET, sizeof(ip_spec_t)) == 0
#define IS_ANY_PORT(X)		bcmp((char *)X, (char *)&ALL_PORTS, sizeof(port_range_t)) == 0
#define IS_ANY_PROT(X) 		X == -1


// Function prototypes
_begin_decls

_end_decls
#endif
