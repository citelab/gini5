/*
 * NAME: stats.c 
 * FUNCTION: Collection of functions to provide the statistical support.
 * AUTHOR: Sheng Liao
 * DATE:   Revised on Oct 12th, 2005
 */


//=======================================================
//       File Name :  stats.c
//======================================================= 
    #include "stats.h"

//=======================================================
//       FUNCTION: IniNodeStats
//       PURPOSE:  Initialize the node statistics parameters. 
//======================================================= 
   void IniNodeStats(NodeType type) { 
	    int i;
		//printf("Initializing statistical parameters... \n");
	   ThroutputComSign = FALSE;	
		
		//used to generate the statistical output file name
		for (i=0; i<TotNodeNo; i++) {
		     FileSeqArray[i] = 1;
			 MobSeqArray[i] = 1;
		}

        if (type == NORMAL) { 
			for ( i=0; i<TotNodeNo; i++) {
				    WGNnode(i+1)->nodeStats = (NodeStats *)malloc(sizeof(NodeStats));
		            if(WGNnode(i+1)->nodeStats == NULL){
		               printf("[IniNodeStats]:: nodeStats malloc error.\n");
		               exit(1);
		            }	       
					WGNnode(i+1)->nodeStats->BroadcastTx = 0;	  
					WGNnode(i+1)->nodeStats->UnicastTx = 0;     	
					WGNnode(i+1)->nodeStats->RtsTxed = 0;			 
					WGNnode(i+1)->nodeStats->CtsTxed = 0;			   
					WGNnode(i+1)->nodeStats->DataTxed = 0;		
					WGNnode(i+1)->nodeStats->AckTxed = 0;	
					WGNnode(i+1)->nodeStats->TotPktTxed = 0;
					
					//retransmission stuff
					WGNnode(i+1)->nodeStats->ReTxPktNum = 0;	 
					WGNnode(i+1)->nodeStats->ReTxRtsNum = 0;	
					WGNnode(i+1)->nodeStats->ReTxNum = 0;	

					//recording error stuff
					WGNnode(i+1)->nodeStats->DropForExMaxRtsRetryNo = 0;
					WGNnode(i+1)->nodeStats->DropForExMaxPktRetryNo = 0;
					WGNnode(i+1)->nodeStats->DropForExMaxRetryNo = 0;

					//before take a look at the content of the pkt
					WGNnode(i+1)->nodeStats->DropForInTx = 0;                            //recv packet when the node is sending
					WGNnode(i+1)->nodeStats->DropForCollision = 0;	
					WGNnode(i+1)->nodeStats->RtsDropForCollision = 0;
					WGNnode(i+1)->nodeStats->CtsDropForCollision = 0;
					WGNnode(i+1)->nodeStats->AckDropForCollision = 0;
					WGNnode(i+1)->nodeStats->DataDropForCollision = 0;
					WGNnode(i+1)->nodeStats->DropForLowRxPwr = 0;
					WGNnode(i+1)->nodeStats->TotPktErrorDrop = 0;

					//recording the pkt accepted correctly
					WGNnode(i+1)->nodeStats->TotPktRxed = 0;	
					WGNnode(i+1)->nodeStats->PktSucRxed = 0;	
					WGNnode(i+1)->nodeStats->NotForMeRxed = 0;
					WGNnode(i+1)->nodeStats->RtsRxed = 0; 
					WGNnode(i+1)->nodeStats->CtsRxed = 0;
					WGNnode(i+1)->nodeStats->DataRxed = 0;
					WGNnode(i+1)->nodeStats->AckRxed = 0;

					//about capture function
  					WGNnode(i+1)->nodeStats->AptCaptureNo = 0;                         //accept for the capture

					//about rate stuff
				   WGNnode(i+1)->nodeStats->RtsReTranRate	= 0;
				   WGNnode(i+1)->nodeStats->DataReTranRate = 0;
                   WGNnode(i+1)->nodeStats->ReTranRate = 0;
				   WGNnode(i+1)->nodeStats->RecvColErrorDropRate = 0;
				   WGNnode(i+1)->nodeStats->RecvWhileTxErrorDropRate = 0;
				   WGNnode(i+1)->nodeStats->RecvNoiseErrorDropRate = 0;
				   WGNnode(i+1)->nodeStats->RecvLowPwrErrorDropRate = 0;
				   WGNnode(i+1)->nodeStats->RecvErrorDropRate = 0;
				   WGNnode(i+1)->nodeStats->RecvDropRate = 0;     //including the packets which are not for me
	               WGNnode(i+1)->nodeStats->RecvColRate = 0;

				   //for sepecial purpose
				   WGNnode(i+1)->nodeStats->TotTxByteNo = 0;
	               WGNnode(i+1)->nodeStats->LToMBufDrop = 0;
	               WGNnode(i+1)->nodeStats->LToUBufDrop = 0;
		    }
		}
   }

//=======================================================
//       FUNCTION: FinalizeNodeStats
//======================================================= 
   void FinalizeNodeStats(NodeType type) { 
	    int i;
		//printf("Finalizing statistical parameters... \n");
        if (type == NORMAL) { 
			for ( i=0; i<TotNodeNo; i++) {
				    free(WGNnode(i+1)->nodeStats);
            }
		}
   }

//=======================================================
//       FUNCTION:  StatsPrintOut
//=======================================================
	void StatsPrintOut(int id, char* file) {
	   FILE* in;  
       
	   in = fopen(file, "a+");
       if (in==NULL) {
	       printf ("[StatsPrintOut]:: Error, can't create the file.\n");
           return;
       } 
	  
	   fprintf (in, "\n================================================================");
	   fprintf (in, "\nSENDING PACKETS INFORMATION OF NODE %d.", id);
	   fprintf (in, "\n================================================================");
	   fprintf (in, "\nGENERAL SENDING PACKETS INFORMATION.");
	   fprintf (in, "\n================================================================");
       fprintf (in, "\nThe number of the BROADCAST packets have been sent is:    %ld ", WGNnode(id)->nodeStats->BroadcastTx);
	   fprintf (in, "\nThe number of the UNICAST packets have been sent is:    %ld ", WGNnode(id)->nodeStats->UnicastTx);
	   fprintf (in, "\n================================================================");
	   fprintf (in, "\nCLASSIFIED SENDING PACKETS INFORMATION.");
	   fprintf (in, "\n================================================================");
	   fprintf (in, "\nThe number of the RTS packets have been sent is:    %ld ", WGNnode(id)->nodeStats->RtsTxed);
	   fprintf (in, "\nThe number of the CTS packets have been sent is:    %ld ", WGNnode(id)->nodeStats->CtsTxed);
	   fprintf (in, "\nThe number of the DATA packets have been sent is:    %ld ", WGNnode(id)->nodeStats->DataTxed);
	   fprintf (in, "\nThe number of the ACK packets have been sent is:    %ld ", WGNnode(id)->nodeStats->AckTxed);
	   fprintf (in, "\n================================================================");
	   fprintf (in, "\nThe TOTAL number of the packets have been sent is:    %ld ", WGNnode(id)->nodeStats->TotPktTxed);
	   fprintf (in, "\n================================================================");

	   fprintf (in, "\n\n\n\n================================================================");
	   fprintf (in, "\nSENDING PACKETS RETRY INFORMATION OF NODE %d. ", id);
	   fprintf (in, "\n================================================================");
	   fprintf (in, "\nThe DATA PACKET RETRY TIMES number is:    %ld ", WGNnode(id)->nodeStats->ReTxPktNum);
	   fprintf (in, "\nThe RTS PACKET RETRY TIMES number is:    %ld ", WGNnode(id)->nodeStats->ReTxRtsNum);
	   fprintf (in, "\n================================================================");

	   fprintf (in, "\n\n\n\n================================================================");
	   fprintf (in, "\nSENDING PACKETS INFORMATION OF NODE %d. ", id);
	   fprintf (in, "\n================================================================");
	   fprintf (in, "\nThe number of the packet DROPED FOR EXCEEDING THE MAX RTS RETRY VALUE is:    %ld ", WGNnode(id)->nodeStats->DropForExMaxRtsRetryNo);
	   fprintf (in, "\nThe number of the packet DROPED FOR EXCEEDING THE MAX DATA RETRY VALUE is:    %ld ", WGNnode(id)->nodeStats->DropForExMaxPktRetryNo);
       fprintf (in, "\n================================================================");
	   fprintf (in, "\nThe TOTAL number of the packet DROPED FOR FAILURE OF RETRANSMISSION is:    %ld ", WGNnode(id)->nodeStats->DropForExMaxRetryNo);
	   fprintf (in, "\n================================================================");

	   fprintf (in, "\n\n\n\n================================================================");
	   fprintf (in, "\nDROPING INFORMATION OF THE PACKETS RECEIVED BY NODE %d. ", id);
	   fprintf (in, "\n================================================================");
	   fprintf (in, "\nThe number of the received packet DROPED FOR TRANSMITTING AT THE SAME TIME is:    %ld ", WGNnode(id)->nodeStats->DropForInTx);
	   fprintf (in, "\nThe number of the received packet DROPED FOR COLLISION is:    %ld ", WGNnode(id)->nodeStats->DropForCollision);
	   fprintf (in, "\nThe number of the received  RTS packet DROPED FOR COLLISION is:    %ld ", WGNnode(id)->nodeStats->RtsDropForCollision);
	   fprintf (in, "\nThe number of the received  CTS packet DROPED FOR COLLISION is:    %ld ", WGNnode(id)->nodeStats->CtsDropForCollision);
	   fprintf (in, "\nThe number of the received  ACK packet DROPED FOR COLLISION is:    %ld ", WGNnode(id)->nodeStats->AckDropForCollision);
	   fprintf (in, "\nThe number of the received  DATA packet DROPED FOR COLLISION is:    %ld ", WGNnode(id)->nodeStats->DataDropForCollision);
	   fprintf (in, "\nThe number of the received packet DROPED FOR LOW RECV POWER is:    %ld ", WGNnode(id)->nodeStats->DropForLowRxPwr);
	   fprintf (in, "\nThe number of the received packet DROPED FOR NOISE ERROR is:    %ld ", WGNnode(id)->nodeStats->DropForNoiseErr);
	   fprintf (in, "\n================================================================");
	   fprintf (in, "\nThe TOTAL number of the received packet DROPED by ERROR is:    %ld ", WGNnode(id)->nodeStats->TotPktErrorDrop);
	   fprintf (in, "\n================================================================");
       
	   fprintf (in, "\n\n\n\n================================================================");
	   fprintf (in, "\nGENERAL INFORMATION OF THE PACKETS RECEIVED BY NODE %d. ", id);
	   fprintf (in, "\n================================================================");
	   fprintf (in, "\nThe TOTAL number of the packet received is:    %ld ", WGNnode(id)->nodeStats->TotPktRxed);
	   fprintf (in, "\nThe number of the packet received CORRECTLY is:    %ld ", WGNnode(id)->nodeStats->PktSucRxed);
	   fprintf (in, "\nThe number of the packet received NOT FOR ITSELF is:    %ld ", WGNnode(id)->nodeStats->NotForMeRxed);
	   fprintf (in, "\n================================================================");
	   fprintf (in, "\nCLASSIFIED INFORMATION OF THE PACKETS RECEIVED BY NODE %d.", id);
	   fprintf (in, "\n================================================================");
	   fprintf (in, "\nThe number of the RTS packet received is:    %ld ", WGNnode(id)->nodeStats->RtsRxed);
	   fprintf (in, "\nThe number of the CTS packet received is:    %ld ", WGNnode(id)->nodeStats->CtsRxed);
	   fprintf (in, "\nThe number of the DATA packet received is:    %ld ", WGNnode(id)->nodeStats->DataRxed);
	   fprintf (in, "\nThe number of the ACK packet received is:    %ld ", WGNnode(id)->nodeStats->AckRxed);
	   fprintf (in, "\n================================================================");

	   fprintf (in, "\n\n\n\n================================================================");
	   fprintf (in, "\nINFORMATION OF CAPTURE OF NODE %d. ", id);
	   fprintf (in, "\n================================================================");
	   fprintf (in, "\nThe number of the packet CAPTURED is:    %ld ", WGNnode(id)->nodeStats->AptCaptureNo);
	   fprintf (in, "\n================================================================");

	   fprintf (in, "\n================================================================");
	   fprintf (in, "\nSTATISTIC INFORMATION OF NODE %d. ", id);
	   fprintf (in, "\n================================================================");
	   fprintf (in, "\nThe RTS PACKET RETRANSMISSION RATE is:    %0.2f%% ", WGNnode(id)->nodeStats->RtsReTranRate*100);
	   fprintf (in, "\nThe DATA PACKET RETRANSMISSION RATE is:    %0.2f%% ", WGNnode(id)->nodeStats->DataReTranRate*100 );
	   fprintf (in, "\nThe TOTAL PACKET RETRANSMISSION RATE is:    %0.2f%%  ", WGNnode(id)->nodeStats->ReTranRate*100);
	   fprintf (in, "\nThe RECV ERROR DROP RATE FOR RECV COLLISION is:    %0.2f%% ", WGNnode(id)->nodeStats->RecvColErrorDropRate*100);
	   fprintf (in, "\nThe RECV ERROR DROP RATE FOR RECV WHILE TX is:    %0.2f%% ", WGNnode(id)->nodeStats->RecvWhileTxErrorDropRate*100);
	   fprintf (in, "\nThe RECV ERROR DROP RATE FOR LOW POWER is:    %0.2f%% ", WGNnode(id)->nodeStats->RecvLowPwrErrorDropRate*100);
	   fprintf (in, "\nThe RECV ERROR DROP RATE FOR NOISE is:    %0.2e%% ", WGNnode(id)->nodeStats->RecvNoiseErrorDropRate*100);
	   fprintf (in, "\nThe RECV TOTAL ERROR DROP RATE is:    %0.2f%% ", WGNnode(id)->nodeStats->RecvErrorDropRate*100);
	   fprintf (in, "\nThe RECV PKT DROP RATE is:    %0.2f%%  ", WGNnode(id)->nodeStats->RecvDropRate*100);
	   fprintf (in, "\nThe TOTAL COLLISION RATE is:    %0.2f%%  ", WGNnode(id)->nodeStats->RecvColRate*100);
	   fprintf (in, "\n================================================================");
	   fprintf (in, "\n\n\n\n");
	   fclose(in);		    
	}

//=======================================================
//       FUNCTION:  StatsComp
//=======================================================
	void StatsComp(int id) {
       WGNnode(id)->nodeStats->TotPktTxed = WGNnode(id)->nodeStats->RtsTxed +
		                                                                 WGNnode(id)->nodeStats->CtsTxed +
		                                                                 WGNnode(id)->nodeStats->DataTxed +
		                                                                 WGNnode(id)->nodeStats->AckTxed;
	   
	   WGNnode(id)->nodeStats->ReTxNum	= 	WGNnode(id)->nodeStats->ReTxPktNum +
		                                                                WGNnode(id)->nodeStats->ReTxRtsNum;
	   
	   WGNnode(id)->nodeStats->DropForExMaxRetryNo = WGNnode(id)->nodeStats->DropForExMaxRtsRetryNo +
																						   WGNnode(id)->nodeStats->DropForExMaxPktRetryNo;
  	   
	   WGNnode(id)->nodeStats->TotPktErrorDrop =  WGNnode(id)->nodeStats->DropForInTx +
																		   WGNnode(id)->nodeStats->DropForCollision +
																		   WGNnode(id)->nodeStats->DropForLowRxPwr +
		                                                                   WGNnode(id)->nodeStats->DropForNoiseErr;

	   WGNnode(id)->nodeStats->PktSucRxed = WGNnode(id)->nodeStats->TotPktRxed -
		                                                                   WGNnode(id)->nodeStats->TotPktErrorDrop;  

	   WGNnode(id)->nodeStats->RtsReTranRate = (double)(WGNnode(id)->nodeStats->ReTxRtsNum)/(WGNnode(id)->nodeStats->RtsTxed);	 
	   WGNnode(id)->nodeStats->DataReTranRate = (double)(WGNnode(id)->nodeStats->ReTxPktNum)/(WGNnode(id)->nodeStats->DataTxed);	 
	   WGNnode(id)->nodeStats->ReTranRate = (double)(WGNnode(id)->nodeStats->ReTxNum)/(WGNnode(id)->nodeStats->TotPktTxed - WGNnode(id)->nodeStats->CtsTxed - WGNnode(id)->nodeStats->AckTxed);	 
	   WGNnode(id)->nodeStats->RecvColErrorDropRate = (double)WGNnode(id)->nodeStats->DropForCollision/WGNnode(id)->nodeStats->TotPktRxed;
       WGNnode(id)->nodeStats->RecvWhileTxErrorDropRate = (double)WGNnode(id)->nodeStats->DropForInTx/WGNnode(id)->nodeStats->TotPktRxed;
	   WGNnode(id)->nodeStats->RecvNoiseErrorDropRate = (double)WGNnode(id)->nodeStats->DropForNoiseErr/WGNnode(id)->nodeStats->TotPktRxed;
	   WGNnode(id)->nodeStats->RecvLowPwrErrorDropRate = (double)WGNnode(id)->nodeStats->DropForLowRxPwr/WGNnode(id)->nodeStats->TotPktRxed;
	   WGNnode(id)->nodeStats->RecvErrorDropRate = (double)WGNnode(id)->nodeStats->TotPktErrorDrop/WGNnode(id)->nodeStats->TotPktRxed;  
	   WGNnode(id)->nodeStats->RecvDropRate	= (double)(WGNnode(id)->nodeStats->TotPktErrorDrop + WGNnode(id)->nodeStats->NotForMeRxed) /WGNnode(id)->nodeStats->TotPktRxed;
	   WGNnode(id)->nodeStats->RecvColRate = (double)(WGNnode(id)->nodeStats->DropForCollision + WGNnode(id)->nodeStats->DropForInTx)/WGNnode(id)->nodeStats->TotPktRxed;
	}


//=======================================================
//       FUNCTION:  ResetStats
//=======================================================
  void ResetStats(int id) { 
	    int i;
		if (id<0||id>TotNodeNo) {
			printf ("[ResetStats]:: Error, invalid id number, type 'show system' to get the info about the id.\n");
			return;
		}
		if (id==0) {
		    for ( i=0; i<TotNodeNo; i++) {
				WGNnode(i+1)->nodeStats->BroadcastTx = 0;	  
				WGNnode(i+1)->nodeStats->UnicastTx = 0;     	
				WGNnode(i+1)->nodeStats->RtsTxed = 0;			 
				WGNnode(i+1)->nodeStats->CtsTxed = 0;			   
				WGNnode(i+1)->nodeStats->DataTxed = 0;		
				WGNnode(i+1)->nodeStats->AckTxed = 0;	
				WGNnode(i+1)->nodeStats->TotPktTxed = 0;
					
				//retransmission stuff
				WGNnode(i+1)->nodeStats->ReTxPktNum = 0;	 
				WGNnode(i+1)->nodeStats->ReTxRtsNum = 0;	
				WGNnode(i+1)->nodeStats->ReTxNum = 0;	

		    	//recording error stuff
				WGNnode(i+1)->nodeStats->DropForExMaxRtsRetryNo = 0;
				WGNnode(i+1)->nodeStats->DropForExMaxPktRetryNo = 0;
				WGNnode(i+1)->nodeStats->DropForExMaxRetryNo = 0;

				//before take a look at the content of the pkt
				WGNnode(i+1)->nodeStats->DropForInTx = 0;                            //recv packet when the node is sending
				WGNnode(i+1)->nodeStats->DropForCollision = 0;		  
		        WGNnode(i+1)->nodeStats->RtsDropForCollision = 0;
				WGNnode(i+1)->nodeStats->CtsDropForCollision = 0;
				WGNnode(i+1)->nodeStats->AckDropForCollision = 0;
				WGNnode(i+1)->nodeStats->DataDropForCollision = 0;
				WGNnode(i+1)->nodeStats->DropForLowRxPwr = 0;
				WGNnode(i+1)->nodeStats->DropForNoiseErr = 0;
				WGNnode(i+1)->nodeStats->TotPktErrorDrop = 0;

				//recording the pkt accepted correctly
				WGNnode(i+1)->nodeStats->TotPktRxed = 0;	
				WGNnode(i+1)->nodeStats->PktSucRxed = 0;	
				WGNnode(i+1)->nodeStats->NotForMeRxed = 0;
				WGNnode(i+1)->nodeStats->RtsRxed = 0; 
				WGNnode(i+1)->nodeStats->CtsRxed = 0;
				WGNnode(i+1)->nodeStats->DataRxed = 0;
				WGNnode(i+1)->nodeStats->AckRxed = 0;

				//about capture function
  				WGNnode(i+1)->nodeStats->AptCaptureNo = 0;                         //accept for the capture

				//about rate stuff
				WGNnode(i+1)->nodeStats->RtsReTranRate	= 0;
				WGNnode(i+1)->nodeStats->DataReTranRate = 0;
                WGNnode(i+1)->nodeStats->ReTranRate = 0;
				WGNnode(i+1)->nodeStats->RecvColErrorDropRate = 0;
				WGNnode(i+1)->nodeStats->RecvWhileTxErrorDropRate = 0;
				WGNnode(i+1)->nodeStats->RecvLowPwrErrorDropRate = 0;
				WGNnode(i+1)->nodeStats->RecvNoiseErrorDropRate = 0;
	        	WGNnode(i+1)->nodeStats->RecvErrorDropRate = 0;
			    WGNnode(i+1)->nodeStats->RecvDropRate = 0;     //including the packets which are not for me
	            WGNnode(i+1)->nodeStats->RecvColRate = 0;

				//for sepecial purpose
				WGNnode(i+1)->nodeStats->TotTxByteNo = 0;
	            WGNnode(i+1)->nodeStats->LToMBufDrop = 0;
	            WGNnode(i+1)->nodeStats->LToUBufDrop = 0;
			}//end of for
			PrintLine ();
			printf("[ResetStats]:: Reset the statistic parameters for all nodes in the system successfully!\n");
			PrintLine ();
		}//end of if
		else	{
				WGNnode(id)->nodeStats->BroadcastTx = 0;	  
				WGNnode(id)->nodeStats->UnicastTx = 0;     	
				WGNnode(id)->nodeStats->RtsTxed = 0;			 
				WGNnode(id)->nodeStats->CtsTxed = 0;			   
				WGNnode(id)->nodeStats->DataTxed = 0;		
				WGNnode(id)->nodeStats->AckTxed = 0;	
				WGNnode(id)->nodeStats->TotPktTxed = 0;
					
				//retransmission stuff
				WGNnode(id)->nodeStats->ReTxPktNum = 0;	 
				WGNnode(id)->nodeStats->ReTxRtsNum = 0;	
				WGNnode(id)->nodeStats->ReTxNum = 0;	

		    	//recording error stuff
				WGNnode(id)->nodeStats->DropForExMaxRtsRetryNo = 0;
				WGNnode(id)->nodeStats->DropForExMaxPktRetryNo = 0;
				WGNnode(id)->nodeStats->DropForExMaxRetryNo = 0;

				//before take a look at the content of the pkt
				WGNnode(id)->nodeStats->DropForInTx = 0;                            //recv packet when the node is sending
				WGNnode(id)->nodeStats->DropForCollision = 0;		  
		        WGNnode(id)->nodeStats->RtsDropForCollision = 0;
				WGNnode(id)->nodeStats->CtsDropForCollision = 0;
				WGNnode(id)->nodeStats->AckDropForCollision = 0;
				WGNnode(id)->nodeStats->DataDropForCollision = 0;
				WGNnode(id)->nodeStats->DropForLowRxPwr = 0;
				WGNnode(id)->nodeStats->DropForNoiseErr = 0;
				WGNnode(id)->nodeStats->TotPktErrorDrop = 0;

				//recording the pkt accepted correctly
				WGNnode(id)->nodeStats->TotPktRxed = 0;	
				WGNnode(id)->nodeStats->PktSucRxed = 0;	
				WGNnode(id)->nodeStats->NotForMeRxed = 0;
				WGNnode(id)->nodeStats->RtsRxed = 0; 
				WGNnode(id)->nodeStats->CtsRxed = 0;
				WGNnode(id)->nodeStats->DataRxed = 0;
				WGNnode(id)->nodeStats->AckRxed = 0;

				//about capture function
  				WGNnode(id)->nodeStats->AptCaptureNo = 0;                         //accept for the capture

				//about rate stuff
				WGNnode(id)->nodeStats->RtsReTranRate	= 0;
				WGNnode(id)->nodeStats->DataReTranRate = 0;
                WGNnode(id)->nodeStats->ReTranRate = 0;
		    	WGNnode(id)->nodeStats->RecvColErrorDropRate = 0;
		        WGNnode(id)->nodeStats->RecvWhileTxErrorDropRate = 0;
				WGNnode(id)->nodeStats->RecvLowPwrErrorDropRate = 0;
				WGNnode(id)->nodeStats->RecvNoiseErrorDropRate = 0;
	        	WGNnode(id)->nodeStats->RecvErrorDropRate = 0;
			    WGNnode(id)->nodeStats->RecvDropRate = 0;     //including the packets which are not for me
	            WGNnode(id)->nodeStats->RecvColRate = 0;

				//for sepecial purpose
				WGNnode(id)->nodeStats->TotTxByteNo = 0;
	            WGNnode(id)->nodeStats->LToMBufDrop = 0;
	            WGNnode(id)->nodeStats->LToUBufDrop = 0;

				PrintLine ();
			    printf("[ResetStats]:: Reset the statistic parameters for node %d successfully!\n",id);
			    PrintLine ();
		}
   }


//=======================================================
//       FUNCTION:  FileNameGen
//=======================================================
void FileNameGen(int id, char* type, char* filename) {    
	char index[10];

	sprintf(index,"%d",id);
	strcpy(filename,"node_");
	strcat(filename,index);
	strcat(filename,"_");
	strcat(filename, type);
	strcat(filename,"_");
	if (!strcmp(type, "pkt")) {
		sprintf(index,"%d",FileSeqArray[id-1]);
	    strcat(filename,index);
		FileSeqArray[id-1] += 1;	
	}
	if (!strcmp(type, "mob")) {
		sprintf(index,"%d",MobSeqArray[id-1]);
	    strcat(filename,index);
		MobSeqArray[id-1] +=1;
	}
}

//=======================================================
//       FUNCTION:  FileNameGen
//=======================================================
WGNflag IsFileValid(char* filename) {    
	FILE* in; 
	in = fopen(filename, "a+");
    if(in==NULL) {
       return (FALSE);
    }
	else
	   return (TRUE);
}



