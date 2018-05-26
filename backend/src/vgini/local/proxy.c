#include <unistd.h>
#include <stdio.h>
#include <string.h>
#include <assert.h>
#include <sys/types.h>
#include <arpa/inet.h>
#include <sys/socket.h>
#include <signal.h>
#include <unistd.h>
#include <linux/if_tun.h>
#include <netinet/in.h>
#include <sys/ioctl.h>
#include <sys/time.h>
#include <linux/if.h>
#include <errno.h>
#include <fcntl.h>  

#include "packet.h"
#include "utils.h"
#include "vpl.h"

pthread_t vt_thread;
pthread_t gini_thread;
pthread_t delay_thread;

int vt_fd;
int gini_fd;

void *vt_polling(void *val);
void *gini_polling(void *val);

struct _io_fd
{
	int vt;
	vpl_data_t *gini;
} io_fd;

/*
 * Redefine signal handlers
 */
void redefineSignalHandler(int sigid, void (*my_func)(int signum))
{
	struct sigaction handler, old_handler;

	handler.sa_handler = my_func;
	sigemptyset(&handler.sa_mask);
	handler.sa_flags = 0;

	sigaction(sigid, NULL, &old_handler);
	if (old_handler.sa_handler != SIG_IGN)
		sigaction(sigid, &handler, NULL);
	else
		verbose(1, "[redefineSignalHandler]:: signal %d is already ignored.. redefinition ignored ", sigid);

}

void wait4thread(pthread_t threadid)
{
	int *jstatus;
	if (threadid > 0)
		pthread_join(threadid, (void **)&jstatus);
}

int main(int ac, char *av[])
{
	int ret;
	int thread_stat;

	char vt_addr[20];
	short vt_port;

	struct sockaddr_in vtSockAddr;
	struct sockaddr_in localSockAddr;

	char gini_ip[20];
	char gini_mac[20];
	char sock_file[100];

	char tmpbuf[512];
	char cmd[100];

	vpl_data_t *pri = (vpl_data_t *)malloc(sizeof(vpl_data_t));

	bzero(vt_addr, 20);
	strcpy(vt_addr, "127.0.0.1");
	vt_port = 4900;
	if (ac < 4) 
	{
		printf("Error: need 3 arguments (ip, mac, socket_file)\n");
		return;
	}
	strcpy(gini_ip, av[1]);
	strcpy(gini_mac, av[2]);
	strcpy(sock_file, av[3]);
	// strcpy(gini_ip, "192.168.1.3");
	// strcpy(gini_mac, "fe:fd:03:01:00:01");
	// strcpy(sock_file, "/home/bshagi/.gini/data/Router_1/gini_socket_eth1.ctl");

	// if (ac == 1)		// no parameter
	// {
	// }
	// else if (ac == 2)	// set specific ip
	// {
	// }
	// else if (ac == 3)	// set specific ip & port
	// {
	// }
	// else				// error command line
	// {
	// 	fprintf(stderr, "Command Line Error!\n");
	// 	exit(1);
	// }

	// setup gini socket link
	if ((pri = vpl_connect(sock_file)) == NULL)
	{
		if ((pri = vpl_create_server(sock_file)) == NULL)
		{
			printf("Unable to make server connection...");
			return 0;
		}

		thread_stat = pthread_create(&delay_thread, NULL, (void *)delayedServerCall, (void *)pri);
		if (thread_stat != 0)
			return 0;
	}
	gini_fd = pri->data;

	// setup udp link to virtual terminal
	int vt_fd = socket(PF_INET, SOCK_DGRAM, IPPROTO_UDP);
	memset(&vtSockAddr, 0, sizeof(struct sockaddr_in));
	vtSockAddr.sin_family = AF_INET;
	vtSockAddr.sin_port = htons(vt_port);
	ret = inet_pton(AF_INET, vt_addr, &vtSockAddr.sin_addr);

	if (0 > ret)
	{
		perror("error: first parameter is not a valid address family");
		close(vt_fd);
		exit(EXIT_FAILURE);
	}
	else if (0 == ret)
	{
		perror("char string (second parameter does not contain valid ipaddress");
		close(vt_fd);
		exit(EXIT_FAILURE);
	}

	if (-1 == connect(vt_fd, (const struct sockaddr *)&vtSockAddr, sizeof(struct sockaddr_in)))
	{
		perror("connect failed");
		close(vt_fd);
		exit(EXIT_FAILURE);
	}

	sprintf(tmpbuf, "start,%s,%s,end", gini_ip, gini_mac);
	send(vt_fd, tmpbuf, strlen(tmpbuf) + 1, 0);


	io_fd.vt = vt_fd;
	io_fd.gini = pri;

	// start thread for gini and virtual terminal
	pthread_create(&vt_thread, NULL, vt_polling, (void *)&io_fd);
	pthread_create(&gini_thread, NULL, gini_polling, (void *)&io_fd);

	wait4thread(vt_thread);
	wait4thread(gini_thread);

	return 0;
}

void *vt_polling(void * val)
{
	char tmpbuf[2000];
	int len;
	int ret;

	while(1)
	{
		len = read(io_fd.vt, tmpbuf, 2000);
		//printf("One packet! vt -> gini len: %d\n", len);
		//ret = write(io_fd.gini, tmpbuf, len);
		ret = vpl_sendto(io_fd.gini, tmpbuf, len);
		//printf("write len: %d\n", ret);
		//perror("vt -> gini");
	}
}

void *gini_polling(void *val)
{
	char tmpbuf[2000];
	int len;
	int ret;

	while(1)
	{
		//len = read(io_fd.gini, tmpbuf, 2000);
		len = vpl_recvfrom(io_fd.gini, tmpbuf, 2000);
		//printf("One packet! gini -> vt len: %d\n", len);
		ret = write(io_fd.vt, tmpbuf, len);
		//printf("write len: %d\n", ret);
	}
}


