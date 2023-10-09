import { Injectable } from '@angular/core';
import { CanActivate, ActivatedRouteSnapshot, RouterStateSnapshot, Router } from '@angular/router';
import { APP_ROUTES } from '../constants/routes.constants';
import { AuthService } from './auth.service';
import { APIClient } from 'src/app/swagger/api-client.service';

@Injectable({
  providedIn: 'root',
})
export class AuthGuard implements CanActivate {
  	constructor(
		private authService: AuthService,
		private router: Router,
		public apiClient: APIClient
  	) {}

	canActivate(
		next: ActivatedRouteSnapshot,
		state: RouterStateSnapshot
	) {
		return this.isAuthenticated();
	}

	public async isAuthenticated() {

		await this.apiClient.isSessionActive().toPromise().then((data: any) => {
			if (data && data !== null) {
				if (data.SESSION === 'ACTIVE') {
				    this.apiClient.loggedInUser = data.USER;
					return true;
				} else if (data.SESSION === 'INACTIVE') {
					this.router.navigate([APP_ROUTES.LOGIN]);
				}
			}
		})
		.catch((error: any) => {
            this.router.navigate([APP_ROUTES.LOGIN]);
        });
		return true;
	}
}
