#ifndef __MULTISWITCH_H
#define __MULTISWITCH_H


/*
 * Julien Villemure, julien@cs.mcgill.ca
 * Student ID: 260151677
 *
 * COMP 535 Final Project, Fall 2009
 *
*/

#include <stdint.h>

#include "port.h"


#define IS_BRIDGE_GROUP_ADDR(X) ( \
    ((X)[0] == 0x01) && \
    ((X)[1] == 0x80) && \
    ((X)[2] == 0xC2) && \
    ((X)[3] == 0x00) && \
    ((X)[4] == 0x00) && \
    ((X)[5] == 0x00) \
)

#define SET_BRIDGE_GROUP_ADDR(X) \
    (X)[0] = 0x01; \
    (X)[1] = 0x80; \
    (X)[2] = 0xC2; \
    (X)[3] = 0x00; \
    (X)[4] = 0x00; \
    (X)[5] = 0x00;


union bridge_id {

    struct {
	uint16_t priority;
	uint8_t	 mac[6];
    };

    uint8_t id[8];		// priority (2) + MAC address (6)

};

typedef struct _bpdu_t {

    uint16_t	protocol;	// set to 0 for STP
    uint8_t	version;	// set to 0 for this version of STP
    uint8_t	type;		// set to 0 for configuration BPDU
    uint8_t	flags;		// set to 0 unless dealing with topology change

    union bridge_id root;	// bridge ID believed to be the root

    uint32_t	cost;		// cost of path to root

    union bridge_id bridge;	// bridge ID of sender

    uint16_t	port;		// port ID within a bridge

    // Our simplified protocol doesn't use any of the fields below
    //uint16_t	age;		// age of the message
    //uint16_t	max_age;	// maximum age
    //uint16_t	hello_time;	// hello time
    //uint16_t	forward_delay;	// forward delay

    // Instead we use the space for this:
    union bridge_id gateway;	// bridge ID of root port, i.e. next hop towards the root

} bpdu_t;


// Socket for communicating with other switches

extern int ms_sock;


// Function prototypes

int ms_init (uint16_t priority, uint8_t mac[6]);
void ms_parse_file (char *path);
void ms_broadcast (struct packet *pkt, int len, struct sockaddr *sa);
void ms_stp ();


#endif
