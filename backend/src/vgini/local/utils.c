#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "packet.h"


char *IP2Dot(char *buf, uchar ip_addr[])
{
	sprintf(buf, "%u.%u.%u.%u", ip_addr[3], ip_addr[2], ip_addr[1], ip_addr[0]);
	return buf;
}



int Dot2IP(char *buf, uchar ip_addr[])
{
        unsigned int iip_addr[4];
        int i;

        sscanf(buf, "%u.%u.%u.%u", &(iip_addr[3]), &(iip_addr[2]), &(iip_addr[1]), &(iip_addr[0]));

        for (i=0; i < 4; i++) ip_addr[i] = iip_addr[i];
        return EXIT_SUCCESS;
}


// This is unaltered by the endianess. We treat the MAC as a string.
int Colon2MAC(char *buf, uchar mac_addr[])
{
        unsigned int imac_addr[6];
        int i;

        sscanf(buf, "%x:%x:%x:%x:%x:%x", &(imac_addr[0]), &(imac_addr[1]), &(imac_addr[2]),
	       &(imac_addr[3]), &(imac_addr[4]), &(imac_addr[5]));

        for (i=0; i < 6; i++) mac_addr[i] = imac_addr[i];
        return EXIT_SUCCESS;
}



char *MAC2Colon(char *buf, uchar mac_addr[])
{

	sprintf(buf, "%02x:%02x:%02x:%02x:%02x:%02x", mac_addr[0], mac_addr[1], mac_addr[2],
		mac_addr[3], mac_addr[4], mac_addr[5]);
	return buf;
}


int gAtoi(char *str)
{
	int val = 0;
	int indx = 1, i;

	for (i = strlen(str); i >= 0; i--)
	{
		if ((str[i] <= '9') && (str[i] >= '0'))
		{
			val += indx * (str[i] - '0');
			indx *= 10;
		}
	}
	return val;
}





unsigned char *gHtonl(unsigned char tbuf[], unsigned char val[])
{
	long inpara, outpara;

	memcpy(&inpara, val, 4);
	outpara = htonl(inpara);
	memcpy(tbuf, &outpara, 4);

	return tbuf;
}


unsigned char *gNtohl(unsigned char tbuf[], unsigned char val[])
{
	long inpara, outpara;

	memcpy(&inpara, val, 4);
	outpara = ntohl(inpara);
	memcpy(tbuf, &outpara, 4);

	return tbuf;
}


