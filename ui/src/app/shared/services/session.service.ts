import { Injectable } from '@angular/core';
import { Router } from '@angular/router';

@Injectable({
  providedIn: 'root'
})
export class SessionService {

  constructor(private router: Router) { }

  getAppCookie(): any{
    return localStorage.getItem('cookie');
  }

  setLocalStorage(cookie: any): any{
    localStorage.setItem('cookie', cookie);
  }

  removeLocalStorage(): any{
    localStorage.setItem('cookie', '');
  }

}
