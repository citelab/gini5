#ifndef UTILS_H
#define UTILS_H

#define OFF   0
#define ON    1
#define TRUE  1
#define FALSE 0

char *IP2Dot(char *buf, uchar ip_addr[]);
int Dot2IP(char *buf, uchar ip_addr[]);
int Colon2MAC(char *buf, uchar mac_addr[]);
char *MAC2Colon(char *buf, uchar mac_addr[]);
int gAtoi(char *str);
unsigned char *gHtonl(unsigned char tbuf[], unsigned char val[]);
unsigned char *gNtohl(unsigned char tbuf[], unsigned char val[]);

#endif	// UTILS_H
