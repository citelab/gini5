/*
 * NAME: energy.c 
 * FUNCTION: Collection of functions implements the energy module. because 
 *                    so far there is no implementation about the power save mode, 
 *                    therefore, this file only provide some interface for the future de-
 *                    velopment.
 * AUTHOR: Sheng Liao
 * DATE:   Revised on Oct 12th, 2005
 */

//=======================================================
//       File Name :  energy.c
//=======================================================  
 #include "energy.h"

//=======================================================
//       Function Part
//======================================================= 

//=======================================================
//       FUNCTION: IniEnergyModel
//       PURPOSE:  Initialize the energy module.
//======================================================= 
    void IniNodeEnergy(NodeType type) {
		 int id;
		 if (prog_verbosity_level()==2){
             printf("[IniNodeEnergy]:: Initializing energy module ... ");
		 }	
		 if (type == NORMAL) {
			  for ( id=1; id<=TotNodeNo; id++) {
					 WGNnode(id)->nodePhy->nodeEnergy = (NodeEnergy *)malloc(sizeof(NodeEnergy));
					 if( WGNnode(id)->nodePhy->nodeEnergy == NULL ){
					     printf("IniEnergyModel(): nodeEnergy malloc error");
					     exit(1);
					 }
                    /*set the power switch of the mobile node*/
					WGNnode(id)->nodePhy->nodeEnergy->PowSwitch = EnPowSwitchArray[(WGNnode(id)->Id)-1];    
		
					 if (WGNnode(id)->nodePhy->nodeEnergy->PowSwitch==ON) {
						  WGNnode(id)->nodePhy->nodeEnergy->PSM = EnPSMArray[id-1];
						  WGNnode(id)->nodePhy->nodeEnergy->TotalEnergy = TotalEnergyArray[id-1];                                         
						  WGNnode(id)->nodePhy->nodeEnergy->Pt = WGNnode(id)->nodePhy->nodeWCard->Pt;
						  WGNnode(id)->nodePhy->nodeEnergy->Pt_consume = WGNnode(id)->nodePhy->nodeWCard->Pt_consume;
						  WGNnode(id)->nodePhy->nodeEnergy->Pr_consume = WGNnode(id)->nodePhy->nodeWCard->Pr_consume;
						  WGNnode(id)->nodePhy->nodeEnergy->P_idle = WGNnode(id)->nodePhy->nodeWCard->P_idle;
						  WGNnode(id)->nodePhy->nodeEnergy->P_sleep = WGNnode(id)->nodePhy->nodeWCard->P_sleep;
						  WGNnode(id)->nodePhy->nodeEnergy->P_off = WGNnode(id)->nodePhy->nodeWCard->P_off;
					}
					else 
				       printf ("This mobile node is POWER OFF.");
		     }	
		 }
		 if (prog_verbosity_level()==2){
		     printf("[ OK ]\n");
		 }
    }   


//=======================================================
//       FUNCTION: FinalizeNodeEnergy
//======================================================= 
    void FinalizeNodeEnergy(NodeType type) {
		 int id;
		 if (prog_verbosity_level()==2){
			 printf("[FinalizeEnergyModel]:: Finalizing energy module ... ");
		 }
		 if (type == NORMAL) {
			  for ( id=1; id<=TotNodeNo; id++) {
					 free(WGNnode(id)->nodePhy->nodeEnergy);
		     }	
		 }
		 if (prog_verbosity_level()==2){		 
			  printf("[ OK ]\n");
		 }
    }   


//=======================================================
//       FUNCTION:  UpdateEnergy
//       PURPOSE:   Update the total energy of the node after a period.
//=======================================================   
    Switch UpdateEnergy(MobileNode *node, EnergyUpdate_type type, double time){
		double pwr_consume_unit_time;

		if (type == IDLE)
		    pwr_consume_unit_time = node->nodePhy->nodeEnergy->P_idle;
		else if (type == TX)
            pwr_consume_unit_time = node->nodePhy->nodeEnergy->Pt_consume;
		else if (type == RX)
            pwr_consume_unit_time = node->nodePhy->nodeEnergy->Pr_consume;
        else if (type == SLEEP)
            pwr_consume_unit_time = node->nodePhy->nodeEnergy->P_sleep;
		else {
            printf ("[UpdateEnergy]:: Unrecognized EnergyUpdate type.");
		    exit (1); 
		}
        /*reduce the energy consumed in the idle period*/
		node->nodePhy->nodeEnergy->TotalEnergy -= pwr_consume_unit_time*time;
        if (node->nodePhy->nodeEnergy->TotalEnergy <= 0) {
            node->nodePhy->nodeEnergy->TotalEnergy = 0;
            node->nodePhy->nodeEnergy->PowSwitch = OFF;
        }
        return (node->nodePhy->nodeEnergy->PowSwitch);
	}
	
//=======================================================
//       FUNCTION:  GetPowSwitch
//       PURPOSE:   Get the status of the power swtich of the node.
//=======================================================    
    Switch GetPowSwitch(MobileNode *node) {
        return (node->nodePhy->nodeEnergy->PowSwitch);
    }

//=======================================================
//       FUNCTION:  GetPSM
//       PURPOSE:   Get the status of the switch of the node's PSM.
//=======================================================   
    Switch GetPSM(MobileNode *node) {
        return (node->nodePhy->nodeEnergy->PSM);
    }

//=======================================================
//       FUNCTION:  GetTotalEnergy
//       PURPOSE:   Get the status of the switch of the node's PSM.
//=======================================================   
    double GetTotalEnergy(MobileNode *node) {
        return node->nodePhy->nodeEnergy->TotalEnergy;
    }

//=======================================================
//       FUNCTION:  SetPowSwitch
//       PURPOSE:   Set the status of the power swtich of the node.
//=======================================================    
    void SetPowSwitch(MobileNode *node) {
        node->nodePhy->nodeEnergy->PowSwitch = EnPowSwitchArray[node->Id-1];
    } 

//=======================================================
//       FUNCTION:  SetPSM
//       PURPOSE:   Set the status of the switch of the node's PSM.
//=======================================================   
    void SetPSM(MobileNode *node) {
        node->nodePhy->nodeEnergy->PSM = EnPSMArray[node->Id-1];
    }

//=======================================================
//       FUNCTION:  SetTotalEnergy
//       PURPOSE:   Set the status of the switch of the node's PSM.
//=======================================================   
    void SetTotalEnergy(MobileNode *node) {
        node->nodePhy->nodeEnergy->TotalEnergy =  TotalEnergyArray[node->Id-1];
    }
