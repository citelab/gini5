/**
 * openflow_pkt_proc.h - OpenFlow packet processing
 */

#ifndef __OPENFLOW_PKT_PROC_H_
#define __OPENFLOW_PKT_PROC_H_

#include <stdint.h>

#include "message.h"
#include "openflow_defs.h"
#include "packetcore.h"

/**
 * Initializes the OpenFlow packet processor.
 */
void openflow_pkt_proc_init(pktcore_t *core);

/**
 * Processes the specified packet using the OpenFlow packet processor.
 *
 * @param packet The packet to be handled using the OpenFlow packet processor.
 *
 * @return 0, or a negative value if an error occurred.
 */
int32_t openflow_pkt_proc_handle_packet(gpacket_t *packet);

/**
 * Performs the specified action on the specified packet.
 *
 * @param header The action to perform on the packet.
 * @param packet The packet on which the action should be performed.
 *
 * @return 0, or a negative value if an error occurred.
 */
int32_t openflow_pkt_proc_perform_action(ofp_action_header *header,
        gpacket_t *packet);

#endif // ifndef __OPENFLOW_PKT_PROC_H_
