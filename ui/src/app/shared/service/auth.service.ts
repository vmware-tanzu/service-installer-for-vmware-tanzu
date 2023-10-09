import { Injectable } from '@angular/core';
import { Observable } from 'rxjs';
import { APIClient } from 'src/app/swagger/api-client.service';

@Injectable({
  providedIn: 'root'
})
export class AuthService {

  constructor(public apiClient: APIClient) { }

  public setPermissions(permissions): void {
    // this.permissions = permissions;
  }

  public isAuthenticated(): boolean {
    // return false;
    try {
      this.apiClient.isSessionActive().subscribe((data: any) => {
        if (data && data !== null) {
            if (data.SESSION === 'ACTIVE') {
                return true;
            } else if (data.SESSION === 'INACTIVE') {
                return false;
            }
        } else {
          return false;
        }
      }, (err: any) => {
        return false;
      });
    } catch {
      return false;
    }
  }

//   public getPermissions(): AuthPermissions {
//     return this.permissions;
//   }

//   public getPermissionStatus(): boolean {
//     return this.permissionStatus;
//   }

  public setPermissionStatus(permissionStatus: boolean) {
    // this.permissionStatus = permissionStatus;
  }

//   public getAuthPermissions(): Observable<AuthPermissions> {
//     const endpoint = `${MdsApiUrl.MDS_AUTH_SERVICES}${MdsApiUrl.AUTH}/${MdsApiUrl.MDS_PERMISSIONS}`
//     return this.mdsApiService.getAuth(endpoint);
//   }

//   public getAuthToken(): Observable<any> {
//     const endpoint = `${MdsApiUrl.MDS_AUTH_SERVICES}${MdsApiUrl.AUTH}${MdsApiUrl.TOKEN}`
//     return this.mdsApiService.getAuth(endpoint);
//   }

//   public getRefreshToken(): Observable<any> {
//     const endpoint = `${MdsApiUrl.MDS_AUTH_SERVICES}${MdsApiUrl.AUTH}${MdsApiUrl.REFRESH_TOKEN}`
//     return this.mdsApiService.postAuth(endpoint, '');
//   }

//   public logout(): Observable<any> {
//     const endpoint = `${MdsApiUrl.MDS_AUTH_SERVICES}${MdsApiUrl.AUTH}/${MdsApiUrl.LOGOUT}`
//     return this.mdsApiService.getAuth(endpoint)
//   }

//   public getServiceInstanceDetails(): Observable<any> {
//     const endpoint = `${MdsApiUrl.MDS_AUTH_SERVICES}/${MdsApiUrl.SERVICE_INSTANCE}`
//     return this.mdsApiService.getAuth(endpoint)
//   }

}
