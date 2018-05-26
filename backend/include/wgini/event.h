//=======================================================
//       File Name :  event.h
//======================================================= 
   #ifndef __EVENT_H_
   #define __EVENT_H_   

   #include <stdio.h>
   #include <stdio.h>      
   #include <sys/socket.h> 
   #include <arpa/inet.h>  
   #include <stdlib.h>     
   #include <string.h>     
   #include <unistd.h>     
   #include <math.h>
   #include <pthread.h>
   #include <slack/prog.h>

   #include "gwcenter.h"
   #include "mobility.h"
   #include "mathlib.h"
   #include "antenna.h"
   #include "energy.h"
   #include "channel.h"
   #include "propagation.h"
   #include "802_11_frame.h"
   #include "nomac.h"
   #include "csma.h"
   #include "mac.h"
   #include "timer.h"
   #include "wirelessphy.h"
   #include "llc.h"
   #include "vpl.h"
   #include "errmodel.h"
   #include "awgn.h"
   #include "fading.h"
   #include "wcard.h"
   
	#define EVE_REP_PREFIX  "sys_event_report"    

	char eve_rep_name[MAX_REPORT_NAME_LEN];

    WGNflag EventQIsEmpty(); 
    WGNEvent* GenNewEvent(NodeId id, Event_type type,WGNTime time, void *eveObject,
		                                           WGNEvent *nextEventPtr); 
    WGNEvent* AddNewEventToList(NodeId id, Event_type type,WGNTime time, void *object);
	void IniEvent();
	void EventDelete();
    WGNflag EventDestroy(NodeId id, Event_type type);
    void EventHandler();
	void EventPrint(WGNEvent* eve , char* do_what);
	void PrintCurTime ();
	void PrintEarliestEveTime();
	void PrintMacAddr (char* type, unsigned char *mac_addr);
	void PrintIPAddr (char* type, unsigned char *ip_addr);
	void PrintEventList();
	void EventListFilePrint();
	void EventFilePrint(WGNEvent* eve , char* do_what);
	void PrintProt (unsigned char *prot);
	void PrintSystemInfo (char *info);
	void PrintDebugInfo (char *info);
	void PrintLine();
	void FinalizeEvent();

	#endif
