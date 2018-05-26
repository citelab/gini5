//=======================================================
//       File Name :  channel.h
//======================================================= 
   #ifndef __CHANNEL_H_
   #define __CHANNEL_H_
   
   #include <stdio.h>
   #include <stdio.h>    
   #include <sys/socket.h>
   #include <arpa/inet.h>  
   #include <stdlib.h>     
   #include <string.h>     
   #include <unistd.h>     
   #include <math.h>
   #include <slack/err.h>
   #include <slack/prog.h>

   #include "gwcenter.h"
   #include "mobility.h"
   #include "mathlib.h"
   #include "antenna.h"
   #include "energy.h"
   #include "propagation.h"
   #include "802_11.h"
   #include "nomac.h"
   #include "mac.h"
   #include "802_11_frame.h"
   #include "timer.h"
   #include "wirelessphy.h"
   #include "llc.h"
   #include "vpl.h"
   #include "event.h"
   #include "errmodel.h"
   #include "awgn.h"
   #include "fading.h"
   #include "wcard.h"
   
   //used in printing the output file
   #define CH_REP_PREFIX  "ch_fad_report" 
   
   char ch_rep_name[MAX_REPORT_NAME_LEN];

//=======================================================
//                                                Functions 
//======================================================= 
    void ChannelProcess (); 
	void PrintChannelFading(double *fad, int i);
    void IniChannel(); 
	void FinalizeChannel();
	void ChannelDelivery(int src_id, int dst_id, WGN_802_11_Mac_Frame *frame) ;
	void KillJamInt (int id);
	void SetJamInt (int id, double interference);
	double GetPropDelay(MobileNode *tx, MobileNode *rx);	
	Prop_type GetPropType();
	void SetPropType(Prop_type type);
	Switch GetRayleighSign();
	void SetRayleighSign(Switch state);
	Switch GetAwgnSign();
	void SetAwgnSign(Switch state);
	Awgn_Mode GetAwgnMode();
	void SetAwgnMode(Awgn_Mode mode);	
	void SetLinkStartTime(WGN_802_11_Mac_Frame *frame, WGNTime link_start_time);
	void SetLinkEndTime(WGN_802_11_Mac_Frame *frame, WGNTime link_end_time);
	void INTTimeoutHandler( MobileNode * node, WGN_802_11_Mac_Frame *frame);
	void LinkStateComp();
    void IniChannelLinkStateMatrix();
#endif
