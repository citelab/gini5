#include <unistd.h>
#include <stdio.h>
#include <stdlib.h>
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
#include "tapdev.h"
#include "utils.h"
#include "cli.h"

#define SERVER_PORT		(50007)
#define SERVER_IP		{127,0,0,1}

pthread_t tap_thread;
pthread_t cli_thread;
pthread_t gini_thread;

int tap_fd;
int server_fd;
int gini_fd;
int gini_status;

/* char buf_interface[256]; */
/* char buf_ipfo[256]; */
/* char buf_parp[256]; */
/* char buf_sysc[256]; */
/* char gini_ip[20]; */

void *gini_polling(void *val);
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
	char tap_name[IFNAMSIZ];
	tap_name[0] = '\0';
	char server_addr[20];
	short server_port;
	char server_req[100];
	char local_name[20];
  memset(buf_sysc,0,256);
  memset(buf_parp,0,256);
  memset(buf_ipfo,0,256);
  memset(buf_interface,0,256);
  memset(gini_ip,0,20);

	struct sockaddr_in serverSockAddr;
	struct sockaddr_in localSockAddr;
	struct sockaddr_in giniSockAddr;

	bzero(server_addr, 20);
	if (ac == 1)		// no parameter
	{
		strcpy(server_addr, "127.0.0.1");
		server_port = 50007;
	}
	// else if (ac == 2)	// set specific ip
	// {
	// 	strcpy(server_addr, av[1]);
	// 	server_port = 50007;
	// }
	// else if (ac == 3)	// set specific ip & port
	// {
	// 	strcpy(server_addr, av[1]);
	// 	server_port = (short)atoi(av[2]);
	// }
	else				// error command line
	{
		fprintf(stderr, "Command Line Error!\n");
		exit(1);
	}

	// self init
	strcpy(local_name, "TEST");
	gini_status == OFF;

	/* Hey Yiwei, this commented block is relative with you
	   U can read it and modify it properly.
	// connect to server and send local information
	int serverSocketFD = socket(PF_INET, SOCK_STREAM, IPPROTO_TCP);
	memset(&serverSockAddr, 0, sizeof(struct sockaddr_in));
    serverSockAddr.sin_family = AF_INET;
    serverSockAddr.sin_port = htons(server_port);
	ret = inet_pton(AF_INET, server_addr, &serverSockAddr.sin_addr);

    if (0 > ret)
    {
      perror("error: first parameter is not a valid address family");
      close(serverSocketFD);
      exit(EXIT_FAILURE);
    }
    else if (0 == ret)
    {
      perror("char string (second parameter does not contain valid ipaddress");
      close(serverSocketFD);
      exit(EXIT_FAILURE);
    }/proc/sys/net/ipv4/ip_forward

    if (-1 == connect(serverSocketFD, (const struct sockaddr *)&serverSockAddr, sizeof(struct sockaddr_in)))
    {
      perror("connect failed");
      close(serverSocketFD);
      exit(EXIT_FAILURE);
    }

	server_fd = serverSocketFD;

	sprintf(server_req, "start, %s, %s, %d, end", local_name, "127.0.0.1", 4900);
	send(server_fd, server_req, sizeof(server_req), 0);
	recv(server_fd, server_req, sizeof(server_req), 0);
	printf("Server Replies: %s\n", server_req);
	*/

	// start UDP server for gini create corresponding thread
    int giniSocketFD = socket(PF_INET, SOCK_DGRAM, IPPROTO_UDP);
	memset(&localSockAddr, 0, sizeof(struct sockaddr_in));
    localSockAddr.sin_family = AF_INET;
    localSockAddr.sin_port = htons(4900);
    localSockAddr.sin_addr.s_addr = INADDR_ANY;

	if (-1 == bind(giniSocketFD, (struct sockaddr *)&localSockAddr, sizeof(struct sockaddr)))
	{
		perror("error bind failed");
		close(giniSocketFD);
		exit(EXIT_FAILURE);
	}
	gini_fd = giniSocketFD;
	pthread_create(&gini_thread, NULL, gini_polling, &giniSockAddr);

	// create tap0
	tap_fd = tap_creat(tap_name, IFF_TAP | IFF_NO_PI);
	if(tap_fd < 0)
	{
		perror("tun_create");
		return 1;
	}
	printf("TAP dev name is %s\n",tap_name);

	pthread_create(&tap_thread, NULL, tap_rolling, NULL);

	//ret = system("ifconfig tap0 10.0.0.1 netmask 255.255.255.0");

  printf("uid:%d\n",geteuid());
	CLIInit(&cli_thread);
	wait4thread(tap_thread);

	return 0;
}

void *gini_polling(void *val)
{
	struct sockaddr_in *giniSockAddr = (struct sockaddr_in *)val;
	socklen_t fromlen;
	char tmpbuf[2000];
	char *nexttok;
	char gini_mac[20];
	char cmd[100];
	ssize_t recsize;
	int ret;

	int i;
	int numbers;
	int pieces;
	int len;

	fromlen = sizeof(struct sockaddr_in);

  /* printf("polling thread: connecting\n"); */
	// receive the first packet from gini, set virtual address, set status=ON
	recsize = recvfrom(gini_fd, (void *)tmpbuf, (size_t)2000, 0, (struct sockaddr *)giniSockAddr, &fromlen);
  if (recsize == -1) {
    perror("initial proxy receive error");
  }
	if (connect(gini_fd, (struct sockaddr *)giniSockAddr, fromlen) != 0) {
    perror("proxy connection error");
  }

  /* printf("polling thread: parsing initial input\n"); */
	// Set address according to the content of tmpbuf
	nexttok = strtok(tmpbuf, ",\0");
	if (strcmp(nexttok, "start") != 0)
	{
		printf("gini command error.\n");
		exit (1);
	}
	// ip
	nexttok = strtok(NULL, ",\0");
	sprintf(gini_ip, "%s", nexttok);

	// mac 
	nexttok = strtok(NULL, ",\0");
	sprintf(gini_mac, "%s", nexttok);

	// ending
	nexttok = strtok(NULL, ",\0");
	if (strcmp(nexttok, "end") != 0)
	{
		printf("gini command error.\n");
		exit (1);
	}

  /* printf("polling thread, starting validation\n"); */
	// Verify the input for the IP is valid
	numbers = 0;
	pieces = 0;
	len = strlen(gini_ip);
	for (i = 0; i < len; i++)
	{
		if('0' <= gini_ip[i] && gini_ip[i] <= '9')
		{
			if(numbers++ >= 3)
			{
				printf("Too many numbers in IP\n");
				exit (1);
			}
		}
		else if (gini_ip[i] == '.')
		{
			if(pieces++ >= 3)
			{
				printf("Too many pieces in IP\n");
				exit (1);
			}
			numbers = 0;
		}
		else
		{
			printf("Invalid character for IP\n");
			exit (1);
		}
	}

	// Verify the input for the MAC is valid
	numbers = 0;
	pieces = 0;
	len = strlen(gini_mac);
	for (i=0; i < len; i++)
	{
		if (('0' <= gini_mac[i] && gini_mac[i] <= '9') ||
			('a' <= gini_mac[i] && gini_mac[i] <= 'f') ||
			('A' <= gini_mac[i] && gini_mac[i] <= 'F'))
		{
			if (numbers++ >= 2)
			{
				printf("Too many numbers for MAC\n");
				exit (1);
			}
		}
		else if (gini_mac[i] == ':')
		{
			if (pieces++ >= 5)
			{
				printf("Too many pieces in the MAC");
				exit (1);
			}
			numbers = 0;
		}
		else
		{
			printf("Invalid character for MAC\n");
			exit (1);
		}
	}
  /* printf("polling thread: validation done\n"); */

	ret = system("/sbin/ifconfig tap0 down");
	sprintf(cmd, "/sbin/ifconfig tap0 hw ether %s", gini_mac);
	ret = system(cmd);
	sprintf(cmd, "/sbin/ifconfig tap0 %s netmask 255.255.255.0", gini_ip);
	ret = system(cmd);
	ret = system("/sbin/ifconfig tap0 up");
	gini_status = ON;

	char c;
	c = 0;
	FILE *fp_interface = popen("/bin/bash \"route | grep default | tr -s ' ' | cut -d ' ' -f 8\"", "r");
	if (fp_interface != NULL)
	{
		for (i=0; c != EOF; i++)
		{
			c = fgetc(fp_interface);
			if (c != EOF && c != '\n')
				buf_interface[i] = c;
		}
		pclose(fp_interface);
	}
	FILE *fp_ipfo = fopen("/proc/sys/net/ipv4/ip_forward", "r");
	if (fp_ipfo != NULL)
	{
		for (i=0; c != EOF; i++)
		{
			c = fgetc(fp_ipfo);
			if (c != EOF && c != '\n')
				buf_ipfo[i] = c;
		}
		fclose(fp_ipfo);
	}
	c = 0;
	sprintf(cmd, "/proc/sys/net/ipv4/conf/%s/proxy_arp", buf_interface);
	FILE *fp_parp = fopen(cmd, "r");
	if (fp_parp != NULL)
	{
		for (i=0; c != EOF; i++)
		{
			c = fgetc(fp_parp);
			if (c != EOF && c != '\n')
				buf_parp[i] = c;
		}
		fclose(fp_parp);
	}
	c = 0;
	FILE *fp_sysc = popen("/sbin/sysctl -n net.ipv6.conf.all.forwarding", "r");
	if (fp_sysc != NULL)
	{
		for (i=0; c != EOF; i++)
		{
			c = fgetc(fp_sysc);
			if (c != EOF && c != '\n')
				buf_sysc[i] = c;
		}
		pclose(fp_sysc);
	}
	ret = system("/bin/echo 1 > /proc/sys/net/ipv4/ip_forward");
	ret = system("/bin/echo 1 > /proc/sys/net/ipv4/conf/tap0/proxy_arp");
  sprintf(cmd,"/bin/echo 1 > /proc/sys/net/ipv4/conf/%s/proxy_arp",buf_interface);
	ret = system(cmd);
	sprintf(cmd, "/sbin/route add -host %s dev tap0", gini_ip);
	ret = system(cmd);
	sprintf(cmd, "/usr/sbin/arp -Ds %s %s pub", gini_ip,buf_interface);
	ret = system(cmd);
	ret = system("/sbin/sysctl -w net.ipv6.conf.all.forwarding=1");

	// the following packets should be normal gpackets
	for (;;) 
	{
		memset(tmpbuf, 0, 1024);
		recsize = recvfrom(gini_fd, (void *)tmpbuf, (size_t)2000, 0, (struct sockaddr *)giniSockAddr, &fromlen);
		if (recsize < 0)
		{
			fprintf(stderr, "%s\n", strerror(errno));
		}
		else
		{
			ret = write(tap_fd, tmpbuf, (size_t)2000);
		}
	}
}

