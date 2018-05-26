/*
 * devicedefs.h (header for device definitions)
 * AUTHOR: Muthucumaru Maheswaran
 * DATE: December 28, 2004
 * VERSION: Beta
 */

#ifndef __DEVICEDEFS_H__
#define __DEVICEDEFS_H__


// These are device names... not all are defined!
#define ETHERNET_DEVICE		"eth"
#define TAP_DEVICE		"tap"
#define TUN_DEVICE              "tun"
#define WIRELESS_LAN_DEVICE	"wlan"
#define PPP_DEVICE		"ppp"
#define TOKEN_RING_DEVICE	"tr"
#define AMATEUR_RADIO_DEVICE	"ax"
#define SLIP_DEVICE		"sl"
#define PARALLEL_LINE_DEVICE	"plip"
#define RAW_DEVICE              "raw"

#define LIST_OF_DEVICES   devicedirectory_t devdir[] = { \
	{  \
		ETHERNET_DEVICE, \
		"ETHERNET DEVICE DRIVER", \
		fromEthernetDev, \
		toEthernetDev, \
	}, \
	{ \
		TAP_DEVICE, \
		"TAP DEVICE DRIVER", \
		fromTapDev, \
		toTapDev, \
	}, \
        { \
		TUN_DEVICE, \
		"TUNNEL DEVICE DRIVER", \
		fromTunDev, \
		toTunDev, \
	}, \
        { \
		RAW_DEVICE, \
		"RAW DEVICE DRIVER", \
		fromRawDev, \
		toRawDev, \
	} \
}


#endif //__DEVICEDEFS_H__
