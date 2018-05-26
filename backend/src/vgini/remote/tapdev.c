#include <unistd.h>
#include <stdio.h>
#include <string.h>
#include <assert.h>
#include <sys/types.h>
#include <sys/socket.h>
#include <netinet/in.h>
#include <signal.h>
#include <unistd.h>
#include <linux/if_tun.h>
#include <netinet/in.h>
#include <sys/ioctl.h>
#include <sys/time.h>
#include <linux/if.h>
#include <netinet/in.h>
#include <arpa/inet.h>
#include <errno.h>
#include <fcntl.h>  

#include "packet.h"
#include "tapdev.h"
#include "utils.h"

extern int tap_fd;
extern int gini_fd;
extern int gini_status;

int tun_alloc(char *dev)
{
	struct ifreq ifr;
	int fd, err;

	if( (fd = open("/dev/net/tun", O_RDWR)) < 0 )
		//return tun_alloc_old(dev);
		return fd;

	memset(&ifr, 0, sizeof(ifr));

	/* Flags: IFF_TUN   - TUN device (no Ethernet headers) 
	 *        IFF_TAP   - TAP device  
	 *
	 *        IFF_NO_PI - Do not provide packet information  
	 */ 
	ifr.ifr_flags = IFF_TUN; 
	if( *dev )
		strncpy(ifr.ifr_name, dev, IFNAMSIZ);

	if( (err = ioctl(fd, TUNSETIFF, (void *) &ifr)) < 0 ){
		close(fd);
		return err;
	}
	strcpy(dev, ifr.ifr_name);
	return fd;
}              

int tap_creat(char *dev, int flags)
{
	struct ifreq ifr;
	int fd,err;

	assert(dev != NULL);
	if((fd = open ("/dev/net/tun", O_RDWR))<0) //you can replace it to tap to create tap device.
		return fd;

	memset(&ifr, 0, sizeof(ifr));
	ifr.ifr_flags |= flags;

	if(*dev != '\0')
		strncpy(ifr.ifr_name, dev, IFNAMSIZ);

	if((err = ioctl(fd, TUNSETIFF, (void *)&ifr))<0)
	{
		close (fd);
		return err;
	}

	strcpy(dev, ifr.ifr_name);

	return fd;
}

void *tap_rolling(void *val)
{
	int len;
	int ret;
	unsigned char ip[4];
	//char *buf = ((char *)&gpkt_temp) + sizeof(pkt_frame_t);
	char buf[1500];

	while (1) {
		memset(buf, 0, 1500);
		len = read(tap_fd, buf, DEFAULT_MTU);
		if (ret < 0)
			break;

		//printEthernetHeader(&gpkt_temp);

		// make an instant reply to echo-request
		/*
		memcpy(ip, &buf[12], 4);
		memcpy(&buf[12], &buf[16], 4);
		memcpy(&buf[16], ip, 4);
		buf[20] = 0;
		*((unsigned short*)&buf[22]) += 8;
		if (gini_status == ON)
		{
			ret = write(tap_fd, &gpkt_temp, ret + sizeof(pkt_frame_t));
		}
		*/
		if (gini_status == ON)
		{
			ret = write(gini_fd, buf, len);
		}
	}

}




