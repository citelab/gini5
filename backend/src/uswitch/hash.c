/* hash.c - contains all the functions for managing the hash table */

#include <signal.h>
#include <stdlib.h>
#include <stdio.h>
#include <string.h>
#include <sys/time.h>

#include "cleanup.h"	/* for CLEANUP_DO() macro */
#include "error.h"
#include "hash.h"

/* hash table for MAC addresses */
static struct hash_entry *hash_tbl[HASH_SIZE];	

/* prototypes */
static inline void hash_insert_entry(unsigned char *, struct hash_entry *, 
		struct port *);
static inline void hash_del_entry(struct hash_entry *);
static void sig_alarm(int sig);

/* searches the hash for a given mac address and sets e to the resulting
 * hash_entry or NULL on failure
 */
#define HASH_FIND(mac, e)						\
	do {								\
		for (e = hash_tbl[HASH_CALC(mac)]; e; e = e->next) {	\
			if (!memcmp(&(e->mac), mac, ETH_ALEN))		\
				break;					\
		}							\
	} while (0);

/* return the port corresponding to a given MAC address */
struct port * 
hash_find_port(unsigned char mac[ETH_ALEN])
{
	struct hash_entry * e;
	HASH_FIND(mac, e);
	return (e != NULL) ? e->port : NULL;
}

static inline void
hash_insert_entry(unsigned char * mac, struct hash_entry * e, 
		struct port * port)
{
	int k;

	k = HASH_CALC(mac);

	/* create new entry and place in hash */
	if ((e = malloc(sizeof(struct hash_entry))) == NULL)
		CLEANUP_DO(ERR_MALLOC);

	memcpy(&e->mac, mac, ETH_ALEN);
	/* insert into top of hash chain */
	if (hash_tbl[k] != NULL) 
		hash_tbl[k]->prev = e;
	e->next = hash_tbl[k];
	e->prev = NULL;
	e->port = port;
	e->last_seen = time(NULL);
	hash_tbl[k] = e;
}

void
hash_update(unsigned char mac[ETH_ALEN], struct port * p)
{
	struct hash_entry * e;

	HASH_FIND(mac, e);

	if (e == NULL || e->port == NULL)
		hash_insert_entry(mac, e, p);
	else if (e->port == p)
		e->last_seen = time(NULL);	/* update entry time */
	else {
		/* port changed ?! */
		DPRINTF(2, "%02x:%02x:%02x:%02x:%02x:%02x old %d new %d\n",
			mac[0], mac[1], mac[2], mac[3], mac[4], mac[5],
			p->id, e->port->id);
		hash_delete(mac);
		hash_insert_entry(mac, e, p);
	}
}

/* deletes an entry from the hash given a valid hash_entry */
static inline void
hash_del_entry(struct hash_entry * e)
{
	int k;

	k = HASH_CALC(e->mac);

	if (e->prev != NULL)
		e->prev->next = e->next;
	if (e->next != NULL)
		e->next->prev = e->prev;
	if (hash_tbl[k] == e)
		hash_tbl[k] = e->next;
	free(e);
}

/* delete MAC address from hash */
void 
hash_delete(unsigned char mac[ETH_ALEN]) 
{
	struct hash_entry * e;

	HASH_FIND(mac, e);
	if (e != NULL)
		hash_del_entry(e);	
}

/* dump all values in hash, for debugging purposes */
void 
hash_print(void) 
{
	fprintf(stderr, "----DUMPING HASH----\n");

	int k;
	struct hash_entry *e;

	for (k = 0; k < HASH_SIZE; ++k) {
		fprintf(stderr, "HASH %d:\n", k);
		for (e = hash_tbl[k]; e != NULL; e = e->next) {
			fprintf(stderr, "\tAddr: %02x:%02x:%02x:%02x:%02x:%02x "
					"to port: %d  age %ld secs\n", 
					e->mac[0], e->mac[1], e->mac[2], 
					e->mac[3], e->mac[4], e->mac[5],
					e->port->id, 
					(time(NULL) - e->last_seen));
		}
	}
}

#define GC_INTERVAL	60	/* Length between each SIGALRM */

/* signal handler for SIGALRM
 * cleans up expired entries in hash at each GC_INTERVAL
 */
static void
sig_alarm(int sig)
{
	int i;
	time_t t;
	struct hash_entry *e;
	struct hash_entry *next;
	struct itimerval it;

	t = time(NULL);

	/* iterate through hash and clean up any expired entries */
	for (i = 0; i < HASH_SIZE; ++i) {
		for (e = hash_tbl[i]; e != NULL; e = next) {
			next = e->next;
			if (e->last_seen + max_age < t)
				hash_del_entry(e);
		}
	}

	/* setup timer for next alarm */
	it.it_value.tv_sec = GC_INTERVAL;
	it.it_value.tv_usec = 0;
	it.it_interval.tv_sec = 0;
	it.it_interval.tv_usec = 0;
	setitimer(ITIMER_REAL, &it, NULL);

}

void
hash_init(void)
{
	/* setup SIGALRM handler */

	struct sigaction sa;

	sa.sa_handler = sig_alarm;
	sa.sa_flags = SA_RESTART;
	if (sigaction(SIGALRM, &sa, NULL) < 0)
		CLEANUP_DO(ERR_SIGACTION);
	else
		kill(getpid(), SIGALRM);
}

