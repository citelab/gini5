/* uswitch.c
 * program to simulate a switch for user-mode-linux instances
 */


#include <errno.h>
#include <fcntl.h>
#include <getopt.h>
#include <netdb.h>
#include <pwd.h>
#include <signal.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>
#include <unistd.h>
#include <linux/if_tun.h>
#include <net/if.h>
#include <netinet/in.h>
#include <sys/ioctl.h>
#include <sys/socket.h>
#include <sys/stat.h>
#include <sys/time.h>
#include <sys/types.h>
#include <sys/un.h>

#include "cleanup.h"
#include "hash.h"	/* hash_init() */
#include "error.h"
#include "port.h"
#include "uswitch.h"
#include "multiswitch.h"


/* user flags */
int debug_flag =	2;	/* 0 - normal, 1+ debug */
int force_flag =	0;
int hub_flag = 		0;

static struct option long_options[] =
{
	{"maxage",	required_argument,	NULL, 'a'},
	{"debug",	no_argument,		NULL, 'd'},
	{"force",	no_argument,		&force_flag, 1},
	{"help",	no_argument,		NULL, 'h'},
	{"hub",		no_argument,		&hub_flag, 1},
	{"logfile",	required_argument,	NULL, 'l'},
	{"pidfile",	required_argument,	NULL, 'p'},
	{"sockfile",	required_argument,	NULL, 's'},
	{"targetfile",	required_argument,	NULL, 't'},
	{"priority",	required_argument,	NULL, 'P'},
	{"mac",		required_argument,	NULL, 'm'},
	{"udp_port",	required_argument,	NULL, 'u'},
	{0, 0, 0, 0}
};

extern int errno;

/* the maximum age an unused MAC address can live in the switch
 * before it is flushed.  We default it here to 200, but that
 * can be changed by the user
 */
int max_age =	200;

static char * g_cmdname;		/* name of program */
static char * pidfile		= NULL; /* name of pidfile */
static char * g_sockname 	= NULL;	/* name of socket file */

struct fd *g_sockdatafd = NULL;	/* packets sent by UML */
struct fd *g_sockctrlfd = NULL; /* control messages from UML */
struct sockaddr_un g_sun_dat;

struct fd *g_fdhead 	= NULL;	/* head of fd linked-list */
int g_fdmax 		= 0;	/* next available file descriptor */

/* for udp connections */
static int g_udpport = 0;
static int g_udpfd = 0;

fd_set set;

static struct fd *fd_insert(void (*)(int), int, struct port *);
static void fd_delete(struct fd *);

void send_sock(struct port *p, struct packet *packet, int len);
void send_tap(struct port *p, struct packet *packet, int len);
void send_udp(struct port *p, struct packet *packet, int len);
void usage(int);


/*
 * Various cleanup functions which are registered with cleanup_add()
 */

/* delete all file descriptors */
static void cleanup_fd(void)
{
	struct fd * fd;
	struct fd * next;

	DPRINTF(1, "Closing all filedescriptors\n");

	for (fd = g_fdhead; fd != NULL; fd = next) {
		next = fd->next;
		fd_delete(fd);
	}
}

/* closes the pidfile and removes it */
static void cleanup_pidfn(void)
{
	if (unlink(pidfile) < 0) {
		DPRINTF(0, ERR_UNLINK " %s", pidfile);
		perror(" ");
	}
}

/* closes the data and control sockets and removes the sockfile */
static void cleanup_sock(void)
{
	DPRINTF(1, "Closing sockets...\n");

	fd_delete(g_sockctrlfd);
	DPRINTF(1, "Closed control socket %d\n", g_sockctrlfd->fh);

	fd_delete(g_sockdatafd);
	DPRINTF(1, "Closed data socket %d\n", g_sockdatafd->fh);

	DPRINTF(1, "Unlink control socket %s.\n", g_sockname);
	if (unlink(g_sockname) < 0)
		DPRINTF(0, ERR_UNLINK " %s\n", g_sockname);
}

static void cleanup_udp(void)
{
	DPRINTF(1, "Closing udp port\n");
	close(g_udpfd);
}

/*
 * File descriptor insert and delete
 */

static struct fd *
fd_insert(void (*handle)(int), int fh, struct port *p)
{
	struct fd *fd;

	DPRINTF(1, "Setup filedescriptor #%d\n", fh);

	if ((fd = malloc(sizeof(struct fd))) == 0)
		CLEANUP_DO(ERR_MALLOC);

	/* setup fd and insert into beginning of linked list */
	fd->next = g_fdhead;
	if (g_fdhead != NULL)
		g_fdhead->prev = fd;
	fd->prev = NULL;
	fd->fh = fh;
	if (fh >= g_fdmax)
		g_fdmax = fh + 1;
	fd->handle = handle;
	fd->rmport = p;
	g_fdhead = fd;

	return fd;
}

/* delete a given fd */
static void
fd_delete(struct fd *fd)
{
	DPRINTF(1, "Closing filedescriptor #%d\n", fd->fh);

	if (fd->prev != NULL)
		fd->prev->next = fd->next;
	else
		g_fdhead = fd->next;
	if (fd->next != NULL)
		fd->next->prev = fd->prev;
	if (fd->rmport != NULL)
		port_delete(fd->rmport);
	close(fd->fh);
	free(fd);

	/* reset g_fdmax (just for completeness) */
	g_fdmax = 1;
	for (fd = g_fdhead; fd != NULL; fd = fd->next) {
		if (fd->fh >= g_fdmax)
			g_fdmax = fd->fh + 1;
	}
}

/*
 * Socket functions
 */

void
send_sock(struct port *p, struct packet *packet, int len)
{
	int n;

	n = sendto(p->fh, (void *) packet, len, 0,
	       (struct sockaddr *) p->sa, sizeof(struct sockaddr_un));
//	if (n != len && errno != EAGAIN) {
	if (n != len) {
		/* Ignore "resource temporarily unavailable" errors */
		DPRINTF(2, "sendto() failed with length %d", n);
		if (debug_flag > 1)
			perror(" ");

		if (errno == ECONNREFUSED) {
			struct fd *fd;
			DPRINTF(0, "Connection refused, looking for "
					"uml-connection to remove.\n");
			for (fd = g_fdhead; fd != NULL; fd = fd->next) {
				if (fd->rmport == p) {
					DPRINTF(0, "Clearing filedescriptor "
							"%d\n", fd->fh);
					fd_delete(fd);
				}
			}
		}
	}
}

/* Create a new UML socket.
 * This occurs when the control socket receives a message for
 * a file descriptor with a NULL remote port
 */
void
create_sock(struct fd *fd)
{
	int n;			/* number of bytes from read() */
	int sa_un_len;
	struct sockaddr * sa;
	struct request_v3 req;
	struct port *port;
	struct sockaddr_un sun_dat;

	DPRINTF(1, "Adding UML socket #%d\n", fd->fh);

	n = read(fd->fh, &req, sizeof (struct request_v3));

	DPRINTF(2, "%d bytes read\n", n);

	if (n < 0) {
		perror(ERR_READ);
		goto error;
	} else if (n == 0) {
		DPRINTF(0, ERR_READ ": EOF\n");
		goto error;
	} else if (req.magic != SWITCH_MAGIC) {
		DPRINTF(0, ERR_READ ": wrong magic\n");
		goto error;
	} else if (n < sizeof(struct request_v3)) {
		DPRINTF(0, ERR_READ ": short request\n");
		goto error;
	}
	if (req.type == REQ_NEW_CONTROL) {
		sa = malloc(sizeof (struct sockaddr_un));
		if (sa == NULL)
			CLEANUP_DO(ERR_MALLOC);

		memcpy((struct sockaddr_un *) sa, &req.sa_un,
				sizeof (struct sockaddr_un));

		sa_un_len = sizeof (struct sockaddr_un);
		if (getsockname(g_sockdatafd->fh, (struct sockaddr *)
					&sun_dat, &sa_un_len) < 0) {
			DPRINTF(0, ERR_GETSOCKNAME);
			perror(" ");
			goto error;
		}
		if (sa_un_len < sizeof(struct sockaddr_un)) {
			DPRINTF(0, ERR_GETSOCKNAME ": short name\n");
			goto error;
		}

		DPRINTF(2, "writing socket address\n");

		n = write(fd->fh, &sun_dat, sa_un_len);
		if (n != sa_un_len) {
			DPRINTF(0, ERR_WRITE);
			perror(" ");
			goto error;
		}


		/* success! */
		port = port_insert(send_sock, g_sockdatafd->fh, sa);
		fd->rmport = port;
		DPRINTF(2, "port %d added\n", fd->rmport->id);
		return;
	} else {
		DPRINTF(0, "FATAL (internal bug): bad request %d\n", req.type);
	}

error:
	close(fd->fh);
}

/* Close a UML socket.
 * This occurs when the control socket receives a message for
 * a file descriptor with a remote port already set
 */
static void
delete_sock(struct fd *fd)
{
	int n;
	char c[256];

	DPRINTF(1, "Closing UML socket #%d\n", fd->fh);

	n = read(fd->fh, &c, sizeof(c));
	if (n < 0) {
		perror(ERR_READ);
	} else if (n == 0) {
		DPRINTF(2, "normal disconnect\n");
	} else {
		DPRINTF(0, "Could read %d characters on socket #%d\n",
				n, fd->fh);
		DPRINTF(0, "Bad request, but closing anyway\n");
	}
	fd_delete(fd);
}

/* Called as the handler for a new file descriptor.
 * If the remote port has not been set, we call create_sock(),
 * otherwise, delete_sock() is used
 */
static void
handle_other_sock(int fh)
{
	struct fd *fd;

	DPRINTF(1, "event on socket %d\n", fh);

//	fd = g_fdhead;
//	if (fd->fh == fh) {	/* ??? */
//		if (fd->rmport == NULL)
//			create_sock(fd);
//		else
//			delete_sock(fd);
//	}
	for (fd = g_fdhead;  fd != NULL; fd = fd->next) {
		if (fd->fh == fh) {
			if (fd->rmport == NULL)
				create_sock(fd);
			else
				delete_sock(fd);
		}
	}
	if (fd == NULL)
		DPRINTF(1, "couldn't find socket!\n");
}

/* An event occurred on the control socket.
 * This means we create a new file descriptor and add it to
 * the list, using the handle_other_sock() handler
 */
static void
handle_ctrl_sock(int fh)
{
	int len;
        int new;
	struct fd *fd;
	struct sockaddr addr;

	DPRINTF(1, "event on control socket %d\n", fh);

	len = sizeof (struct sockaddr);
	new = accept(fh, &addr, &len);
	if (new < 0) {
		DPRINTF(0, ERR_ACCEPT);
		perror(" ");
		return;
	}
	if (fcntl(new, F_SETFL, O_NONBLOCK) < 0) {
		DPRINTF(0, ERR_FCNTL);
		perror(" ");
		close(new);
		return;
	}

	/* new connection, set NULL for the port */
	fd = fd_insert(handle_other_sock, new, NULL);
}

/* An event occurred on the data socket.
 * This mean we are receiving data from the network, so we
 * locate the necessary port and send it.
 */
static void
handle_data_sock(int fd)
{
	int len;
	struct packet packet;
	struct sockaddr_un sa;
	struct port *p;
	socklen_t sa_len = sizeof (sa);

	DPRINTF(1, "event on data file descriptor %d\n", fd);

	/* extract data from socket */
	len = recvfrom(fd, &packet, sizeof (packet), 0, &sa, &sa_len);
	if (len < 0) {
		if (errno != EAGAIN)
			DPRINTF(1, ERR_RECVFROM);
		return;
	}

	/* send data to specific port */

	p = port_send(&sa, &packet, len);
	//if (!p)
	//	DPRINTF(0, "FATAL: no incoming port for packet\n");

	/* XXX: port_find could use a cache... */
//	PORT_FIND(&sa, p);
//	if (p != NULL)
//		port_send(p, &packet, len);
//	else
//		DPRINTF(0, "FATAL (internal bug): no incoming port for "
//				"socket packet\n");
}

#if 0
void sock_owner(char *arg)
{
	if (g_sockctrlfd != NULL) {
		struct passwd *pw;
		if ((pw = getpwnam(arg)) == NULL) {
			printf("user %s not found.\n", arg);
			cleanup_do(NULL);
		}
		printf("set owner of %s to %d:%d.\n", g_sockname, pw->pw_uid, pw->pw_gid);
		if (fchown(g_sockctrlfd->fh, pw->pw_uid, pw->pw_gid) <0) {
			cleanup_do("fchown(sock_owner)");
		}
		if (chown(g_sockname, pw->pw_uid, pw->pw_gid) <0) {
			cleanup_do("chown(sock_owner)");
		}
	} else {
		printf("setting socket owner without active socket.\n");
	}
}
#endif

/*
 * Tap functions
 */

#if 0
struct port *g_porttap = NULL;
struct fd *g_tapfd;
char *g_tapdown;
void send_tap(struct port *p, struct packet *packet, int len)
{
	if (write(p->fh, (void *) packet, len) != len) {
		if (errno != EAGAIN)
			perror("send_tap(): " ERR_WRITE);
		else
			printf("notice: tap packet dropped.");
	}
}
void tap_cleanup(void)
{
	if (debug_flag >0) printf("Close tap interface.\n");
	if (g_tapdown != NULL) {
		if (debug_flag >1) printf("tap_cleanup: execute system(%s).\n", g_tapdown);
		system(g_tapdown);
		free(g_tapdown);
	}
	close(g_porttap->fh);
}
void tap_data(int fd)
{
	struct packet packet;
	int len;
	if (debug_flag >1)
		printf("tap_data: event on tapfd %d.\n", fd);
	len = read(fd, &packet, sizeof(struct packet));
	if (len <0) {
		if (errno != EAGAIN)
			perror("tap_data(): " ERR_READ);
		return;
	}
	if (debug_flag >1) printf("send packet with len %d from tap-device.\n", len);
	port_send(g_porttap, &packet, len);
}
void tap_up(char *cmd)
{
	if (g_porttap != NULL) {
		if (debug_flag >1) printf("tap_up: execute system(%s).\n", cmd);
		system(cmd);
	}
	else printf("Error: define tap device prior to defining up-cmd.\n");
}
void tap_dn(char *cmd)
{
	if (g_porttap != NULL) {
		if (debug_flag >1) printf("Execute system(%s).\n", cmd);
		if ((g_tapdown = malloc(strlen(cmd)+1)) == NULL)
			cleanup_do("malloc(tap_dn)");
		strcpy(g_tapdown, cmd);
	}
	else printf("Error: define tap device prior to defining down-cmd.\n");
}
void tap_setup(char *name)
{
	struct ifreq ifr;
	union sa sa;
	int tapfd;
	sa.s = NULL;
	if (debug_flag >0) printf("Setup tap interface %s.\n", name);
	if ((tapfd = open("/dev/net/tun", O_RDWR)) < 0)
		cleanup_do("open(tap_setup)");
	memset(&ifr, 0, sizeof(ifr));
	ifr.ifr_flags = IFF_TAP | IFF_NO_PI;
	strncpy(ifr.ifr_name, name, sizeof(ifr.ifr_name) -1);
	if (ioctl(tapfd, TUNSETIFF, (void *) &ifr) < 0)
		cleanup_do("ioctl(tap_setup)");
	cleanup_add(tap_cleanup);
	g_porttap = port_insert(send_tap, tapfd, sa);
	g_tapfd = fd_insert(tap_data, tapfd, g_porttap);
}
#endif

/*
 * UDP functions
 */

void send_udp(struct port * p, struct packet * packet, int len)
{
	int r;
	if ((r = sendto(p->fh, (void *) packet, len, 0, p->sa,
		       sizeof (struct sockaddr_in))) != len) {
		DPRINTF(0, "udp-sendto returned %d.\n", r);
		DPRINTF(0, "p->fh=%d, len=%d, p->sa->sa_family=%d.\n",
				p->fh, len, p->sa->sa_family);
		if (errno != EAGAIN)
			perror("sendto(send_udp)");
		else
			DPRINTF(0, "Bug: udp packet dropped.");
	}
	struct sockaddr_in * sin = (struct sockaddr_in *) p->sa;
	DPRINTF(1, "IP Address: %s\tPort:%d\tFamily: %d\n",
			inet_ntoa(sin->sin_addr),
			ntohs(sin->sin_port),
			sin->sin_family);
	DPRINTF(1, "called successfully!\n");
}

void udp_data(int fd)
{
	struct packet packet;
//	struct sockaddr_in * sin_from;
	struct sockaddr_in sin_from;
	struct port *p;
	int len;
	int sinlen = sizeof (struct sockaddr_in);

	DPRINTF(1, "event on udpfd %d\n", fd);

	len = recvfrom(fd, &packet, sizeof (struct packet), 0,
			(struct sockaddr *) &sin_from, &sinlen);
	if (len < 0) {
		if (errno != EAGAIN)
			perror(ERR_RECVFROM);
			// DPRINTF(0, ERR_RECVFROM);
		return;
	}

	DPRINTF(0, "IP Address: %s\tPort:%d\tFamily: %d\n",
			inet_ntoa(sin_from.sin_addr),
			ntohs(sin_from.sin_port),
			sin_from.sin_family);

	if (sin_from.sin_port != htons(g_udpport)) {
		DPRINTF(1, "dropping packet from wrong udp port %d.\n",
				htons(sin_from.sin_port));
		return;
	}

//	port_send((struct sockaddr *) sin_from, &packet, len);

	DPRINTF(1, "calling port_find()...\n");
	if (!port_send((struct sockaddr *) &sin_from, &packet, len)) {
		DPRINTF(1, "No port found\n");
		port_insert(send_udp, fd, (struct sockaddr *) &sin_from);
		port_send((struct sockaddr *) &sin_from, &packet, len);
	} else {
		DPRINTF(1, "remote port found!!!\n");
	}

	/*
	DPRINTF(1, "calling port_find()...\n");
	fflush(stderr);
	port_find((struct sockaddr *) &sin_from, p);
	if (p == NULL) {
		DPRINTF(1, "No port found\n");
		p = port_insert(send_udp, fd, (struct sockaddr *) &sin_from);
	} else {
		DPRINTF(1, "remote port found!!!\n");
	}
	port_send((struct sockaddr *) &sin_from, &packet, len);
	*/
//
//	port_find((struct sockaddr *) sin_from, p);
//	if (p == NULL) {
//		fprintf(stderr, "OH NO!!!!!!\n");
	//	p = port_insert(send_udp, fd, (struct sockaddr *) sin_from);
//		if (debug_flag > 1) {
//			char s[99];
//			DPRINTF(2, "created new udp port [%s]\n",
//					port_dbg(s, p));
//		}
//	}
//	port_send(p, &packet, len);
}

/*
 * Main loop
 */

/* does the main work */
void work(struct timeval *gctime)
{
	int n;
	struct fd *fd;
        struct fd *next;
	//fd_set set;

	DPRINTF(1, "select() called on file descriptors");

	FD_ZERO(&set);
	for (fd = g_fdhead; fd != NULL; fd = fd->next) {
	    //if (!FD_ISSET(fd->fh, &set)) {
    		if (debug_flag)
		    fprintf(stderr, " %d", fd->fh);
		FD_SET(fd->fh, &set);
	    //}
	}

	// Also set the multiswitch socket
	FD_SET(ms_sock, &set);

	if (debug_flag)
		fprintf(stderr, "\n");

	n = select(g_fdmax, &set, NULL, NULL, gctime);

	DPRINTF(1, "select() found %d file descriptor(s)\n", n);

	if (n == 0) {	/* timeout expired */
		DPRINTF(2, "timeout occurred, clearing cache\n");
		kill(getpid(), SIGALRM);
	} else if (n < 0) { 	/* select() failed, possibly interrupted */
		if (debug_flag)
			perror("select() failed");
	} else {	/* found >= 1 file descriptor(s) */
		for (fd = g_fdhead; fd != NULL; fd = next) {
			next = fd->next;
			if (FD_ISSET(fd->fh, &set)) {
				fd->handle(fd->fh);	/* access info */
				FD_CLR(fd->fh, &set);
			}
		}
		if (FD_ISSET(ms_sock, &set)) {
		    handle_data_sock(ms_sock);
		    FD_CLR(ms_sock, &set);
		}
#if 0
		/* now all entries should be cleared ! */
		if (debug_flag >1) {
			int i;
			for (i = 0; i < g_fdmax; i++) {
				if (FD_ISSET(i, &set)) {
					printf("work: unhandled change on fd %d (should never happen).\n", i);
				}
			}
		}
#endif
	}

}

/*
 * Initial setup functions
 */

/* initialize log file */
static void
init_logfile(char *name)
{
	if (name == NULL) {
		DPRINTF(1, "No logfile specified, logging to stderr...\n");
		return;
	}

	time_t t;

	DPRINTF(1, "Using logfile %s\n", name);

	fflush(stderr);

	/* redirect stderr to logfile */
	if (freopen(name, "a", stderr) == NULL)
		CLEANUP_DO(ERR_FREOPEN);

  DPRINTF(1, "stderr redirected\n");

	if (setvbuf(stderr, NULL, _IOLBF, 0) != 0)
		perror("setvbuf() failed");	/* not fatal */

	time(&t);

	DPRINTF(0, "\n*** Starting new logfile at %s\n", ctime(&t));
}

/* creates pidfile */
static void
init_pidfile(char *name)
{
	if (!name) return;

	int fh;
	int n;
	char buf[10];

	DPRINTF(1, "creating pidfile %s\n", name);

	if ((fh = creat(name, S_IRWXU|S_IRGRP|S_IROTH)) < 0)
		CLEANUP_DO(ERR_CREAT);

	fflush(stdout);

	n = snprintf(buf, sizeof buf, "%d\n", getpid());
	write(fh, buf, n);
	if (close(fh) < 0)
		CLEANUP_DO("failed to close pidfile");
	else
		cleanup_add(cleanup_pidfn);
}

static void
init_remote(char *name)
{
	struct hostent *he;
	struct sockaddr_in * sa_in;

	if (g_udpfd == 0)
		CLEANUP_DO("no UDP port specified");

	he = gethostbyname(name);
	if (he == NULL)
		CLEANUP_DO("Host %s cannot be determined", name);

	DPRINTF(1, "host %s (%hhu.%hhu.%hhu.%hhu) added.\n", name,
			he->h_addr_list[0][0], he->h_addr_list[0][1],
			he->h_addr_list[0][2], he->h_addr_list[0][3]);

	if ((sa_in = malloc(sizeof(struct sockaddr_in))) == NULL)
		CLEANUP_DO(ERR_MALLOC);

	sa_in->sin_family = AF_INET;
	sa_in->sin_port = htons(g_udpport);
	sa_in->sin_addr.s_addr = htonl(INADDR_ANY);
	memcpy(&(sa_in->sin_addr.s_addr), he->h_addr_list[0], 4);

	port_insert(send_udp, g_udpfd, (struct sockaddr *) sa_in);
}

/* creates an open UDP socket with the given port number */
static void
init_udp_port(int port)
{
	struct sockaddr_in sin;

	g_udpport = port;

	DPRINTF(1, "Setting up UDP port %d\n", port);

	if ((g_udpfd = socket(PF_INET, SOCK_DGRAM, 0)) < 0)
		CLEANUP_DO(ERR_SOCKET);

	cleanup_add(cleanup_udp);

	/* create UDP socket and bind to port */
	sin.sin_family = AF_INET;
	sin.sin_port = htons(port);
	sin.sin_addr.s_addr = htonl(INADDR_ANY);
	memset(sin.sin_zero, '\0', 8);
	if (bind(g_udpfd, (struct sockaddr *) &sin,
				sizeof (struct sockaddr_in)) <0)
		CLEANUP_DO("bind() failed");

	/* does not have a dedicated port to remove... */
	fd_insert(udp_data, g_udpfd, NULL);
}

static void
bind_ctrl_sock(int fd)
{
	struct sockaddr_un s;

	s.sun_family = AF_UNIX;
	strncpy(s.sun_path, g_sockname, sizeof(s.sun_path));

	if (bind(fd, (struct sockaddr *) &s, sizeof(struct sockaddr_un)) < 0) {
		/* if address already in use, we attempt to remove
		 * the socket and try again
		 */
		if (errno == EADDRINUSE && force_flag) {
			DPRINTF(2, "%s already exists\n", g_sockname);
			if (unlink(g_sockname) < 0)
				CLEANUP_DO(ERR_UNLINK);
			sleep(1);
#if 0
			if ((test_fd = socket(PF_UNIX, SOCK_STREAM, 0)) < 0)
				CLEANUP_DO("socket() failed");
			if (connect(test_fd, (struct sockaddr *) &s,
					sizeof(struct sockaddr_un)) < 0) {
				if (errno == ECONNREFUSED) {
					DPRINTF(0, "Removing unused socket "
							"%s\n", g_sockname);
					if (unlink(g_sockname) < 0)
						CLEANUP_DO(ERR_UNLINK);
				}
				close(test_fd);
			}
#endif
			/* retry bind */
			if (bind(fd, (struct sockaddr *) &s,
					       	sizeof(struct sockaddr_un)) < 0)
				CLEANUP_DO("failed binding control filehandle");
		} else
			CLEANUP_DO("failed binding control filehandle");
	}
}

static void
bind_data_sock(int fd, struct sockaddr_un * sock_out)
{
	pid_t pid;
	struct sockaddr_un s;

	s.sun_family = AF_UNIX;
	memset(s.sun_path, 0, sizeof(s.sun_path));

	pid = getpid();

	memcpy((char *)&s.sun_path + 1, &pid, sizeof(pid_t));

	if (bind(fd, (struct sockaddr *) &s, sizeof(s)) < 0)
		CLEANUP_DO("failed binding data filehandle");

	*sock_out = s;
}

/* initialize socket */
static void
init_sockfile(char *name)
{
	int ctrlfh;
	int datafh;
	struct sockaddr_un sun_dat;

	int one = 1;

	DPRINTF(1, "Setting up control socket %s...\n", name);

	g_sockname = name;

	/* BEGIN: control socket setup */

	if ((ctrlfh = socket(PF_UNIX, SOCK_STREAM, 0)) < 0)
		CLEANUP_DO(ERR_SOCKET);

	if (setsockopt(ctrlfh, SOL_SOCKET,
		      SO_REUSEADDR, (char *) &one, sizeof(one)) < 0)
		CLEANUP_DO("failed setting socket options");

	if (fcntl(ctrlfh, F_SETFL, O_NONBLOCK) < 0)
		CLEANUP_DO(ERR_FCNTL);

	bind_ctrl_sock(ctrlfh);

	cleanup_add(cleanup_sock);

	if (listen(ctrlfh, 15) < 0)
		CLEANUP_DO("failed to listen to filehandle");

	g_sockctrlfd = fd_insert(handle_ctrl_sock, ctrlfh, NULL);

	DPRINTF(1, "Control socket %s created\n", g_sockname);

	/* END: control socket setup */

	/* BEGIN: data socket setup */

	DPRINTF(1, "Setting up data socket (abstract namespace)...\n");

	if ((datafh = socket(PF_UNIX, SOCK_DGRAM, 0)) < 0)
		CLEANUP_DO(ERR_SOCKET);

	if (fcntl(datafh, F_SETFL, O_NONBLOCK) < 0)
		CLEANUP_DO(ERR_FCNTL);

	bind_data_sock(datafh, &sun_dat);

	g_sockdatafd = fd_insert(handle_data_sock, datafh, NULL);

	if (debug_flag) {
		unsigned char *c = (unsigned char *)&sun_dat.sun_path;
		DPRINTF(1, "Data socket "
			"%02x:%02x:%02x:%02x:%02x:%02x:%02x:%02x:%02x "
		        "created\n", c[0], c[1], c[2], c[3], c[4], c[5],
					c[6], c[7], c[8]);
	}

	/* END: data socket setup */
}

/* Signal handler for SIGTERM and SIGINT
 * Cleans up and quits
 */
static void sig_term(int sig)
{
	DPRINTF(1, "SIGTERM/SIGINT received, quitting...\n");
	cleanup_do(EXIT_SUCCESS);
}

/* Signal handler for SIGUSR{1,2}
 * SIGUSR1 toggles hub-mode
 * SIGUSR2 does nothing as of yet
 */
static void sig_usr(int sig)
{
	if (sig == SIGUSR1) {
		DPRINTF(0, "toggling hub mode...\n");
		hub_flag = (hub_flag) ? 0 : 1;
	}
	if (sig == SIGUSR2)
		hash_print();
}

int main(int argc, char *argv[])
{

	int c;			/* getopt character */
	int option_index = 0;	/* index into long_options struct */
	struct sigaction sa_term;
        struct sigaction sa_usr;

	int sa_un_len;

	int sock_flag 		= 0;
	int remote_flag 	= 0;
	int udp_flag 		= 0;
	int udp_port;

	char * log_name		= NULL;
	char * remote_name	= NULL;
	char * targetfile	= NULL;

	int priority = 0;
	char mac[6] = {0, 0, 0, 0, 0, 0};


	opterr = 1;	/* enable error msg when parsing options */

	g_cmdname = argv[0];

	hash_init();
	cleanup_init();

	while((c = getopt_long(argc, argv, "+a:dhl:p:r:s:t:P:m:u:",
			long_options, &option_index)) != -1) {
		switch (c) {
			case 0:
				break;
			case 'a':
				max_age = atoi(optarg);
				break;
			case 'd':
				/* XXX: getopt() can't handle optional
				 * args very well...
				 */
				debug_flag = 2;
				break;
			case 'h': 	/* help */
				usage(EXIT_SUCCESS);
			case 'l':	/* log file */
				log_name = optarg;
				break;
			case 'p':	/* pid file */
				pidfile = optarg;
				break;
			case 'r':
				remote_flag = 1;
				remote_name = optarg;
				break;
			case 's':	/* socket file: required */
				sock_flag = 1;
				g_sockname = optarg;
				break;
			case 't':
				targetfile = optarg;
				break;
			case 'P':
				priority = atoi(optarg);
				break;
			case 'm':
				sscanf(optarg, "%hx:%hx:%hx:%hx:%hx:%hx", mac, mac+1, mac+2, mac+3, mac+4, mac+5);
				break;
			case 'u':
				udp_flag = 1;
				udp_port = atoi(optarg);
				break;
			case '?':
				usage(EXIT_FAILURE);
			default:
				usage(EXIT_FAILURE);
		}
		if (udp_flag) {
			init_udp_port(udp_port);
			udp_flag = 0;
		}
		if (remote_flag) {
			init_remote(remote_name);
			remote_flag = 0;
		}
	}

	if (!sock_flag) {
		DPRINTF(0, "You must specify a socket file using -s or "
				"--socket.\n");
		usage(EXIT_FAILURE);
	}

	init_logfile(log_name);
	init_pidfile(pidfile);
	init_sockfile(g_sockname);

//	if (udp_flag)
//		init_udp_port(udp_port);
//	if (remote_flag)
//		init_remote(remote_name);


	/* initialize signal handlers */

	memset(&sa_term, '\0', sizeof (struct sigaction));
	memset(&sa_usr, '\0', sizeof (struct sigaction));

	sa_term.sa_handler = sig_term;
	if (sigaction(SIGTERM, &sa_term, NULL) < 0)
		CLEANUP_DO(ERR_SIGACTION);
	if (sigaction(SIGINT, &sa_term, NULL) < 0)
		CLEANUP_DO(ERR_SIGACTION);

	sa_usr.sa_handler = sig_usr;
	if (signal(SIGUSR1, sig_usr) < 0)
		CLEANUP_DO("signal() failed");
	if (signal(SIGUSR2, sig_usr) < 0)
		CLEANUP_DO("signal() failed");

	/* initialize the multiswitch module */
	ms_init(priority, mac);
	ms_parse_file(targetfile);

	/* Run STP before any communication is allowed */
	ms_stp();

	/* setup and run main loop */

	struct timeval tv;

	fflush(stdout);
	FD_ZERO(&set);
	for (;;) {
		tv.tv_sec = max_age;
		tv.tv_usec = 0;
		work(&tv);
	}

	cleanup_do(EXIT_SUCCESS);
	return 0;
}

/* TODO: UPDATE!! */
void usage(int status)
{
	printf(
"Usage: %s [OPTION]... -s FILE\n\n"
"  -a, --age [num]        set the age an unused address lives in the switch\n"
"  -d, --debug [level]    set the debug level, between 0 (none) to 2 (max)\n"
"  --hub                  hub mode\n"
"  -h, --help             display this help and exit\n"
"  -l, --logfile FILE     set log file to FILE\n"
"  -p, --pidfile FILE     set pid file to FILE\n"
"  -s, --sockfile FILE    set socket to FILE\n"
"  -t, --targetfile FILE     set target file to FILE\n\n"
	, g_cmdname);
	exit(status);
}
