/*
 * ip.h (header file for Internet protocol (IP)
 * AUTHOR: Originally written by Weiling Xu
 *         Revised by Muthucumaru Maheswaran
 * DATE: December 24, 2004
 *
 */


#ifndef __IP_H_
#define __IP_H_

#include "grouter.h"
#include "message.h"
#include <stdint.h>
#include <endian.h>

/*
 * Private definitions: only used within the IP module
 */

/*
 * IP packet definition.. taken from <netinet/ip.h>
 * Made verbose for readability...
 * Definitions for internet protocol version 4.
 * Per RFC 791, September 1981.
 */
typedef struct _ip_packet_t
{
#if __BYTE_ORDER == __LITTLE_ENDIAN
	uint8_t ip_hdr_len:4;                   // header length 
	uint8_t ip_version:4;                   // version 
#endif
#if __BYTE_ORDER == __BIG_ENDIAN
	uint8_t ip_version:4;                   // version 
	uint8_t ip_hdr_len:4;                   // header length 
#endif
	uint8_t ip_tos;                         // type of service 
	uint16_t ip_pkt_len;                    // total length 
	uint16_t ip_identifier;                 // identification 
	uint16_t ip_frag_off;                   // fragment offset field 
#define IP_RF 0x8000                            // reserved fragment flag 
#define IP_DF 0x4000                            // dont fragment flag 
#define IP_MF 0x2000                            // more fragments flag 
#define IP_OFFMASK 0x1fff                       // mask for fragmenting bits 
	uint8_t ip_ttl;                         // time to live 
	uint8_t ip_prot;                        // protocol 
	uint16_t ip_cksum;                      // checksum 
	uchar ip_src[4], ip_dst[4];             // source and dest address 
} ip_packet_t;

#define TEST_DF_BITS(X)                 ( (X & IP_DF) >> 14)
#define TEST_MF_BITS(X)                 ( (X & IP_MF) >> 13)
#define SET_DF_BITS(X)                  X = ( X | (0x00001 << 14) )
#define SET_MF_BITS(X)                  X = ( X | (0x00001 << 13) )
#define RESET_DF_BITS(X)                X = ( X & (~(0x00001 << 14)) )
#define RESET_MF_BITS(X)                X = ( X & (~(0x00001 << 13)) )


// function prototypes...

void IPInit();
void IPIncomingPacket(gpacket_t *in_pkt);
int IPCheckPacket4Me(gpacket_t *in_pkt);
int IPProcessBcastPacket(gpacket_t *in_pkt);
int IPProcessForwardingPacket(gpacket_t *in_pkt);
int IPCheck4Errors(gpacket_t *in_pkt);
int IPCheck4Fragmentation(gpacket_t *in_pkt);
int IPCheck4Redirection(gpacket_t *in_pkt);
int IPProcessMyPacket(gpacket_t *in_pkt);
int UDPProcess(gpacket_t *in_pkt);
int IPOutgoingPacket(gpacket_t *pkt, uchar *dst_ip, int size, int newflag, int src_prot);
int send2Output(gpacket_t *pkt);
int IPVerifyPacket(ip_packet_t *ip_pkt);
int isInSameNetwork(uchar *ip_addr1, uchar *ip_addr2);

int IPSend2Output(gpacket_t *pkt);

#endif
