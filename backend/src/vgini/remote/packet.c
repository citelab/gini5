#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "packet.h"

int printEthernetHeader(gpacket_t *msg)
//int printEthernetHeader(pkt_data_t *msg)
{
	char tmpbuf[MAX_TMPBUF_LEN];
	int prot;

	printf("\n    P A C K E T  D A T A  S E C T I O N of GMESSAGE \n");
	printf(" DST MAC addr : \t %s\n", MAC2Colon(tmpbuf, msg->data.header.dst));
	printf(" SRC MAC addr : \t %s\n", MAC2Colon(tmpbuf, msg->data.header.src));
	prot = ntohs(msg->data.header.prot);
	printf(" Protocol : \t %x\n", prot);

	fflush(NULL);

	return prot;
}

