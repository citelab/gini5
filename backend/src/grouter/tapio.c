/*
 * This file provides the set of functions to open, read, and write the tap
 * interface. The tap interface is used to connect the virtual network created
 * by GINI to the Internet.
 */

#include "grouter.h"
#include "vpl.h"
#include "simplequeue.h"
#include "message.h"
#include <string.h>
#include <stdlib.h>
#include <errno.h>
#include <unistd.h>
#include <fcntl.h>
#include <syslog.h>
#include <stdio.h>

#include <slack/std.h>
#include <slack/err.h>
#include <slack/fio.h>
#include <sys/stat.h>
#include <sys/ioctl.h>
#include <sys/types.h>
#include <sys/socket.h>
#include <linux/if.h>
#include <linux/if_tun.h>


/*
 * You don't need to read this file unless you
 * are debugging the gRouter for transmission problems to and from the
 * Internet.
 */



/*
 * Connect to the tap interface. We already have the tap0 interface setup
 * using an external script.
 */

vpl_data_t *tap_connect(char *sock_name)
{
	struct ifreq ifr;
	int n, fd;

	verbose(2, "[vpl_connect]:: starting connection.. ");
	vpl_data_t *pri = (vpl_data_t *)malloc(sizeof(vpl_data_t));
	bzero(pri, sizeof(sizeof(vpl_data_t)));

	// initialize the vpl_data structure.. much of it is unused here.
	// we are reusing vpl_data_t to minimize the changes for other code.
	pri->sock_type = "tap";
	pri->ctl_sock = strdup(sock_name);
	pri->ctl_addr = NULL;
	pri->data_addr = NULL;
	pri->local_addr = NULL;
	pri->data = -1;
	pri->control = -1;


	if ((fd = open("/dev/net/tun", O_RDWR)) < 0) {
		verbose(2, "[tap_connect]:: opening /dev/net/tun failed, error = %s", strerror(errno));
	    return NULL;
	}

	memset(&ifr, 0, sizeof(ifr));
	ifr.ifr_flags = IFF_TAP;

	if ( *sock_name )
		strncpy(ifr.ifr_name, sock_name, IFNAMSIZ);

	if (ioctl(fd, TUNSETIFF, (void *) &ifr) < 0)
	{
		verbose(2, "[tap_connect]:: unable to execute TUNSETIFF, error = %s", strerror(errno));
		return NULL;
	}

	pri->data = fd;
	pri->data_addr = strdup(ifr.ifr_name);

	return pri;
}



/*
 * Receive a packet from the vpl. You can use this with a "select"
 * function to multiplex between different interfaces or you can use
 * it in a multi-processed/multi-threaded server. The example code
 * given here should work in either mode.
 */
int tap_recvfrom(vpl_data_t *vpl, void *buf, int len)
{
	int n;
	uchar localbuf[MAX_MESSAGE_SIZE];

	while (((n = read(vpl->data, localbuf, len)) < 0) && (errno == EINTR))
		;

	if (n < 0) {
		if (errno == EAGAIN)
			return (0);
		return (-errno);
	} else if (n == 0)
		return (-ENOTCONN);

	// strip the 4 bytes prepended to the packet..
	bcopy((localbuf+4), buf, n-4);

	return (n-4);
}


/*
 * Send packet through the tap interface pointed by the vpl data structure..
 */

int tap_sendto(vpl_data_t *vpl, void *buf, int len)
{
	int n;
	uchar localbuf[MAX_MESSAGE_SIZE];

	bzero(localbuf, MAX_MESSAGE_SIZE);
	bcopy(buf, (localbuf+4), len);

	while(((n = write(vpl->data, localbuf, len+4)) < 0) && (errno == EINTR)) ;
	if(n < 0)
	{
		if(errno == EAGAIN) return(0);
		return(-errno);
	}
	else if(n == 0) return(-ENOTCONN);
	return(n);
}


