import {Injectable} from '@angular/core';
import {ApiHandlerService} from '../api-handler.service';
import {AppApiUrls} from '../enums/app-api-urls.enum';
import {ApiEndPoint} from '../../configs/api-endpoint.config';
import {SessionService} from './session.service';
import {Validators} from '@angular/forms';

@Injectable({
  providedIn: 'root'
})

export class AnsibleService {

  private apiEndPointConfig: ApiEndPoint;
  private apiEndPoint: string;
  private apiEndpoint: string;
  constructor(private apiHandlerService: ApiHandlerService,
              public sessionService: SessionService) {
    this.apiEndPointConfig = new ApiEndPoint();
    this.apiEndPoint = this.apiEndPointConfig.getGeneratedApiEndpoint();
    this.apiEndpoint = this.apiEndPointConfig.getGeneratedApiEndpoint();
  }

  homePage(data: any): any {
  const payload = {
   "refreshToken": data.login.refreshToken,
   "aviManagementName": data.aviManagementSegment.aviManagementName,
    "aviGatewayAddress": data.aviManagementSegment.aviGatewayAddress,
    "aviDhcpStartRange": data.aviManagementSegment.aviDhcpStartRange,
    "aviDhcpEndRange": data.aviManagementSegment.aviDhcpEndRange,
    "aviDnsServers": data.aviManagementSegment.aviDnsServers,
    "tkgManagementName": data.tkgManagementSegment.tkgManagementName,
    "tkgGatewayAddress": data.tkgManagementSegment.tkgGatewayAddress,
    "tkgDhcpStartRange": data.tkgManagementSegment.tkgDhcpStartRange,
    "tkgDhcpEndRange": data.tkgManagementSegment.tkgDhcpEndRange,
    "tkgDnsServers": data.tkgManagementSegment.tkgDnsServers,
    "tkgWorkloadName": data.tkgWorkloadSegment.tkgWorkloadName,
    "tkgWorkloadGatewayAddress": data.tkgWorkloadSegment.tkgWorkloadGatewayAddress,
    "tkgWorkloadDhcpStartRange": data.tkgWorkloadSegment.tkgWorkloadDhcpStartRange,
    "tkgWorkloadDhcpEndRange": data.tkgWorkloadSegment.tkgWorkloadDhcpEndRange,
    "tkgWorkloadDnsServers": data.tkgWorkloadSegment.tkgWorkloadDnsServers,
    "tkgAviDataName": data.tkgAviDataSegment.tkgAviDataName,
    "tkgAviDataGatewayAddress": data.tkgAviDataSegment.tkgAviDataGatewayAddress,
    "tkgAviDataDhcpStartRange": data.tkgAviDataSegment.tkgAviDataDhcpStartRange,
    "tkgAviDataDhcpEndRange": data.tkgAviDataSegment.tkgAviDataDhcpEndRange,
    "tkgAviDataDnsServers": data.tkgAviDataSegment.tkgAviDataDnsServers,
    "inventoryGroupsCgwAviName": data.inventoryGroupsCgw.inventoryGroupsCgwAviName,
    "inventoryGroupsCgwTkgName": data.inventoryGroupsCgw.inventoryGroupsCgwTkgName,
    "inventoryGroupsTKGWorkloadName": data.inventoryGroupsCgw.inventoryGroupsTKGWorkloadName,
    "inventoryGroupsDnsIps": data.inventoryGroupsCgw.inventoryGroupsDnsIps,
    "inventoryGroupsNtpIPs": data.inventoryGroupsCgw.inventoryGroupsNtpIPs,
    "inventoryGroupsCgwTkgManagementControlPlaneIP": data.inventoryGroupsCgw.inventoryGroupsCgwTkgManagementControlPlaneIP,
    "inventoryGroupsCgwTkgWorkloadControlPlaneIP": data.inventoryGroupsCgw.inventoryGroupsCgwTkgWorkloadControlPlaneIP,
    "inventoryGroupsCgwVcenterIP": data.inventoryGroupsCgw.inventoryGroupsCgwVcenterIP,
    "inventoryGroupsMgwTkgManagementNetworkGroupName": data.inventoryGroupsMgw.inventoryGroupsMgwTkgManagementNetworkGroupName,
    "inventoryGroupsMgwTkgWorkloadNetworkGroupName": data.inventoryGroupsMgw.inventoryGroupsMgwTkgWorkloadNetworkGroupName,
    "inventoryGroupsMgwAviManagementNetworkGroupName": data.inventoryGroupsMgw.inventoryGroupsMgwAviManagementNetworkGroupName,
    "tkgAndAviDnsNameCgw": data.firewallRuleCgw.tkgAndAviDnsNameCgw,
    "tkgAndAviNtpNameCgw": data.firewallRuleCgw.tkgAndAviNtpNameCgw,
    "tkgAndAviVcenterNameCgw": data.firewallRuleCgw.tkgAndAviVcenterNameCgw,
    "tkgAndAviInternetNameCgw": data.firewallRuleCgw.tkgAndAviInternetNameCgw,
    "tkgAndAviMgmtNameCgw": data.firewallRuleCgw.tkgAndAviMgmtNameCgw,
    "tkgMgmtToTkgWorkloadVipNameCgw": data.firewallRuleCgw.tkgMgmtToTkgWorkloadVipNameCgw,
    "tkgWorkloadToTkgMgmtVipNameCgw": data.firewallRuleCgw.tkgWorkloadToTkgMgmtVipNameCgw,

    "csfrUserName": data.aviControllerConfig.csfrUserName,
    "csfrUserPassword": data.aviControllerConfig.csfrUserPassword,
    "setAdminPassword": data.aviControllerConfig.setAdminPassword,
    "setServerListIpAndType": data.aviControllerConfig.setServerListIpAndType,
    "ntpServerListAndType": data.aviControllerConfig.ntpServerListAndType,
    "setBackupPassPhrase": data.aviControllerConfig.setBackupPassPhrase,

    "tkgAndAviVcenterNameMgw": data.firewallRuleMgw.tkgAndAviVcenterNameMgw
  };
  const url = this.apiEndpoint  + AppApiUrls.EXECUTE;
  return this.apiHandlerService.post(url, payload);
  }
}
