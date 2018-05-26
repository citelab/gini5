/*
 * NAME: gwcenter.c
 * FUNCTION: It contains the main function. It is responsible for system initialization
 *                    and finailization as well.
 * AUTHOR: Sheng Liao
 * DATE:   Revised on Oct 12th, 2005
 */

//=======================================================
//       File Name :  gwcenter.c
//=======================================================
 #include <stdio.h>
 #include <stdio.h>
 #include <sys/socket.h>
 #include <arpa/inet.h>
 #include <stdlib.h>
 #include <string.h>
 #include <unistd.h>
 #include <math.h>
 #include <pthread.h>
 #include <sys/time.h>
 #include <slack/err.h>
 #include <slack/std.h>
 #include <slack/prog.h>
 #include <slack/map.h>


#include "gwcenter.h"
#include "mobility.h"
#include "mathlib.h"
#include "antenna.h"
#include "energy.h"
#include "channel.h"
#include "propagation.h"
#include "802_11.h"
#include "nomac.h"
#include "mac.h"
#include "802_11_frame.h"
#include "timer.h"
#include "wirelessphy.h"
#include "llc.h"
#include "event.h"
#include "cli.h"
#include "errmodel.h"
#include "awgn.h"
#include "fading.h"
#include "wcard.h"

wgn_config wgnconfig =  {MaxNodeNo, 1, NULL};

// command parsing table
Option wgn_optab[] =
{
	{
		"nodenumber", 'n', "integer", "Specify the total mobile node number [compulsary]",
		required_argument, OPT_INTEGER, OPT_VARIABLE, &(wgnconfig.tot_node_no)
	},
	{
		"interactive", 'i', "0 or 1", "CLI on for interactive mode (daemon otherwise) [optional]",
		required_argument, OPT_INTEGER, OPT_VARIABLE, &(wgnconfig.cli_flag)
	},
	{
		"config", 'c', "path", "Specify the configuration file path and name [optional]",
		required_argument, OPT_STRING, OPT_VARIABLE, &(wgnconfig.config_file)
	},
	{
		"vsdirectory", 'd', "path", "Specify the directory to place the virtual switches [optional]",
		required_argument, OPT_STRING, OPT_VARIABLE, &(wgnconfig.vs_directory)
	},
	{
		NULL, '\0', NULL, NULL, 0, 0, 0, NULL
	}
};

Options options[1] = {{ prog_options_table, wgn_optab }};

int main(int argc, char *argv[]) {
	WGNTime tmp_time;

	//initialization of the whole system by default
    IniSystem(argc, argv);

	//initialization of the virtual networks
	IniNetworkNode();
	IniChannel();

	//initialize the system following the configuration file and pump up the cmd shell
	IniCli();

	while(1) {
       // current time is the execution time for some event(s).
	   if ((SYSTEM_TIME.tv_sec == timeOutTime.tv_sec) && (SYSTEM_TIME.tv_nsec == timeOutTime.tv_nsec)) {
            //update the system time.
			tmp_time = SYSTEM_TIME;
			SYSTEM_TIME.tv_nsec = SYSTEM_TIME.tv_nsec + 1;
		    if (SYSTEM_TIME.tv_nsec == NFACTOR) {
			    SYSTEM_TIME.tv_sec = SYSTEM_TIME.tv_sec + 1;
			    SYSTEM_TIME.tv_nsec = 0;
				//update the mobility and the channel states.
			    MobilityProcess();
			    ChannelProcess();
		    }
			//keep executing all the events that happen at this moment.
			while ((tmp_time.tv_sec == timeOutTime.tv_sec) && (tmp_time.tv_nsec == timeOutTime.tv_nsec)) {
					  EventHandler();
			}
       }
	   else {
		    //update the system time.
			SYSTEM_TIME.tv_nsec = SYSTEM_TIME.tv_nsec + 1;
		    if (SYSTEM_TIME.tv_nsec == NFACTOR) {
			    SYSTEM_TIME.tv_sec = SYSTEM_TIME.tv_sec + 1;
			    SYSTEM_TIME.tv_nsec = 0;
				//update the mobility and the channel states.
			    MobilityProcess();
			    ChannelProcess();
			}
	   }
	}
	return 0;
}

//=======================================================
//       FUNCTION: IniInput
//       PURPOSE:  Initialize the parameters of the whole system
//=======================================================
   void IniInput() {
	    int i;

		if (prog_verbosity_level()==3){
			printf("[IniInput]:: Initialize the system parameters ... ");
		}
		//shared variables
		TotNodeNo = wgnconfig.tot_node_no;
		oscnum = 5;
        pathlossexp = 2.0;
        dev_db = 3.0;
		modulation = DSSS;
		macType = DCF_802_11;
        prop_type = FreeSpace;
		RayleighSign = OFF;
		AwgnSign = OFF;
        dist0 = 1;
		X_Width = 75;
        Y_Width = 75;
        Z_Width = 0;
        PrintChFadSign =  FALSE;
		PrintEventSign = FALSE;
		noise = -140;    //db
		awgn_mode = SNR;
		snr_Eb_N0 = 12;

		//independent variables
        for ( i=0; i<TotNodeNo; i++) {
			   PrintMovArray[i] = FALSE;
			   MaxSpdArray[i] = 5;
               MinSpdArray[i] = 1;
               MobilityTypeArray[i] = RandomWayPoint;
			   AntHeightArray[i] = 1;
			   AntTypeArray[i] = OmniDirectionalAnt;
			   AntSysLosArray[i] = 1;
		  	   EnPowSwitchArray[i] = ON;
			   EnPSMArray[i] = OFF;
			   TotalEnergyArray[i] = 100;
			   WCardTypeArray[i] = SampleCard;
			   TxProbArray[i] = 0.1;
	    }

		//test variables
        Ch_TimeUnit = 1;                                   //time space to update channel status		  (sec)
		Ch_update_remain = 0;
        Mob_TimeUnit = 1;                                //time space to update the mobility status   (sec)
		Mob_update_remain = 0;

		if (prog_verbosity_level()==3){
			printf("[ OK ]\n");
		}
   }

//=======================================================
//       FUNCTION: IniNetworkNode
//       PURPOSE:  Initialize all nodes in the network.
//=======================================================
  void IniNetworkNode() {
	    if (prog_verbosity_level()==1){
			PrintSystemInfo ("Initializing the network node of wireless GINI ... ");
		}
	   IniMobNode();
  }

//=======================================================
//       FUNCTION: FinalizeNetworkNode
//=======================================================
  void FinalizeNetworkNode() {
	   FinalizeMobNode();
  }

//=======================================================
//       FUNCTION: IniMobNode
//       PURPOSE:  Initialize the normal mobile nodes.
//=======================================================
  void IniMobNode() {
	  //PrintSystemInfo ("Initializing the mobile node... ");
	  MobNodPtrAarry=(MobileNode *)malloc(TotNodeNo*sizeof(MobileNode));
	  if( MobNodPtrAarry == NULL ){
		  printf("[IniMobNode]:: MobNodPtrAarry malloc error! \n");
		  exit(1);
	  }
	  IniNodeID(NORMAL);
	  IniNodeType(NORMAL);
	  IniNodePhy(NORMAL);
	  IniNodeMac(NORMAL);
      IniNodeLlc(NORMAL);
	  IniNodeStats(NORMAL);
}

//=======================================================
//       FUNCTION: FinalizeMobNode
//=======================================================
  void FinalizeMobNode() {
	  PrintSystemInfo ("Finalizing the mobile node... ");
	  FinalizeNodeLlc(NORMAL);
	  FinalizeNodeMac(NORMAL);
	  FinalizeNodePhy(NORMAL);
	  FinalizeNodeStats(NORMAL);
	  free(MobNodPtrAarry);
}

//=======================================================
//       FUNCTION: IniNodeID
//       PURPOSE:  Initialize the time management parameters of all nodes..
//=======================================================
   void IniNodeID(NodeType type) {
	    NodeId id;
		if (type == NORMAL) {
			for ( id=1; id<=TotNodeNo; id++) {
                    WGNnode(id)->Id = id;
		    }
		}
   }

//=======================================================
//       FUNCTION: IniNodeType
//       PURPOSE:  Initialize the node type.
//=======================================================
   void IniNodeType(NodeType type) {
	    NodeId id;
		for ( id=1; id<=TotNodeNo; id++) {
                WGNnode(id)->nodeType = type;
		}
   }

//=======================================================
//       FUNCTION:   IniIDToAddrMap
//=======================================================
   void IniAddrToIDMap() {
   	   int i,id;
	   //int j;
       AddrToIDMap = (AddrToIDEntry *)malloc(TotNodeNo*sizeof(AddrToIDEntry));
	   //add the value for the entry
	   for (i=0; i<TotNodeNo; i++) {
			 id = i+1;
			 //initialize the node mac addr
			 mac_addr_array[i].addr[0] = 0xFE;
			 mac_addr_array[i].addr[1] = 0xFD;
			 mac_addr_array[i].addr[2] = 0;
			 mac_addr_array[i].addr[3] = 0;
			 mac_addr_array[i].addr[4] = 0;
			 mac_addr_array[i].addr[5] = id;
		     AddrToIDMap[i].id = id;
	   	     memcpy(AddrToIDMap[i].mac_addr, mac_addr_array[i].addr, MAC_ADDR_LEN);
	   }
   }

//=======================================================
//       FUNCTION:   IniIDToAddrMap
//=======================================================
   void FinalizeAddrToIDMap() {
       free(AddrToIDMap);
   }

//=======================================================
//       FUNCTION: IniSystem
//=======================================================
   void IniSystem(int argc, char *argv[]) {
	    int i;

		SYS_INFO = (Sys_Info *)malloc(sizeof(Sys_Info));

	    //setup the basic software information
		if (argc != 0) {
			IniProgram(argc, argv);
		}

		if (prog_verbosity_level()==3){
			PrintSystemInfo ("Initializing the basic system information of wireless GINI ... ");
		}
        //initialize the input parameters
        IniInput();
        //initialize the event queue
	    IniEvent();

        //***********************MAC PART*********************
		if (prog_verbosity_level()==3){
			printf("[IniSystem]:: Initialize the basic mac layer information of the system ... ");
		}
		//initialize mac address	to node id table
		IniAddrToIDMap();
		//broadcast mac addr
		for (i=0; i<MAC_ADDR_LEN; i++) {
	          MAC_BROADCAST_ADDR[i] = 0xff;
        }
		//initialize the mac info in the sys inof
		SYS_INFO->mac_info = (MacMib *)malloc(sizeof(MacMib));
        //set values
		//dcf
		SYS_INFO->mac_info->macType = macType;
	    SYS_INFO->mac_info->MAC_RTSThreshold = 0;		     // bytes
        SYS_INFO->mac_info->MAC_ShortRetryLimit = 7;
        SYS_INFO->mac_info->MAC_LongRetryLimit = 4;
	    SYS_INFO->mac_info->MAC_Data_Frame_Header_Length = 30;
	    SYS_INFO->mac_info->MAC_RTS_Frame_Header_Length = 16;
	    SYS_INFO->mac_info->MAC_CTS_Frame_Header_Length = 10;
	    SYS_INFO->mac_info->MAC_ACK_Frame_Header_Length = 10;
	    SYS_INFO->mac_info->MAC_Frame_Tailer_Length = 4;
		if (prog_verbosity_level()==3){
			printf("[ OK ]\n");
		}

		//***********************PHY PART*********************
		if (prog_verbosity_level()==3){
			printf("[IniSystem]:: Initialize the basic phyical layer information of the system ... ");
		}
		SYS_INFO->phy_info = (PhyMib *)malloc(sizeof(PhyMib));
		if (modulation == DSSS) {
		    SYS_INFO->phy_info->PreambleLength = DSSS_PreambleLength;
            SYS_INFO->phy_info->PLCPHeaderLength = DSSS_PLCPHeaderLength;

			//set some global variable
			SetDataHdrLen();
			SetRTSLen();
			SetCTSLen();
			SetACKLen();

		    SYS_INFO->phy_info->CWMin = DSSS_CWMin;
            SYS_INFO->phy_info->CWMax = DSSS_CWMax;
            SYS_INFO->phy_info->SlotTime = DSSS_SlotTime;                                      //seconds
            SYS_INFO->phy_info->CCATime = DSSS_CCATime;	                                     //seconds
            SYS_INFO->phy_info->RxTxTurnaroundTime = DSSS_RxTxTurnaroundTime;	                 //seconds
            SYS_INFO->phy_info->SIFSTime = DSSS_SIFSTime;                                    //seconds
	        SYS_INFO->phy_info->PIFSTime = DSSS_SIFSTime + DSSS_SlotTime;                                    //seconds
	        SYS_INFO->phy_info->DIFSTime = DSSS_SIFSTime + DSSS_SlotTime*2;                                    //seconds
			SYS_INFO->phy_info->EIFSTime = SYS_INFO->phy_info->SIFSTime +
				                                                          SYS_INFO->phy_info->DIFSTime +
			                                                              PHY_ACK_LEN*8/1000000.0;                                    //seconds
		}
		else {
            printf ("(): The other modulation method than DSSS is not implemented at this moment.\n");
		}
		if (prog_verbosity_level()==3){
			printf("[ OK ]\n");
		}

		//**************************TIME PART*************************
		if (prog_verbosity_level()==3){
			printf("[IniSystem]:: Initialize the basic time information of the system ... ");
		}
		SYS_INFO->time_info	 = (TimeMib *)malloc(sizeof(TimeMib));
		SYS_INFO->time_info->Ch_timeunit = Ch_TimeUnit;
		SYS_INFO->time_info->Mob_timeunit = Mob_TimeUnit;
		//ini time
	    SYSTEM_TIME.tv_sec = 0;
        SYSTEM_TIME.tv_nsec = 1;
	    timeOutTime.tv_sec = 0;
	    timeOutTime.tv_nsec = 0;
		if (prog_verbosity_level()==3){
			printf("[ OK ]\n");
		}

		//**************************MAP PART*************************
		if (prog_verbosity_level()==3){
			printf("[IniSystem]:: Initialize the basic map information of the system ... ");
		}
		SYS_INFO->map_info = (MapMib *)malloc(sizeof(MapMib));
		SYS_INFO->map_info->x_width = X_Width;
        SYS_INFO->map_info->y_width = Y_Width;
		SYS_INFO->map_info->z_width = Z_Width;
		if (prog_verbosity_level()==3){
			printf("[ OK ]\n");
		}
   }

void IniProgram(int ac, char *av[]) {
	int i, sign, nodenum;
	sign = 0;
	char cmd[50];

	if (getenv("GINI_HOME") == NULL) {
	    printf("[IniProgram] :: Error, you should set the $GINI_HOME value before you start wireless GINI!\n");
		exit(1);
	}

	//software information
	prog_init();
	prog_set_syntax("[options] arg ... ");
	prog_set_options(options);
	prog_set_version("Beta 1.0");
	prog_set_date("09/12/2005");
	prog_set_author("Mahes <maheswar@cs.mcgill.ca>, Sheng Liao <lsheng1@cs.mcgill.ca>");
	prog_set_contact(prog_author());
	prog_set_url("http://www.cs.mcgill.ca/~anrl/gini/");
	prog_set_desc("Wireless GINI - a component of the GINI toolkit.");

	//prog_set_verbosity_level(1);
	prog_opt_process(ac, av);

	//check the input command. "-n" can not be absent.
	for (i=0; i<ac; i++) {
		  if (!strcmp(av[i], "-n")) {
			  sign = 1;
			  nodenum = atoi(av[i+1]);
			  if (nodenum<=0) {
				  printf("[IniProgram]:: Error, the total number of the mobile node should be greater than zero.\n");
				  exit(1);
			  }
			  break;
		  }
	}
	if (sign == 0) {
		strcpy(cmd,av[0]);
		strcat(cmd," --help");
		system(cmd);
		exit(1);
	}
}

void ReloadWGN() {
	int verbose;
	verbose = prog_verbosity_level();
	prog_set_verbosity_level(0);
	//Finalization
	printf("[ReloadWGN]:: Finalizing the system ...  \n");
	FinalizeChannel();
	FinalizeNodeStats(NORMAL);
	FinalizeNodeMac(NORMAL);
	FinalizeNodePhy(NORMAL);
	FinalizeSystem();
	printf("[ReloadWGN]:: Rebooting the system ...  \n");
	//reboot the system
	IniSystem(0, NULL);
	IniNodePhy(NORMAL);
	IniNodeMac(NORMAL);
	IniNodeStats(NORMAL);
	IniChannel();
	prog_set_verbosity_level(verbose);
}

//=======================================================
//       FUNCTION: IniSystem
//=======================================================
   void FinalizeSystem() {
		if (prog_verbosity_level()==3){
			printf("[FinalizeSystem]:: Finalize the basic information of the system ... ");
		}
	    FinalizeEvent();
		FinalizeAddrToIDMap();
		free(SYS_INFO->mac_info);
		free(SYS_INFO->phy_info);
		free(SYS_INFO->time_info);
		free(SYS_INFO->map_info);
		free(SYS_INFO);
		if (prog_verbosity_level()==3){
			printf("[ OK ]\n");
		}
   }
