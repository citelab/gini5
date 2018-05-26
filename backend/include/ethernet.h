/*
 * ethernet.h (header file the Ethernet driver)
 * AUTHOR: Muthucumaru Maheswaran
 *
 * VERSION:
 */



/*
 * function prototypes
 */

int findPacketSize(pkt_data_t *pkt);

void *toEthernetDev(void *arg);
void* fromEthernetDev(void *arg);
