#ifndef __PORT_H__
#define __PORT_H__

#include "uswitch.h"

struct packet {
	struct {
		unsigned char dst[ETH_ALEN];
		unsigned char src[ETH_ALEN];
		unsigned char prot[2];
	} header;
	unsigned char data[1500];
};

struct port {
	int id;			/* port ID */
	struct sockaddr * sa;
	int fh;			/* internal file handler for port */
	void (*sender)		/* handler function */
		(struct port *, struct packet *, int);	
	struct port *next;	/* next item in list */
	struct port *prev;	/* prev item in list */
};

/* prototypes */
struct port * port_insert(void (*)(struct port *, struct packet *, int),
				int, struct sockaddr *);
void port_delete(struct port *); 
struct port * port_send(struct sockaddr *, struct packet *, int); 
void send_dbg(struct port *, struct packet *, int); 

#endif /* __PORT_H__ */
