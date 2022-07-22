import validationAppName from './api-endpoint-ip-config.json';
import protocol from './api-endpoint-ip-config.json';
import port from './api-endpoint-ip-config.json';

export class ApiEndPoint {

    constructor(){  }

    getGeneratedApiEndpoint(): any {
        let apiEndpoint = '';
        apiEndpoint = this.getIPWithPort();
        return apiEndpoint;
    }

  getGeneratedApiEndpointValidation(): any {
    const apiEndpoint = '';
    const ipWithPort =  this.getIPWithPort();
    const appName = validationAppName;
    return apiEndpoint;
  }

  getIPWithPort(): any {
    return 'http://' + window.location.hostname + ':' + '5000';
//     return ipConfig.protocol + '://localhost:5000';
    // return ipConfig.protocol + "://" + "localhost" + ":" + ipConfig.port;
  }

}
