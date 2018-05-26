/* uswitch.h
 * program to simulate a switch for user-mode-linux instances
 */

#ifndef __USWITCH_H__
#define __USWITCH_H__

#include <stdint.h>
#include <sys/un.h>

/* from <linux/if_ether.h> */
#define ETH_ALEN 6

#define MAX_REMOTE 8
#define SWITCH_MAGIC 0xfeedface

enum request_type { REQ_NEW_CONTROL };

extern int debug_flag;
extern int force_flag;
extern int hub_flag;

extern int max_age;

/* structs */

union sa {
	struct sockaddr *s;
	struct sockaddr_un *sun;
	struct sockaddr_in *sin;
};
    

struct fd {
	int fh;			/* file handler */
	void (*handle)(int);	/* handler function */
	struct port *rmport;	/* remote port */
	struct fd *next;	/* next item in linked list */
	struct fd *prev;
};

struct request_v3 {
	uint32_t magic;
	uint32_t version;
	enum request_type type;
	struct sockaddr_un sa_un;
};

#endif /* __USWITCH_H__ */
