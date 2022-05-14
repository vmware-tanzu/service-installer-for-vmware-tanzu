import { Injectable } from '@angular/core';
import {HttpClient, HttpResponse, HttpErrorResponse, HttpHeaders} from '@angular/common/http';
import {Observable, throwError} from 'rxjs';
import { map} from 'rxjs/operators';
import { catchError } from 'rxjs/operators/catchError';
import 'rxjs/Rx';
import {RequestOptions} from '@angular/http';

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
//      return this.httpClient.get(url, data, { observe: 'response', headers: headers_env })
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
     * @param url Executes GET api
     */
    // download(url: string, token: string): Observable<any> {
    //     const httpHeaders = new HttpHeaders({
    //         'Authorization': 'Bearer ' + token
    //     });
    //
    //     return this.httpClient.get(url, { observe: 'response', headers: httpHeaders })
    //         .map((res: HttpResponse<any>) => this.handleResponse(res))
    //         .catch((error: HttpErrorResponse) => this.handleError(error));
    // };

    /**
     *
     * @param url Execites POST api
     * @param data
     */
    // save(url: string, data: any, token: string): Observable<any> {
    //     const httpHeaders = new HttpHeaders({
    //         'Content-Type':  'application/json',
    //         'Authorization': 'Bearer ' + token,
    //     });
    //
    //     return this.httpClient.post(url, data, {observe: 'response', headers: httpHeaders})
    //         .map((res: HttpResponse<any>) => this.handleResponse(res))
    //         .catch((error: HttpErrorResponse) => this.handleError(error));
    // };

    /**
     *
     * @param url Executes POST api
     * @param data
     */
    post(url: string, data: any): Observable<any> {
        const headers = new HttpHeaders();
        const headersEnv = headers.set('env', 'vsphere');
//         headers_env = headers.set('Content-Type', 'application/json; charset=utf-8');

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
//         headers_env = headers.set('Content-Type', 'application/json; charset=utf-8');

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
     *
     * @param url Executes PUT api
     * @param data
     */
    // update(url: string, data: any): Observable<any> {
    //     return this.httpClient.put(url, data, { observe: 'response' })
    //         .map((res: HttpResponse<any>) => this.handleResponse(res))
    //         .catch((error: HttpErrorResponse) => this.handleError(error));
    // };

    /**
     *
     * @param url Executes DELETE api
     */
    // delete(url: string): Observable<any> {
    //     return this.httpClient.delete(url, { observe: 'response' })
    //         .map((res: HttpResponse<any>) => this.handleResponse(res))
    //         .catch((error: HttpErrorResponse) => this.handleError(error));
    // };

    // downloadFile(url: string, token: string): Observable<any> {
    //     const httpHeaders = new HttpHeaders({
    //         'Authorization': 'Bearer ' + token
    //     });
    //     return this.httpClient.get(url, {responseType: 'blob', headers: httpHeaders})
    //         .map(res => res as Blob)
    //         .catch((error: HttpErrorResponse) => this.handleError(error));
    // }

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
//         console.log(error);
        let errorMessage = 'Unknown error!';
        if (error.error instanceof ErrorEvent) {
            errorMessage = `Error: ${error.error}`;
        } else {
            errorMessage = `Error Code: ${error.error}\nMessage: ${error.error}`;
        }
//         console.log(error.error);
        return throwError(error.error);
        // if (error.status === 401) {
        //     return Observable.throw(error.error);
        // } else if (error.status === 500) {
        //     return Observable.throw(error.error);
        // } else {
        //     return Observable.throw(error.error || 'Something has gone wrong. Please contact support.');
        // }
    }
}
