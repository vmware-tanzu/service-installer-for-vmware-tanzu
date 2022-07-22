import { Injectable } from '@angular/core';
import {HttpClient, HttpResponse, HttpErrorResponse, HttpHeaders} from '@angular/common/http';
import { Observable } from 'rxjs';
import { map, catchError } from 'rxjs/operators';


@Injectable({
  providedIn: 'root'
})
export class ApiHandlerService {



  constructor(private httpClient: HttpClient) { }

  /**
   *
   * @param url Executes GET api
   */
  get(url: string, token: string): Observable<any> {
    const httpHeaders = new HttpHeaders({
      'Content-Type':  'application/json',
      Authorization: 'Bearer ' + token,
    });
    return this.httpClient.get(url, { observe: 'response', headers: httpHeaders }).
    pipe(map((res: HttpResponse<any>) => this.handleResponse(res)))
      .pipe(catchError((error: HttpErrorResponse) => this.handleError(error)));
  }

  /**
   *
   * @param url Executes GET api
   */
  download(url: string, token: string): Observable<any> {
    const httpHeaders = new HttpHeaders({
      Authorization: 'Bearer ' + token
    });

    return this.httpClient.get(url, { observe: 'response', headers: httpHeaders })
      .pipe(map((res: HttpResponse<any>) => this.handleResponse(res)))
      .pipe(catchError((error: HttpErrorResponse) => this.handleError(error)));
  }

  /**
   *
   * @param url Execites POST api
   */
  save(url: string, data: any, token: string): Observable<any> {
    const httpHeaders = new HttpHeaders({
      'Content-Type':  'application/json',
      Authorization: 'Bearer ' + token,
    });

    return this.httpClient.post(url, data, {observe: 'response', headers: httpHeaders})
      .pipe(map((res: HttpResponse<any>) => this.handleResponse(res)))
      .pipe(catchError((error: HttpErrorResponse) => this.handleError(error)));
  }

  post(url: string, data: any): Observable<any> {
    const httpHeaders = new HttpHeaders({
      'Content-Type':  'application/json'
    });

    return this.httpClient.post(url, data, {observe: 'response', headers: httpHeaders})
      .pipe(map((res: HttpResponse<any>) => this.handleResponse(res)))
      .pipe(catchError((error: HttpErrorResponse) => this.handleError(error)));
  }

  update(url: string, data: any): Observable<any> {
    return this.httpClient.put(url, data, { observe: 'response' })
      .pipe(map((res: HttpResponse<any>) => this.handleResponse(res)))
      .pipe(catchError((error: HttpErrorResponse) => this.handleError(error)));
  }

  /**
   *
   * @param url Executes DELETE api
   */
  delete(url: string): Observable<any> {
    return this.httpClient.delete(url, { observe: 'response' })
      .pipe(map((res: HttpResponse<any>) => this.handleResponse(res)))
      .pipe(catchError((error: HttpErrorResponse) => this.handleError(error)));
  }

  downloadFile(url: string, token: string): Observable<any> {
    const httpHeaders = new HttpHeaders({
      Authorization: 'Bearer ' + token
    });
    return this.httpClient.get(url, {responseType: 'blob', headers: httpHeaders})
      .pipe(map(res => res as Blob))
      .pipe(catchError((error: HttpErrorResponse) => this.handleError(error)));
  }

  /**
   * Handles api response
   */
  handleResponse(response: any): any {
    if (response.status === 204) {
      return {};
    } else {
      return response.body;
    }
  }

  /**
   * Handles api error
   */
  handleError(error: HttpErrorResponse): any {
    if (error.status === 401) {
      return Observable.throw(error.error);
    } else if (error.status === 500) {
      return Observable.throw(error.error);
    } else {
      return Observable.throw(error.error || 'Something has gone wrong. Please contact support.');
    }
  }
}
