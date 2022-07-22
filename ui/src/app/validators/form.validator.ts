import { AbstractControl } from '@angular/forms';

export function removeSpaces(control: AbstractControl) {
    if (control && control.value && !control.value.replace(/\s/g, '').length) {
      control.setValue('');
    }
    return null;
  }

  export function IPValidation(control : AbstractControl){
    const IPPattern = /^(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$/;
    if(control && control.value && control.value.match(IPPattern)){
        return null;
    } else {
        return { invalidIPAddress: { valid: false, value: control.value } };
    }
}

export function NotIPValidation(control : AbstractControl){
    const IPPattern = /^(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$/;
    if(control && control.value && control.value.match(IPPattern)){
        return { FQDNRequired: { valid: false, value: control.value } };
    } else {
        return null;
    }
}