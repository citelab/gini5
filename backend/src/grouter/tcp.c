/**
 * tcp.c (Transmission Control Protocol (TCP))
 *
 * @author Michael Kourlas
 * @date November 9, 2015
 */

#include "grouter.h"
#include "ip.h"

#include "tcp.h"
#include <arpa/inet.h>


/**
 * Calculates the TCP checksum for the specified TCP packet.
 *
 * @param ip_packet The IP packet containing the TCP packet.
 *
 * @return The TCP checksum for the specified TCP packet.
 */
uint16_t tcp_checksum(ip_packet_t *ip_packet)
{
	// Derive TCP packet from IP packet and reset checksum
	tcp_packet_type *tcp_packet = (tcp_packet_type *)
		(ip_packet + (ip_packet->ip_hdr_len * 4));
	tcp_packet->checksum = 0;

	// Create TCP pseudo-header
	uint16_t tcp_len = ip_packet->ip_pkt_len - ip_packet->ip_hdr_len * 4;
	tcp_pseudo_header_type pseudo_header;
	COPY_IP(&pseudo_header.ip_src, ip_packet->ip_src);
	COPY_IP(&pseudo_header.ip_dst, ip_packet->ip_dst);
	pseudo_header.reserved = 0;
	pseudo_header.ip_prot = ip_packet->ip_prot;
	pseudo_header.tcp_length = tcp_len;

	// Calculate sums of pseudo-header and TCP packet (same as taking one's
	// complement of checksum) and store in temporary buffer
	uint16_t buf[3];
	buf[0] = ~checksum((uint8_t *) &pseudo_header,
					   sizeof(tcp_pseudo_header_type) / 2);
	buf[1] = ~checksum((uint8_t *) &tcp_packet, ntohs(tcp_len) / 2);
	// If TCP packet length is odd, store zero-padded last byte in temporary
	// buffer as well
	if (tcp_len % 2 != 0)
	{
		uint8_t *temp = (uint8_t *) (tcp_packet + ntohs(tcp_len) - 1);
		buf[2] = *temp << 8;
	}
	else
	{
		buf[2] = 0;
	}

	// Find checksum of the sums (plus the last byte, if applicable)
	return checksum((uint8_t *) &buf, 3);
}
