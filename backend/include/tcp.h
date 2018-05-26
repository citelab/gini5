/**
 * tcp.h (header file for Transmission Control Protocol (TCP))
 *
 * @author Michael Kourlas
 * @date November 9, 2015
 */

#ifndef __TCP_H_
#define __TCP_H_

#include <stdint.h>
#include <endian.h>

#include "ip.h"

/**
 * TCP packet definition adapted from <netinet/tcp.h>.
 */
typedef struct {
	// Source port
	uint16_t	src_port;
	// Destination port
	uint16_t	dst_port;
	// Sequence number
	uint16_t	seq_num;
	uint16_t	ack_num;
#if __BYTE_ORDER == __LITTLE_ENDIAN
	// Unused
	uint8_t		reserved:4;
	// Data offset
	uint8_t		data_offset:4;
#endif
#if __BYTE_ORDER == __BIG_ENDIAN
	// Data offset
	uint8_t		data_offset:4;
	// Unused
	uint8_t		reserved:4;
#endif
	// Flags
	uint8_t		flags;
#define	TCP_FLAG_FIN	0x01
#define	TCP_FLAG_SYN	0x02
#define	TCP_FLAG_RST	0x04
#define	TCP_FLAG_PUSH	0x08
#define	TCP_FLAG_ACK	0x10
#define	TCP_FLAG_URG	0x20
	// Window size
	uint16_t	window;
	// Checksum
	uint16_t	checksum;
	// Urgent pointer
	uint16_t	urp;
} tcp_packet_type;

/**
 * TCP pseudo-header used to calculate checksums.
 */
typedef struct {
	// IP source address
	uint32_t	ip_src;
	// IP destination address
	uint32_t	ip_dst;
	// Reserved
	uint8_t		reserved;
	// IP protocol
	uint8_t		ip_prot;
	// TCP length (in bytes)
	uint16_t	tcp_length;
} tcp_pseudo_header_type;

/**
 * Calculates the TCP checksum for the specified TCP packet.
 *
 * @param ip_packet The IP packet containing the TCP packet.
 *
 * @return The TCP checksum for the specified TCP packet.
 */
uint16_t tcp_checksum(ip_packet_t *ip_packet);

#endif // ifndef __TCP_H_
