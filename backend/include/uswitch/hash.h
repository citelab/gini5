/* hash.h - header information for hash structure and related functions */
/* AUTHOR: Alexis Malozemoff */

#ifndef __HASH_H__
#define __HASH_H__

#include <time.h>

#include "port.h"
#include "uswitch.h"	/* ETH_ALEN */

#define HASH_SIZE 	8
#define HASH_VAL 	11

#define HASH_CALC(mac)	\
	((((unsigned int)mac[0] % HASH_VAL) ^ mac[4] ^ mac[5]) % HASH_SIZE)

struct hash_entry {
	unsigned char mac[ETH_ALEN];
	struct port * port;
	time_t last_seen;
	struct hash_entry * prev;
	struct hash_entry * next;
};

/* prototypes */
struct port * hash_find_port(unsigned char *);
void hash_update(unsigned char *, struct port *); 
void hash_delete(unsigned char *);
void hash_print(void);
void hash_init(void);

#endif /* __HASH_H__ */
