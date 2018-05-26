/*
 * This example code shows how you can connect to a port of the
 * uml_virtual_switch when it is running in HUB mode. To put the
 * virtual switch in hub mode just include the word "hub" in the
 * config file for the switch in a line by itself.

 * This example code is based on code borrowed from different portions
 * of the UML source code. The original code is copyrighted as follows:

 * Copyright (C) 2001 Lennert Buytenhek (buytenh@gnu.org) and
 * James Leu (jleu@mindspring.net).
 * Copyright (C) 2001 by various other people who didn't put their name here.
 * Licensed under the GPL.
 */

#include "vpl.h"
#include "gwcenter.h"
/*
 * Local support routines...
 * I don't expect you to use these! These routines are used by other
 * routines.
 */


int __vpl_sendto(int fd, void *buf, int len, void *to, int sock_len)
{
        int n;

        while(((n = sendto(fd, buf, len, 0, (struct sockaddr *) to,
                           sock_len)) < 0) && (errno == EINTR)) ;
        if(n < 0){
                if(errno == EAGAIN) return(0);
                return(-errno);
        }
        else if(n == 0) return(-ENOTCONN);
        return(n);
}



/*
 * Virtual physical layer connect routine. This routine connects to
 * the HUB or Switch that is already running in daemon mode.
 */

int vpl_connect(struct vpl_data *pri)
{
	struct sockaddr_un *ctl_addr = pri->ctl_addr;
	struct sockaddr_un *local_addr = pri->local_addr;
	struct sockaddr_un *sun;
	struct request_v3 req;
	int fd, n, err;

	//printf("ctl_addr->family is: ... %s\n", (char*)(ctl_addr->sun_family));
	//printf("ctl_addr->path is: ... %s\n", (char*)(ctl_addr->sun_path));
	//printf("pchSocket[1] = %s\n", pchSocket[1]);

	if((pri->control = socket(AF_UNIX, SOCK_STREAM, 0)) < 0){
		printf("virtual physical layer : control socket failed, errno = %d\n", errno);
		return(-errno);
	}

	if(connect(pri->control, (struct sockaddr *) ctl_addr,
		   sizeof(*ctl_addr)) < 0){
		printf("virtual physical layer : control connect failed, errno = %d\n", errno);
		err = -errno;

		close(pri->control);
		return(err);
	}

	if((fd = socket(AF_UNIX, SOCK_DGRAM, 0)) < 0){
		printf("virtual physical layer : data socket failed, errno = %d\n",
		       errno);
		err = -errno;

		close(pri->control);
		return(err);
	}
	if(bind(fd, (struct sockaddr *) local_addr, sizeof(*local_addr)) < 0){
		printf("virtual physical layer : data bind failed, errno = %d\n",
		       errno);
		err = -errno;

		close(fd);
		close(pri->control);
		return(err);
	}

	sun = malloc(sizeof(struct sockaddr_un));
	if(sun == NULL){
		printf("new_addr: allocation of sockaddr_un failed\n");
		err = -ENOMEM;

		close(fd);
		close(pri->control);
		return(err);
	}

	req.magic = SWITCH_MAGIC;
	req.version = SWITCH_VERSION;
	req.type = REQ_NEW_CONTROL;
	req.sock = *local_addr;
	n = write(pri->control, &req, sizeof(req));
	if(n != sizeof(req)){
		printf("virtual physical layer : control setup request returned %d, "
		       "errno = %d\n", n, errno);
		err = -ENOTCONN;

		close(pri->control);
		return(err);
	}

	n = read(pri->control, sun, sizeof(*sun));
	if(n != sizeof(*sun)){
		printf("virtual physical layer : read of data socket returned %d, "
		       "errno = %d\n", n, errno);
		err = -ENOTCONN;

		close(fd);
		close(pri->control);
		return(err);
	}

	pri->data_addr = sun;
	return(fd);
}


/*
 * Receive a packet from the vpl. You can use this with a "select"
 * function to multiplex between different interfaces or you can use
 * it in a multi-processed/multi-threaded server. The example code
 * given here should work in either mode.
 */

int vpl_recvfrom(int fd, void *buf, int len)
{
        int n;

        while(((n = recvfrom(fd,  buf,  len, 0, NULL, NULL)) < 0) &&
              (errno == EINTR)) ;

        if(n < 0){
                if(errno == EAGAIN) return(0);
                return(-errno);
        }
        else if(n == 0) return(-ENOTCONN);
        return(n);
}


int vpl_sendto(int fd, void *buf, int len, struct vpl_data *pri)
{
	struct sockaddr_un *data_addr = pri->data_addr;

	return(__vpl_sendto(fd, buf, len, data_addr, sizeof(*data_addr)));
}



/*
 * Cast the address in appropriate format for the socket.
 */

struct sockaddr_un *new_addr(void *name, int len)
{
	struct sockaddr_un *sun;

	sun = malloc(sizeof(struct sockaddr_un));
	if(sun == NULL){
		printf("new_addr: allocation of sockaddr_un failed\n");
		return(NULL);
	}
	sun->sun_family = AF_UNIX;
	memcpy(sun->sun_path, name, len);

	return(sun);

}



/*
 * Overrides for Emacs so that we follow Linus's tabbing style.
 * Emacs will notice this stuff at the end of the file and automatically
 * adjust the settings for this buffer only.  This must remain at the end
 * of the file.
 * ---------------------------------------------------------------------------
 * Local variables:
 * c-file-style: "linux"
 * End:
 */
