import { Injectable } from '@angular/core';
import { HttpEvent, HttpHeaders, HttpInterceptor, HttpHandler, HttpRequest, HttpResponse } from '@angular/common/http';
import { Observable } from 'rxjs';
import { SessionService } from './services/session.service';

@Injectable()
export class HttpInterceptorsService implements HttpInterceptor {

  headers: HttpHeaders;

  constructor(public sessionService: SessionService) {
    this.headers = new HttpHeaders();
  }

  /**
   * Creates the required headers for request
   */
  createAuthorizationHeader(): void {
    let sessionId = this.sessionService.getAppCookie();
    sessionId = sessionId !== null ? sessionId.toString() : '';
    this.headers = this.headers.set('Access-Control-Allow-Origin', '*');
    this.headers = this.headers.set('Access-Control-Allow-Credentials', 'true');
    this.headers = this.headers.set('Content-Type', 'application/json');
    this.headers = this.headers.set('Accept', 'q=0.8;application/json;q=0.9');
    this.headers = this.headers.set('vmware-api-session-id', sessionId);
  }

  /**
   *
   * @param req Request to be cloned
   * @param next Handling request
   */
  intercept(req: HttpRequest<any>, next: HttpHandler): Observable<HttpEvent<any>> {
    this.createAuthorizationHeader();
    const apiRequest = req.clone({headers: this.headers});
    return next.handle(apiRequest);
  }
}
