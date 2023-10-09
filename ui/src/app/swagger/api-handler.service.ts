/*
 * Copyright 2021 VMware, Inc
 * SPDX-License-Identifier: BSD-2-Clause
 */
import { Injectable } from '@angular/core';
import { HttpClient, HttpResponse, HttpErrorResponse, HttpHeaders } from '@angular/common/http';
import { Observable, Subject, throwError } from 'rxjs';
import { map, takeUntil} from 'rxjs/operators';
import { catchError } from 'rxjs/operators/catchError';
import 'rxjs/Rx';

@Injectable({
    providedIn: 'root'
})
export class ApiHandlerService {



    constructor(private httpClient: HttpClient) { }

    /**
     *
     * @param url Executes GET api
     */
    get(url: string): Observable<any> {
        let header = new HttpHeaders();
        header = header.set('Access-Control-Allow-Credentials', 'true');
        header = header.set('x-access-tokens', localStorage.getItem('token'));
        const val = localStorage.getItem('token');

        return this.httpClient.get(url, {observe: 'response', headers: header, withCredentials: true})
            .pipe(
                map((res: HttpResponse<any>) => this.handleResponse(res)),
                catchError((error: HttpErrorResponse) => this.handleError(error))
            );
    }

    /**
     *
     * @param url Executed a GET api for a download call
     */
    download(url: string, env: string): Observable<any> {
        let header = new HttpHeaders();
        header = header.set('env', env);
        header = header.set('x-access-tokens', localStorage.getItem('token'));
        return this.httpClient.get(url, {responseType: 'blob', headers: header})
            .pipe(
                map(res => res as Blob),
                catchError((error: HttpErrorResponse) => this.handleError(error))
            );
    }

    /**
     *
     * @param url Executes POST api
     * @param data
     */
    post(url: string, data: any): Observable<any> {
        let header = new HttpHeaders();
        header = header.set('env', 'vsphere');
        header = header.set('x-access-tokens', localStorage.getItem('token'));

        return this.httpClient.post(url, data, {observe: 'response', headers: header})
            .pipe(
                map((res: HttpResponse<any>) => this.handleResponse(res)),
                catchError((error: HttpErrorResponse) => this.handleError(error))
            );

    }

    loginAPIpost(url: string, data: any): Observable<any> {
        let headers = new HttpHeaders();
        headers = headers.set('Server', data.fqdn);
        let authorizationData = 'Basic ' + btoa(data.username + ':' + data.password);
        headers = headers.set('Authorization', authorizationData);

        return this.httpClient.post(url, {}, {observe: 'response', headers: headers, withCredentials: true})
            .pipe(
                map((res: HttpResponse<any>) => this.handleResponse(res)),
                catchError((error: HttpErrorResponse) => this.handleError(error))
            );
    }

    postGenerateInput(url: string, data: any, filename, env): Observable<any> {
        let header = new HttpHeaders();
        header = header.set('env', env);
        header = header.set('filename', filename);
        header = header.set('x-access-tokens', localStorage.getItem('token'));

        return this.httpClient.post(url, data, {observe: 'response', headers: header})
            .pipe(
                map((res: HttpResponse<any>) => this.handleResponse(res)),
                catchError((error: HttpErrorResponse) => this.handleError(error))
            );
    }

    postVmc(url: string, data: any): Observable<any> {
        let header = new HttpHeaders();
        header = header.set('env', 'vmc');
        header = header.set('x-access-tokens', localStorage.getItem('token'));

        return this.httpClient.post(url, data, {observe: 'response', headers: header})
            .pipe(
                map((res: HttpResponse<any>) => this.handleResponse(res)),
                catchError((error: HttpErrorResponse) => this.handleError(error))
            );
    }

    postVcf(url: string, data: any): Observable<any> {
        let header = new HttpHeaders();
        header = header.set('env', 'vcf');
        header = header.set('x-access-tokens', localStorage.getItem('token'));

        return this.httpClient.post(url, data, {observe: 'response', headers: header})
            .pipe(
                map((res: HttpResponse<any>) => this.handleResponse(res)),
                catchError((error: HttpErrorResponse) => this.handleError(error))
            );
    }

    postCall(url: string, data: any, env: string): Observable<any> {
        let header = new HttpHeaders();
        header = header.set('env', env);
        header = header.set('x-access-tokens', localStorage.getItem('token'));

        return this.httpClient.post(url, data, {observe: 'response', headers: header})
            .pipe(
                map((res: HttpResponse<any>) => this.handleResponse(res)),
                catchError((error: HttpErrorResponse) => this.handleError(error))
            );
    }

    /**
     * Handles api response
     * @param response
     */
    handleResponse(response) {
        if (response.status === 204 || response.status === 200) {
            console.log(response.headers);
            return response && response.body ? response.body : response;
        } else {
            console.log(response.headers);
            return response && response.body ? response.body : response;
        }
    }

    /**
     * Handles api error
     * @param error
     */
    handleError(error: HttpErrorResponse) {
        let errorMessage = 'Unknown error!';
        if (error.error instanceof ErrorEvent) {
            errorMessage = `Error: ${error.error}`;
        } else {
            errorMessage = `Error Code: ${error.error}\nMessage: ${error.error}`;
        }
        return throwError(error.error);
    }
}
