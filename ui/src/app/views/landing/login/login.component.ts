/*
 * Copyright 2021 VMware, Inc
 * SPDX-License-Identifier: BSD-2-Clause
 */
// Angular imports
import { Component } from '@angular/core';
import { Router } from '@angular/router';
import { FormBuilder, FormGroup, Validators, FormControl } from '@angular/forms';

import { ILogin } from 'src/app/views/landing/login/login';
import { ValidationService } from 'src/app/views/landing/wizard/shared/validation/validation.service';
import { APP_ROUTES } from 'src/app/shared/constants/routes.constants';
import { APIClient } from 'src/app/swagger/api-client.service';
import { StepFormDirective } from 'src/app/views/landing/wizard/shared/step-form/step-form';
import { ClrLoadingState } from '@clr/angular';

@Component({
    selector: 'tkg-kickstart-ui-login',
    templateUrl: './login.component.html',
    styleUrls: ['../landing.component.scss']
})
export class LoginComponent extends StepFormDirective{
    public fqdn: String;
    public username: String;
    public password: String;
    public displayError = false;

    public loginLoadingState: ClrLoadingState;

    constructor(
        private router: Router,
        private apiClient: APIClient,
        private formBuilder : FormBuilder,
        private validationService: ValidationService
        // private authService : AuthService
    ) {
        super();
    }

    model: ILogin = { fqdn: "vcenter.local", username: "rashik@vmware.com", password: "admin@123" }
    loginForm: FormGroup;

    ngOnInit() {
        this.loginForm = this.formBuilder.group({});

        this.loginForm.addControl('fqdn',
            new FormControl('', [
                Validators.required,
                this.validationService.isValidIpOrFqdn(),
                this.validationService.noWhitespaceOnEnds()]
            )
        );
        this.loginForm.addControl('username',
            new FormControl('', [
                Validators.required,
                this.validationService.noWhitespaceOnEnds()]
            )
        );
        this.loginForm.addControl('password',
            new FormControl('', [
                Validators.required]
            )
        );
    }

    get f() { return this.loginForm.controls; }

    login() {
        if (this.loginForm.invalid) {
            return;
        }
        else {
            // TODO : TEST on active server
            this.loginLoadingState = ClrLoadingState.LOADING;
            this.apiClient.loginToSIVT(this.f.fqdn.value, this.f.username.value, this.f.password.value).subscribe((data: any) => {
                if (data && data !== null) {
                    if (data.responseType === 'SUCCESS') {
                        this.displayError = false;
                        console.log("Login successful");
                        localStorage.setItem('token', data.token);
                        this.apiClient.loggedInUser = this.f.username.value;
                        this.loginLoadingState = ClrLoadingState.SUCCESS;

                        // Navigating
                        this.navigateToLanding();
                    } else if (data.responseType === 'ERROR') {
                        this.displayError = true;
                        if(data.STATUS_CODE === 401) {
                            this.loginLoadingState = ClrLoadingState.ERROR;
                        } else {
                            this.loginLoadingState = ClrLoadingState.ERROR;
                        }
                    }
                } else {
                    this.displayError = true;
                    this.loginLoadingState = ClrLoadingState.ERROR;
                }
            }, (err: any) => {
                this.displayError = true;
                if (err.responseType === 'ERROR') {
                    this.loginLoadingState = ClrLoadingState.ERROR;
                } else {
                    this.loginLoadingState = ClrLoadingState.ERROR;
                }
            });

            // if (this.f.username.value == this.model.username && this.f.password.value == this.model.password) {
            //     console.log("Login successful");

            //     localStorage.setItem('isLoggedIn', "true");
            //     localStorage.setItem('user', this.f.username.value);
            //     localStorage.setItem('token', this.f.username.value);
            //     console.log(localStorage.getItem('token'));

            //     console.log("navigating");
            //     const landing = APP_ROUTES.LANDING;
            //     this.router.navigate([landing]);
            // }
            // else {
            //     localStorage.removeItem("isLoggedIn");
            //     this.displayError = true;
            // }
        }
    }

    navigateToLanding() {
        const landing = APP_ROUTES.LANDING;
        this.router.navigate([landing]);
    }
}
