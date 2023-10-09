/*
 * Copyright 2021 VMware, Inc
 * SPDX-License-Identifier: BSD-2-Clause
 */

export class ApiEndPoint {

    constructor(){  }

    getGeneratedApiEndpoint(): any {
        let apiEndpoint = '';
        apiEndpoint = this.getIPWithPort();
        return apiEndpoint;
    }

  getGeneratedApiEndpointValidation(): any {
    const apiEndpoint = '';
    return apiEndpoint;
  }

  getIPWithPort(): any {
    return 'http://' + window.location.hostname + ':' + '5000';
  }

}
