//=======================================================
//                              File Name :  802_11_frame.h
//======================================================= 
 #ifndef __802_11_FRAME_H_
 #define __802_11_FRAME_H_
 
 #include <stdio.h>
 #include <stdio.h>     
 #include <sys/socket.h> 
 #include <arpa/inet.h>  
 #include <stdlib.h>     
 #include <string.h>   
 #include <unistd.h>     
 #include <math.h>
 #include <pthread.h>

 #include "gwcenter.h"
 #include "mobility.h"
 #include "mathlib.h"
 #include "antenna.h"
 #include "energy.h"
 #include "channel.h"
 #include "propagation.h"
 #include "802_11.h"
 #include "timer.h"
 #include "wirelessphy.h"
 #include "llc.h"
 #include "vpl.h"
 #include "event.h"
 #include "nomac.h"
 #include "mac.h"
 #include "errmodel.h"
 #include "awgn.h"
 #include "fading.h"
 #include "wcard.h"

//=======================================================
//                                                  Functions
//=======================================================  
	void set_fc_protocol_version(WGN_802_11_Mac_Pseudo_Frame_Control *fc, int version);
	void set_fc_type(WGN_802_11_Mac_Pseudo_Frame_Control *fc , int type);
	void set_fc_subtype(WGN_802_11_Mac_Pseudo_Frame_Control *fc , int subtype);
    void set_fc_to_ds(WGN_802_11_Mac_Pseudo_Frame_Control *fc , int flag); 
	void set_fc_from_ds(WGN_802_11_Mac_Pseudo_Frame_Control *fc , int flag); 
	void set_fc_more_frag(WGN_802_11_Mac_Pseudo_Frame_Control *fc , int flag);
    void set_fc_retry(WGN_802_11_Mac_Pseudo_Frame_Control *fc , int flag); 
	void set_fc_pwr_mgt(WGN_802_11_Mac_Pseudo_Frame_Control *fc , int flag);
	void set_fc_more_data(WGN_802_11_Mac_Pseudo_Frame_Control *fc , int flag);
	void set_fc_wep(WGN_802_11_Mac_Pseudo_Frame_Control *fc , int flag);
	void set_fc_order(WGN_802_11_Mac_Pseudo_Frame_Control *fc , int flag); 
    void Set_WGN_802_11_Mac_Pseudo_Frame_Control(WGN_802_11_Mac_Pseudo_Frame_Control* fc, WGN_802_11_Mac_Frame_Type frame_type); 
    void  Set_WGN_802_11_Mac_Pseudo_Sequence_Control (MobileNode *node, WGN_802_11_Mac_Pseudo_Sequence_Control* sc);
    void UpdateSeqNumber(MobileNode *node); 
    int GetSeqNumber(MobileNode *node);
	int GetFctype(WGN_802_11_Mac_Frame *p);
	int GetFcSubtype(WGN_802_11_Mac_Frame *p);
	unsigned int GetDuration(WGN_802_11_Mac_Frame *p);
	char *GetSa(WGN_802_11_Mac_Frame *p);
	char *GetDa(WGN_802_11_Mac_Frame *p);
	char *GetTa(WGN_802_11_Mac_Frame *p);
	char *GetRa(WGN_802_11_Mac_Frame *p); 
	unsigned char *Dot_3_GetDa(WGN_802_3_Mac_Frame *p); 
	unsigned char *Dot_3_GetSa(WGN_802_3_Mac_Frame *p);
    double FrameTimeComp(MobileNode *node, int length, Pkt_Unit unit); 
	double TX_Time(MobileNode *node);
	double RX_Time(MobileNode *node); 
	double Frame_Time(MobileNode *node, WGN_802_11_Mac_Frame *frame); 
    void SetDataHdrLen(); 
    void SetRTSLen(); 
    void SetCTSLen();
    void SetACKLen();
    void SetRTSTime(double bandwidth);
    void SetCTSTime(double bandwidth); 
    void SetACKTime(double bandwidth); 
    void SetWaitCTSTimeout();
    double GetWaitACKTimeout(MobileNode *node); 
    int  RTS_DURATION (MobileNode *node);
    int  CTS_DURATION(unsigned int rts_duration);
    int  DATA_DURATION(); 
    int  ACK_DURATION();
    void Mac_802_11_RTS_Frame( MobileNode *node, unsigned char *ra, unsigned char *ta); 
    void Mac_802_11_CTS_Frame( MobileNode *node, unsigned int rts_duration, unsigned char *ra); 
    void Mac_802_11_ACK_Frame(MobileNode *node, unsigned char *ra); 
    //void Mac_802_11_Data_Frame(MobileNode *node, WGN_802_3_Mac_Frame *dot_3_frame); 
    //void Set_802_11_Data_Frame_Addr (MobileNode *node, WGN_802_11_Mac_Pseudo_Header *hdr, char *SA, char *DA); 
    int Get_Payload_Length (WGN_802_3_Mac_Frame *dot_3_frame);
	void Dot11FrameFree(WGN_802_11_Mac_Frame *frame);
	void Dot3FrameFree(WGN_802_3_Mac_Frame *frame);

#endif
