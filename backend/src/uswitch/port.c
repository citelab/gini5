
#include <stdio.h>
#include <stdlib.h>
#include <sys/socket.h>

#include "cleanup.h"
#include "error.h"
#include "hash.h"
#include "port.h"
#include "multiswitch.h"


#define IS_BROADCAST(mac) ((mac[0] & 1) == 1)

extern int hub_flag;

/* head of the port list */
static struct port * phead = NULL;

/* prototypes */
static void port_print_list(void);
static char * port_dbg(char * s, const struct port *p);
static void port_print_list(void);

#define SOCKADDR_SIZE	sizeof (struct sockaddr)

/* locate a port given a sockaddr */
#define PORT_FIND(sa, p)					\
	do {							\
		for (p = phead; p != NULL; p = p->next)		\
			if (!memcmp(p->sa, sa, SOCKADDR_SIZE))	\
				break;				\
	} while (0)

/* TEMPORARY: FIX HERE FOR NEXT VERSION */
/* We don't want outside modules calling port_find,
 * but udp_data needs to call it
 */
void
port_find(struct sockaddr * sa, struct port * p)
{
	PORT_FIND(sa, p);
}

static void
port_print_list(void)
{
	struct port * p;

	for (p = phead; p != NULL; p = p->next) {
		fprintf(stderr, "Port found: ");
		fprintf(stderr, "id=%d ", p->id);
		fprintf(stderr, "sa->sun_family=%d ", 
				((struct sockaddr_un *)p->sa)->sun_family);
		fprintf(stderr, "sa->sun_path=%s ", 
				((struct sockaddr_un *)p->sa)->sun_path);
		fprintf(stderr, "fh=%d ", p->fh);
		fprintf(stderr, "\n");
	}
}

/* insert a port with the given handler */
struct port *
port_insert(void (*sender)(struct port *p, struct packet *packet, int len),
				int fh, struct sockaddr * sa) 
{
	struct port *port;

	if ((port = malloc(sizeof (struct port))) == NULL)
		CLEANUP_DO(ERR_MALLOC); 

	/* initialize port and insert into beginning of list */
	port->next = phead;
	if (phead != NULL)
		phead->prev = port;
	port->prev = NULL;
	port->fh = fh;

	port->id = (phead == NULL) ? 100 : phead->id + 1;
	port->sa = sa;
	port->sender = sender;
	phead = port;

	return port;
}

struct port *
port_send(struct sockaddr * sa, struct packet * pkt, int len) 
{
	struct port *src_port;
	struct port *dst_port;

	PORT_FIND(sa, src_port);
	//    Removing this check because packets incoming from switches will not have
	//    a source port.
	//if (!src_port)
	//	return NULL;

	//DPRINTF(1, "found source port!\n");

	/* update the src MAC's hash entry */
	if ((!hub_flag) && (src_port != NULL))
		hash_update(pkt->header.src, src_port);

	/* locate the dst mac address */
	dst_port = hash_find_port(pkt->header.dst);

	/* if dst mac addr is broadcast or hub mode,
	 * then send to all ports */
	if (IS_BROADCAST(pkt->header.dst) || hub_flag) {

		if (debug_flag && !dst_port) {
			fprintf(stderr, "Broadcast addr: "
				"%02x:%02x:%02x:%02x:%02x:%02x",
			       	pkt->header.dst[0], pkt->header.dst[1],
			       	pkt->header.dst[2], pkt->header.dst[3],
			       	pkt->header.dst[4], pkt->header.dst[5]);
			if (src_port == NULL)
				fprintf(stderr, " from unknown source\n");
			else
				fprintf(stderr, " from port %d\n",src_port->id);
		}

		for (dst_port = phead; dst_port; dst_port = dst_port->next) {
			/* don't send it back the port it came in */
			if (dst_port != src_port) {
				if (debug_flag) 
					send_dbg(dst_port, pkt, len);
				(*dst_port->sender)(dst_port, pkt, len);
			}
		}

		// Forward to all switches
		ms_broadcast(pkt, len, sa);

		DPRINTF(1, "broadcast sent\n");
	}
	else if (dst_port == NULL) {
	       	// If the destination is not a direcly connected UML, forward to switches only
		ms_broadcast(pkt, len, sa);
	}
	else {
		DPRINTF(1, "found destination port!\n");
		if (debug_flag) 
			send_dbg(dst_port, pkt, len);
		(*dst_port->sender)(dst_port, pkt, len);
	}
	return src_port;
}

void 
port_delete(struct port *p) 
{
	char s[99];
	DPRINTF(1, "Closing port [%s]\n", port_dbg(s, p));

	if (p->prev)
		p->prev->next = p->next;
	else
		phead = p->next;
	if (p->next)
		p->next->prev = p->prev;

	free(p->sa);
	free(p);
}

void 
send_dbg(struct port *port, struct packet *p, int len) 
{
	unsigned char s[99], *psrc = p->header.src, *pdst = p->header.dst;
	DPRINTF(1, "%02x:%02x:%02x:%02x:%02x:%02x -> "
		"%02x:%02x:%02x:%02x:%02x:%02x\n",
	       psrc[0], psrc[1], psrc[2], psrc[3], psrc[4], psrc[5],
	       pdst[0], pdst[1], pdst[2], pdst[3], pdst[4], pdst[5]);
	DPRINTF(1, "%d bytes on [%s]\n", len, port_dbg(s, port));
}

static char * 
port_dbg(char * s, const struct port *p) 
{
	unsigned char *c =  ((struct sockaddr_un *) p->sa)->sun_path;
	sprintf(s, "sock(%d, %d) f%d "
		"%02x:%02x:%02x:%02x:%02x:%02x:%02x:%02x:%02x",
		p->id, p->fh, p->sa->sa_family, 
		c[0], c[1], c[2], c[3], c[4], c[5], c[6], c[7], c[8]);
	return s;
} 

/* removes all ports registered by the switch */
static void 
cleanup_port(void) 
{
	struct port *p;
	struct port *next;
	DPRINTF(1, "Deleting all ports\n");
	for (p = phead; p != NULL; p = next) {
		next = p->next;
		port_delete(p);
	}
}
