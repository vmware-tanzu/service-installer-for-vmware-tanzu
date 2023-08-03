/*
 * Copyright 2021 VMware, Inc
 * SPDX-License-Identifier: BSD-2-Clause
 */
import { Injectable } from '@angular/core';
import {HttpClient, HttpResponse, HttpErrorResponse, HttpHeaders} from '@angular/common/http';
import {Observable, throwError} from 'rxjs';
import { map} from 'rxjs/operators';
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
        const headers = new HttpHeaders();
        const headersEnv = headers.set('env', 'vsphere');
        return this.httpClient.get(url, {headers: headersEnv})
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
        const headers = new HttpHeaders();
        const headersEnv = headers.set('env', env);
        return this.httpClient.get(url, {responseType: 'blob', headers: headersEnv})
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
        const headers = new HttpHeaders();
        const headersEnv = headers.set('env', 'vsphere');

        return this.httpClient.post(url, data, {observe: 'response', headers: headersEnv})
            .pipe(
                map((res: HttpResponse<any>) => this.handleResponse(res)),
                catchError((error: HttpErrorResponse) => this.handleError(error))
            );

    }

    postGenerateInput(url: string, data: any, filename, env): Observable<any> {
        const headersEnv = new HttpHeaders({
            'env': env,
            'filename': filename
        });
        return this.httpClient.post(url, data, {observe: 'response', headers: headersEnv})
            .pipe(
                map((res: HttpResponse<any>) => this.handleResponse(res)),
                catchError((error: HttpErrorResponse) => this.handleError(error))
            );
    }

    postVmc(url: string, data: any): Observable<any> {
        const headers = new HttpHeaders();
        const headersEnv = headers.set('env', 'vmc');

        return this.httpClient.post(url, data, {observe: 'response', headers: headersEnv})
            .pipe(
                map((res: HttpResponse<any>) => this.handleResponse(res)),
                catchError((error: HttpErrorResponse) => this.handleError(error))
            );
    }

    postVcf(url: string, data: any): Observable<any> {
        const headers = new HttpHeaders();
        const headersEnv = headers.set('env', 'vcf');
        return this.httpClient.post(url, data, {observe: 'response', headers: headersEnv})
            .pipe(
                map((res: HttpResponse<any>) => this.handleResponse(res)),
                catchError((error: HttpErrorResponse) => this.handleError(error))
            );
    }

    postCall(url: string, data: any, env: string): Observable<any> {
        const headers = new HttpHeaders();
        const headersEnv = headers.set('env', env);
        return this.httpClient.post(url, data, {observe: 'response', headers: headersEnv})
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
        if (response.status === 204) {
            return {};
        } else {
            return response.body;
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
